#!/usr/bin/env python3
"""
End-to-end conversion demo: PyTorch model → TensorFlow → PB export.

Demonstrates the complete pytorch2tensorflow pipeline on a SimpleResNet:
    1. Define and save a PyTorch model + weights
    2. Convert model code to TensorFlow
    3. Build TF model and transfer weights
    4. Validate accuracy (cosine similarity, abs/rel diff, output stats)
    5. Export to Frozen Graph (.pb) and check Ascend compatibility

Usage:
    python -m pytorch2tensorflow.examples.run_conversion

    # Or with custom options:
    python pytorch2tensorflow/examples/run_conversion.py --num-samples 10
"""

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np

# ─────────────────────────────────────────────
# PyTorch model source
# ─────────────────────────────────────────────

PYTORCH_MODEL_CODE = '''
import torch
import torch.nn as nn


class BasicBlock(nn.Module):
    """ResNet Basic Block with residual connection."""

    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.downsample = downsample

    def forward(self, x):
        identity = x
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return torch.relu(out)


class SimpleResNet(nn.Module):
    """A simple ResNet for demonstration (3-channel input, 10 classes)."""

    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)

        self.layer1 = BasicBlock(32, 32)
        self.layer2 = BasicBlock(32, 64, stride=2,
                                 downsample=nn.Sequential(
                                     nn.Conv2d(32, 64, 1, stride=2, bias=False),
                                     nn.BatchNorm2d(64)))
        self.layer3 = BasicBlock(64, 128, stride=2,
                                 downsample=nn.Sequential(
                                     nn.Conv2d(64, 128, 1, stride=2, bias=False),
                                     nn.BatchNorm2d(128)))

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x
'''


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 and norm_b < 1e-10:
        return 1.0
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def main():
    parser = argparse.ArgumentParser(description="PyTorch → TensorFlow conversion demo")
    parser.add_argument("--num-samples", type=int, default=5,
                        help="Number of random samples for accuracy validation")
    parser.add_argument("--input-shape", type=str, default="3,224,224",
                        help="Input shape in C,H,W format (default: 3,224,224)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: auto temp dir)")
    args = parser.parse_args()

    input_shape = tuple(int(x) for x in args.input_shape.split(","))
    c, h, w = input_shape

    work_dir = Path(args.output_dir) if args.output_dir else Path(tempfile.mkdtemp(prefix="pt2tf_demo_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("  PyTorch → TensorFlow Full Pipeline Demo")
    print("=" * 78)
    print(f"  Input shape:  ({c}, {h}, {w}) NCHW")
    print(f"  Output dir:   {work_dir}")
    print(f"  Num samples:  {args.num_samples}")

    # ─── Step 1: Create PyTorch model ───
    print(f"\n{'─' * 78}")
    print("  [Step 1] Creating PyTorch model and saving weights")
    print(f"{'─' * 78}")

    import torch

    pt_model_path = work_dir / "model.py"
    pt_model_path.write_text(PYTORCH_MODEL_CODE)

    # Load model dynamically
    import importlib.util
    spec = importlib.util.spec_from_file_location("pt_model", str(pt_model_path))
    pt_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pt_mod)

    pt_model = pt_mod.SimpleResNet(num_classes=10)
    pt_model.eval()

    param_count = sum(p.numel() for p in pt_model.parameters())
    print(f"  Model class:     SimpleResNet")
    print(f"  Parameters:      {param_count:,}")

    # Test forward pass
    dummy = torch.randn(1, *input_shape)
    with torch.no_grad():
        pt_test = pt_model(dummy)
    print(f"  Output shape:    {tuple(pt_test.shape)}")

    # Save weights
    pt_weights_path = work_dir / "model_weights.pth"
    torch.save(pt_model.state_dict(), str(pt_weights_path))
    print(f"  Weights saved:   {pt_weights_path} ({pt_weights_path.stat().st_size / 1024:.1f} KB)")

    # ─── Step 2: Convert model code ───
    print(f"\n{'─' * 78}")
    print("  [Step 2] Converting model code to TensorFlow")
    print(f"{'─' * 78}")

    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(add_channel_convert=True)
    tf_model_path = work_dir / "model_tf.py"
    converted_code = converter.convert_file(str(pt_model_path), str(tf_model_path))

    num_lines = converted_code.count("\n")
    print(f"  Output file:     {tf_model_path}")
    print(f"  Converted lines: {num_lines}")

    # Show key transformations
    print(f"\n  Key converted lines:")
    for line in converted_code.split("\n"):
        s = line.strip()
        if any(kw in s for kw in [
            "class SimpleResNet", "class BasicBlock",
            "tf.keras.layers.Conv2D", "tf.keras.layers.Dense",
            "tf.keras.layers.BatchNorm", "def call",
        ]):
            print(f"    {line.rstrip()}")

    # ─── Step 3: Build TF model and transfer weights ───
    print(f"\n{'─' * 78}")
    print("  [Step 3] Building TF model and transferring weights")
    print(f"{'─' * 78}")

    import tensorflow as tf

    spec2 = importlib.util.spec_from_file_location("tf_model", str(tf_model_path))
    tf_mod = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(tf_mod)

    tf_model = tf_mod.SimpleResNet(num_classes=10)

    # Build with dummy NHWC input
    dummy_nhwc = tf.zeros((1, h, w, c))
    _ = tf_model(dummy_nhwc, training=False)

    tf_trainable = sum(int(np.prod(w.shape)) for w in tf_model.trainable_weights)
    tf_total = sum(int(np.prod(w.shape)) for w in tf_model.weights)
    print(f"  TF trainable params: {tf_trainable:,}")
    print(f"  TF total params:     {tf_total:,}")

    # Weight transfer
    from pytorch2tensorflow.weight_converter import WeightConverter

    weight_converter = WeightConverter(strict=False)
    wstats = weight_converter.convert(
        str(pt_weights_path), tf_model,
        output_path=str(work_dir / "tf_weights")
    )
    print(f"  Weights assigned:    {wstats['assigned']}/{wstats['total_pytorch_weights']}")
    print(f"  Weights skipped:     {wstats['skipped']}")
    print(f"  Errors:              {wstats['errors']}")

    # ─── Step 4: Accuracy validation ───
    print(f"\n{'─' * 78}")
    print(f"  [Step 4] Validating accuracy ({args.num_samples} random samples)")
    print(f"{'─' * 78}")

    np.random.seed(42)
    torch.manual_seed(42)

    all_cosine = []
    all_max_abs = []
    all_mean_abs = []
    all_max_rel = []
    all_mean_rel = []

    print(f"\n  {'#':>4}  {'Cosine':>12}  {'MaxAbsDiff':>12}  {'MeanAbsDiff':>12}"
          f"  {'MaxRelDiff':>12}  {'MeanRelDiff':>12}")
    print(f"  {'─'*4}  {'─'*12}  {'─'*12}  {'─'*12}  {'─'*12}  {'─'*12}")

    for i in range(args.num_samples):
        input_np = np.random.randn(1, *input_shape).astype(np.float32)

        with torch.no_grad():
            pt_out = pt_model(torch.from_numpy(input_np)).numpy()

        input_nhwc = np.transpose(input_np, (0, 2, 3, 1))
        tf_out = tf_model(tf.constant(input_nhwc), training=False).numpy()

        pt_flat = pt_out.flatten()
        tf_flat = tf_out.flatten()

        cos_sim = cosine_similarity(pt_flat, tf_flat)
        abs_diff = np.abs(pt_flat - tf_flat)
        rel_diff = abs_diff / (np.abs(pt_flat) + 1e-10)

        max_abs = float(np.max(abs_diff))
        mean_abs = float(np.mean(abs_diff))
        max_rel = float(np.max(rel_diff))
        mean_rel = float(np.mean(rel_diff))

        all_cosine.append(cos_sim)
        all_max_abs.append(max_abs)
        all_mean_abs.append(mean_abs)
        all_max_rel.append(max_rel)
        all_mean_rel.append(mean_rel)

        print(f"  {i+1:>4}  {cos_sim:>12.8f}  {max_abs:>12.6e}  {mean_abs:>12.6e}"
              f"  {max_rel:>12.6e}  {mean_rel:>12.6e}")

    # Aggregate
    avg_cosine = float(np.mean(all_cosine))
    avg_max_abs = float(np.mean(all_max_abs))
    avg_mean_abs = float(np.mean(all_mean_abs))
    worst_max_abs = float(max(all_max_abs))
    worst_cosine = float(min(all_cosine))

    print(f"\n  ──── Aggregate ({args.num_samples} samples) ────")
    print(f"  {'Avg Cosine Similarity':<26}: {avg_cosine:.8f}")
    print(f"  {'Worst Cosine Similarity':<26}: {worst_cosine:.8f}")
    print(f"  {'Avg Max Abs Diff':<26}: {avg_max_abs:.6e}")
    print(f"  {'Worst Max Abs Diff':<26}: {worst_max_abs:.6e}")
    print(f"  {'Avg Mean Abs Diff':<26}: {avg_mean_abs:.6e}")

    # Output distribution comparison (last sample)
    print(f"\n  ──── Output Distribution (last sample) ────")
    print(f"  {'':>10} {'Min':>12} {'Max':>12} {'Mean':>12} {'Std':>12}")
    print(f"  {'PyTorch':>10} {np.min(pt_flat):>12.6f} {np.max(pt_flat):>12.6f}"
          f" {np.mean(pt_flat):>12.6f} {np.std(pt_flat):>12.6f}")
    print(f"  {'TensorFlow':>10} {np.min(tf_flat):>12.6f} {np.max(tf_flat):>12.6f}"
          f" {np.mean(tf_flat):>12.6f} {np.std(tf_flat):>12.6f}")

    passed = avg_cosine >= 0.99 or avg_mean_abs <= 1e-3
    status = "PASSED" if passed else "FAILED"
    print(f"\n  Validation: {status}")

    # ─── Step 5: Export to PB ───
    print(f"\n{'─' * 78}")
    print("  [Step 5] Exporting to Frozen Graph (.pb)")
    print(f"{'─' * 78}")

    from pytorch2tensorflow.exporter import PBExporter

    exporter = PBExporter()
    pb_path = str(work_dir / "frozen_model.pb")
    pb_ok = False
    try:
        exporter.export_frozen_graph(
            tf_model, pb_path,
            input_shapes=[(h, w, c)]
        )
        pb_size = Path(pb_path).stat().st_size
        print(f"  Frozen graph:    {pb_path}")
        print(f"  PB file size:    {pb_size / 1024:.1f} KB")
        pb_ok = True
    except Exception as e:
        print(f"  Export error:     {e}")

    if pb_ok and Path(pb_path).exists():
        print(f"\n  Ascend compatibility check:")
        compat = exporter.check_ascend_compatibility(pb_path=pb_path)
        print(f"    Total nodes:       {compat['total_nodes']}")
        print(f"    Unique ops:        {compat['unique_ops']}")
        print(f"    Supported ops:     {len(compat['supported_ops'])}")
        print(f"    Unknown ops:       {len(compat['unsupported_ops'])}")
        compat_st = "COMPATIBLE" if compat['compatible'] else "ISSUES FOUND"
        print(f"    Status:            {compat_st}")

        if compat['unsupported_ops']:
            print(f"    Unknown ops list:  {compat['unsupported_ops']}")

        print(f"\n  Generated ATC command:")
        atc_cmd = exporter.generate_atc_command(
            pb_path=pb_path,
            output_path=str(work_dir / "model_ascend"),
            soc_version="Ascend910B4",
            input_shape=f"input:1,{h},{w},{c}",
        )
        for line in atc_cmd.split("\n"):
            print(f"    {line}")

    # ─── Summary ───
    print(f"\n{'=' * 78}")
    print("  Pipeline Summary")
    print(f"{'=' * 78}")
    print(f"  Model:             SimpleResNet (num_classes=10)")
    print(f"  Input shape:       ({c}, {h}, {w}) NCHW / ({h}, {w}, {c}) NHWC")
    print(f"  PT parameters:     {param_count:,}")
    print(f"  TF parameters:     {tf_total:,}")
    print(f"  Weights mapped:    {wstats['assigned']}/{wstats['total_pytorch_weights']}")
    print(f"  Cosine similarity: {avg_cosine:.8f} (worst: {worst_cosine:.8f})")
    print(f"  Max abs diff:      {avg_max_abs:.6e} (worst: {worst_max_abs:.6e})")
    print(f"  Accuracy:          {status}")
    print(f"  PB export:         {'OK' if pb_ok else 'FAILED'}")
    print(f"  Output dir:        {work_dir}")
    print(f"{'=' * 78}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
