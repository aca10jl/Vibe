#!/usr/bin/env python3
"""
Validate converter reliability with multiple model architectures.

Tests 7 different architectures covering a broad range of PyTorch patterns:
  1. UNet          — segmentation, skip connections, concat, ConvTranspose
  2. SimpleResNet  — classification, residual add, AdaptiveAvgPool, flatten
  3. LeNet         — classic CNN, MaxPool, Linear stack
  4. MiniVGG       — Sequential + BN + ReLU in a loop, AdaptiveAvgPool
  5. MultiHeadNet  — dual output heads (classification + regression)
  6. BottleneckNet — ResNet-50 style bottleneck blocks, 1x1 + 3x3 + 1x1
  7. EncoderDecoder— encoder-decoder with skip connection + ConvTranspose2d

Each model is converted, weights transferred, and output accuracy
compared between PyTorch and TensorFlow with detailed metrics:
  - Cosine Similarity
  - Max / Mean Absolute Difference
  - Max / Mean Relative Difference
  - Min / Max output values for both frameworks
  - Per-sample breakdown over multiple random inputs

Usage:
    python -m pytorch2tensorflow.examples.validate_models
"""

import ast
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

# ──────────────────────────────────────────────
# Model Definitions (PyTorch source code strings)
# ──────────────────────────────────────────────

UNET_CODE = '''
import torch
import torch.nn as nn


class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)

    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = torch.relu(self.bn2(self.conv2(x)))
        return x


class Down(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.pool = nn.MaxPool2d(2)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x):
        return self.conv(self.pool(x))


class Up(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class UNet(nn.Module):
    def __init__(self, in_channels=3, num_classes=2, base_features=16):
        super().__init__()
        self.inc = DoubleConv(in_channels, base_features)
        self.down1 = Down(base_features, base_features * 2)
        self.down2 = Down(base_features * 2, base_features * 4)
        self.up1 = Up(base_features * 4, base_features * 2)
        self.up2 = Up(base_features * 2, base_features)
        self.outc = nn.Conv2d(base_features, num_classes, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x = self.up1(x3, x2)
        x = self.up2(x, x1)
        return self.outc(x)
'''

RESNET_CODE = '''
import torch
import torch.nn as nn


class BasicBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
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
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.layer1 = BasicBlock(32, 32)
        self.layer2 = BasicBlock(32, 64, stride=2,
                                 downsample=nn.Sequential(
                                     nn.Conv2d(32, 64, 1, stride=2, bias=False),
                                     nn.BatchNorm2d(64)))
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(64, num_classes)

    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x
'''

LENET_CODE = '''
import torch
import torch.nn as nn

class LeNet(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 6, kernel_size=5, padding=2)
        self.conv2 = nn.Conv2d(6, 16, kernel_size=5)
        self.pool = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, num_classes)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = torch.flatten(x, 1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x
'''

VGG_BLOCK_CODE = '''
import torch
import torch.nn as nn

class VGGBlock(nn.Module):
    def __init__(self, in_channels, out_channels, num_convs=2):
        super().__init__()
        layers = []
        for i in range(num_convs):
            layers.append(nn.Conv2d(in_channels if i == 0 else out_channels,
                                     out_channels, kernel_size=3, padding=1))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU())
        layers.append(nn.MaxPool2d(2))
        self.block = nn.Sequential(*layers)

    def forward(self, x):
        return self.block(x)

class MiniVGG(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.features = nn.Sequential(
            VGGBlock(3, 64, 2),
            VGGBlock(64, 128, 2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x
'''

MULTIHEAD_CODE = '''
import torch
import torch.nn as nn

class MultiHeadNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.cls_head = nn.Linear(64, 10)
        self.reg_head = nn.Linear(64, 4)

    def forward(self, x):
        feat = self.backbone(x)
        feat = torch.flatten(feat, 1)
        cls_out = self.cls_head(feat)
        reg_out = self.reg_head(feat)
        return cls_out, reg_out
'''

BOTTLENECK_CODE = '''
import torch
import torch.nn as nn

class Bottleneck(nn.Module):
    def __init__(self, in_channels, mid_channels, out_channels, stride=1, downsample=None):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, mid_channels, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(mid_channels)
        self.conv2 = nn.Conv2d(mid_channels, mid_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(mid_channels)
        self.conv3 = nn.Conv2d(mid_channels, out_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(out_channels)
        self.downsample = downsample

    def forward(self, x):
        identity = x
        out = torch.relu(self.bn1(self.conv1(x)))
        out = torch.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return torch.relu(out)

class BottleneckNet(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.block1 = Bottleneck(64, 64, 256,
                                  downsample=nn.Sequential(
                                      nn.Conv2d(64, 256, 1, bias=False),
                                      nn.BatchNorm2d(256)))
        self.block2 = Bottleneck(256, 64, 256)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.block1(x)
        x = self.block2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x
'''

ENCODER_DECODER_CODE = '''
import torch
import torch.nn as nn

class EncoderDecoder(nn.Module):
    def __init__(self, in_ch=3, out_ch=1):
        super().__init__()
        self.enc1 = nn.Sequential(
            nn.Conv2d(in_ch, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )
        self.enc2 = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(),
        )
        self.pool = nn.MaxPool2d(2)
        self.up = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec = nn.Sequential(
            nn.Conv2d(64, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )
        self.final = nn.Conv2d(32, out_ch, kernel_size=1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        d = self.up(e2)
        d = torch.cat([d, e1], dim=1)
        d = self.dec(d)
        return self.final(d)
'''

# ──────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────

NUM_SAMPLES = 5  # random inputs per model

# ── Strict PASS/FAIL thresholds ──
# A model must satisfy ALL of the following to PASS:
COSINE_THRESHOLD = 0.99       # avg cosine similarity ≥ 0.99
COSINE_WORST_THRESHOLD = 0.98 # worst single-sample cosine ≥ 0.98
MAX_ABS_DIFF_THRESHOLD = 0.1  # avg max absolute diff ≤ 0.1
MEAN_ABS_DIFF_THRESHOLD = 0.01  # avg mean absolute diff ≤ 0.01


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two flat vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 and norm_b < 1e-10:
        return 1.0
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def compute_metrics(pt_vec: np.ndarray, tf_vec: np.ndarray) -> dict:
    """Compute full comparison metrics between two flat vectors."""
    abs_diff = np.abs(pt_vec - tf_vec)
    rel_diff = abs_diff / (np.abs(pt_vec) + 1e-10)

    return {
        "cosine_sim": cosine_similarity(pt_vec, tf_vec),
        "max_abs_diff": float(np.max(abs_diff)),
        "mean_abs_diff": float(np.mean(abs_diff)),
        "median_abs_diff": float(np.median(abs_diff)),
        "max_rel_diff": float(np.max(rel_diff)),
        "mean_rel_diff": float(np.mean(rel_diff)),
        "pt_min": float(np.min(pt_vec)),
        "pt_max": float(np.max(pt_vec)),
        "pt_mean": float(np.mean(pt_vec)),
        "pt_std": float(np.std(pt_vec)),
        "tf_min": float(np.min(tf_vec)),
        "tf_max": float(np.max(tf_vec)),
        "tf_mean": float(np.mean(tf_vec)),
        "tf_std": float(np.std(tf_vec)),
    }


def aggregate_metrics(per_sample: list[dict]) -> dict:
    """Aggregate per-sample metrics into summary statistics."""
    keys_avg = [
        "cosine_sim", "max_abs_diff", "mean_abs_diff", "median_abs_diff",
        "max_rel_diff", "mean_rel_diff",
    ]
    agg = {}
    for k in keys_avg:
        vals = [s[k] for s in per_sample]
        agg[k] = float(np.mean(vals))
    agg["worst_max_abs_diff"] = float(max(s["max_abs_diff"] for s in per_sample))
    agg["best_cosine_sim"] = float(max(s["cosine_sim"] for s in per_sample))
    agg["worst_cosine_sim"] = float(min(s["cosine_sim"] for s in per_sample))
    # Use last sample for output range stats
    last = per_sample[-1]
    for k in ["pt_min", "pt_max", "pt_mean", "pt_std",
              "tf_min", "tf_max", "tf_mean", "tf_std"]:
        agg[k] = last[k]
    return agg


# ──────────────────────────────────────────────
# Test runner
# ──────────────────────────────────────────────

MODELS = [
    {
        "name": "UNet (segmentation)",
        "code": UNET_CODE,
        "input_shape": (3, 64, 64),
    },
    {
        "name": "SimpleResNet (classification)",
        "code": RESNET_CODE,
        "input_shape": (3, 32, 32),
    },
    {
        "name": "LeNet (simple CNN)",
        "code": LENET_CODE,
        "input_shape": (1, 28, 28),
    },
    {
        "name": "MiniVGG (Sequential + BN loops)",
        "code": VGG_BLOCK_CODE,
        "input_shape": (3, 32, 32),
    },
    {
        "name": "MultiHeadNet (dual output)",
        "code": MULTIHEAD_CODE,
        "input_shape": (3, 32, 32),
    },
    {
        "name": "BottleneckNet (ResNet-50 style)",
        "code": BOTTLENECK_CODE,
        "input_shape": (3, 32, 32),
    },
    {
        "name": "EncoderDecoder (skip + ConvTranspose)",
        "code": ENCODER_DECODER_CODE,
        "input_shape": (3, 64, 64),
    },
]


def test_model_conversion(model_config: dict, tmpdir: str) -> dict:
    """Test a single model through the full conversion pipeline with metrics."""
    import torch
    import tensorflow as tf
    from pytorch2tensorflow.converter import ModelConverter
    from pytorch2tensorflow.weight_converter import WeightConverter

    name = model_config["name"]
    code = model_config["code"]
    input_shape = model_config["input_shape"]

    result = {"name": name, "passed": False, "error": None}

    # Write PyTorch model
    pt_path = Path(tmpdir) / "model.py"
    pt_path.write_text(code)

    # Step 1: Convert code
    converter = ModelConverter(channels_first=False)
    tf_path = Path(tmpdir) / "model_tf.py"
    converted = converter.convert_file(str(pt_path), str(tf_path))
    result["converted_lines"] = converted.count("\n")

    # Step 2: Check no remaining torch references (excluding comments)
    for line in converted.split("\n"):
        code_part = line.split("#")[0]
        if re.search(r"\btorch\.\w+", code_part):
            if "WARNING" not in line:
                result["error"] = f"Unconverted torch ref: {line.strip()}"
                return result

    # Step 3: Load PyTorch model
    tree = ast.parse(code)
    cls_names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]

    spec = importlib.util.spec_from_file_location("pt", str(pt_path))
    pt_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pt_mod)

    pt_cls = None
    for cname in reversed(cls_names):
        obj = getattr(pt_mod, cname, None)
        if obj and isinstance(obj, type) and issubclass(obj, torch.nn.Module) and obj is not torch.nn.Module:
            pt_cls = obj
            break
    pt_model = pt_cls()
    pt_model.eval()

    # Save weights for transfer
    weights_path = Path(tmpdir) / "weights.pth"
    torch.save(pt_model.state_dict(), str(weights_path))

    # Step 4: Load TF model
    spec2 = importlib.util.spec_from_file_location("tf_m", str(tf_path))
    tf_mod = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(tf_mod)

    tf_tree = ast.parse(converted)
    tf_cls_names = [n.name for n in tf_tree.body if isinstance(n, ast.ClassDef)]
    tf_cls = None
    for cname in reversed(tf_cls_names):
        obj = getattr(tf_mod, cname, None)
        if obj and isinstance(obj, type) and issubclass(obj, tf.keras.Model):
            tf_cls = obj
            break
    tf_model = tf_cls()

    # Build TF model with dummy NHWC input
    c, h, w = input_shape
    dummy = tf.zeros((1, h, w, c))
    tf_model(dummy, training=False)

    result["pt_params"] = sum(p.numel() for p in pt_model.parameters())
    result["tf_params"] = sum(int(np.prod(v.shape)) for v in tf_model.weights)

    # Step 5: Transfer weights
    weight_converter = WeightConverter(strict=False)
    try:
        wstats = weight_converter.convert(
            str(weights_path), tf_model,
            output_path=str(Path(tmpdir) / "tf_weights")
        )
        result["weights_assigned"] = wstats["assigned"]
        result["weights_total"] = wstats["total_pytorch_weights"]
        result["weights_skipped"] = wstats["skipped"]
    except Exception as e:
        result["weights_assigned"] = 0
        result["weights_total"] = "?"
        result["weights_skipped"] = f"error: {e}"

    # Step 6: Multi-sample inference comparison with detailed metrics
    np.random.seed(42)
    torch.manual_seed(42)

    per_sample_metrics = []
    shape_ok = True

    for _ in range(NUM_SAMPLES):
        input_np = np.random.randn(1, *input_shape).astype(np.float32)

        with torch.no_grad():
            pt_out = pt_model(torch.from_numpy(input_np))

        input_nhwc = np.transpose(input_np, (0, 2, 3, 1))
        tf_out = tf_model(tf.constant(input_nhwc), training=False)

        # Handle tuple outputs (e.g. MultiHeadNet)
        if isinstance(pt_out, tuple):
            pt_list = [o.numpy() for o in pt_out]
            tf_list = [o.numpy() for o in tf_out]
            result["pt_output_shape"] = tuple(o.shape for o in pt_list)
            result["tf_output_shape"] = tuple(o.shape for o in tf_list)
            if result["pt_output_shape"] != result["tf_output_shape"]:
                shape_ok = False
                break
            # Concat all heads for unified metric computation
            pt_vec = np.concatenate([o.flatten() for o in pt_list])
            tf_vec = np.concatenate([o.flatten() for o in tf_list])
        else:
            pt_np = pt_out.numpy()
            tf_np = tf_out.numpy()
            if tf_np.ndim == 4:
                tf_np = np.transpose(tf_np, (0, 3, 1, 2))
            result["pt_output_shape"] = pt_np.shape
            result["tf_output_shape"] = tf_np.shape
            if pt_np.shape != tf_np.shape:
                shape_ok = False
                break
            pt_vec = pt_np.flatten()
            tf_vec = tf_np.flatten()

        per_sample_metrics.append(compute_metrics(pt_vec, tf_vec))

    if not shape_ok:
        result["error"] = (
            f"Shape mismatch: PT={result['pt_output_shape']} vs TF={result['tf_output_shape']}"
        )
        return result

    result["metrics"] = aggregate_metrics(per_sample_metrics)
    result["per_sample"] = per_sample_metrics

    # Strict metric-based PASS/FAIL
    m = result["metrics"]
    checks = {
        "cosine_sim >= {:.2f}".format(COSINE_THRESHOLD):
            m["cosine_sim"] >= COSINE_THRESHOLD,
        "worst_cosine >= {:.2f}".format(COSINE_WORST_THRESHOLD):
            m["worst_cosine_sim"] >= COSINE_WORST_THRESHOLD,
        "max_abs_diff <= {:.2f}".format(MAX_ABS_DIFF_THRESHOLD):
            m["max_abs_diff"] <= MAX_ABS_DIFF_THRESHOLD,
        "mean_abs_diff <= {:.4f}".format(MEAN_ABS_DIFF_THRESHOLD):
            m["mean_abs_diff"] <= MEAN_ABS_DIFF_THRESHOLD,
    }
    result["checks"] = checks
    result["passed"] = all(checks.values())

    if not result["passed"]:
        failed_checks = [k for k, v in checks.items() if not v]
        result["error"] = "Failed criteria: " + ", ".join(failed_checks)

    return result


def print_metrics(metrics: dict, per_sample: list[dict]):
    """Pretty-print validation metrics."""
    w = 24  # label width
    print(f"  {'Cosine Similarity':<{w}}: {metrics['cosine_sim']:.8f}"
          f"  (best={metrics['best_cosine_sim']:.8f}, worst={metrics['worst_cosine_sim']:.8f})")
    print(f"  {'Max Abs Diff':<{w}}: {metrics['max_abs_diff']:.6e}"
          f"  (worst={metrics['worst_max_abs_diff']:.6e})")
    print(f"  {'Mean Abs Diff':<{w}}: {metrics['mean_abs_diff']:.6e}")
    print(f"  {'Median Abs Diff':<{w}}: {metrics['median_abs_diff']:.6e}")
    print(f"  {'Max Rel Diff':<{w}}: {metrics['max_rel_diff']:.6e}")
    print(f"  {'Mean Rel Diff':<{w}}: {metrics['mean_rel_diff']:.6e}")
    print()
    print(f"  {'PT output range':<{w}}: [{metrics['pt_min']:.6f}, {metrics['pt_max']:.6f}]"
          f"  mean={metrics['pt_mean']:.6f}, std={metrics['pt_std']:.6f}")
    print(f"  {'TF output range':<{w}}: [{metrics['tf_min']:.6f}, {metrics['tf_max']:.6f}]"
          f"  mean={metrics['tf_mean']:.6f}, std={metrics['tf_std']:.6f}")
    print()
    print(f"  Per-sample breakdown ({len(per_sample)} samples):")
    print(f"  {'#':>4}  {'Cosine':>12}  {'MaxAbsDiff':>12}  {'MeanAbsDiff':>12}  {'MaxRelDiff':>12}")
    for i, s in enumerate(per_sample):
        print(f"  {i+1:>4}  {s['cosine_sim']:>12.8f}  {s['max_abs_diff']:>12.6e}"
              f"  {s['mean_abs_diff']:>12.6e}  {s['max_rel_diff']:>12.6e}")


def main():
    print("=" * 78)
    print("  Model Conversion Validation Suite (with weight transfer + accuracy metrics)")
    print("=" * 78)

    all_passed = True
    pass_count = 0
    summary_rows = []

    for config in MODELS:
        print(f"\n{'─' * 78}")
        print(f"  {config['name']}")
        print(f"{'─' * 78}")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = test_model_conversion(config, tmpdir)
            except Exception as e:
                result = {
                    "name": config["name"],
                    "passed": False,
                    "error": str(e),
                }

            m = result.get("metrics")
            if m:
                print(f"  Code conversion:   OK ({result.get('converted_lines', '?')} lines)")
                print(f"  PT params:         {result.get('pt_params', '?'):,}")
                print(f"  TF params:         {result.get('tf_params', '?'):,}")
                wa = result.get("weights_assigned", "?")
                wt = result.get("weights_total", "?")
                ws = result.get("weights_skipped", 0)
                print(f"  Weights transfer:  {wa}/{wt} assigned, {ws} skipped")
                print(f"  Output shape (PT): {result.get('pt_output_shape')}")
                print(f"  Output shape (TF): {result.get('tf_output_shape')}")
                print()
                print_metrics(m, result["per_sample"])

                # Print criteria check results
                print()
                checks = result.get("checks", {})
                for criterion, ok in checks.items():
                    mark = "PASS" if ok else "FAIL"
                    print(f"  [{mark}] {criterion}")

                if result["passed"]:
                    pass_count += 1
                    print(f"\n  Result: PASS")
                else:
                    all_passed = False
                    print(f"\n  Result: FAIL — {result.get('error', '')}")
                summary_rows.append((config["name"], m["cosine_sim"],
                                     m["max_abs_diff"], m["mean_abs_diff"],
                                     result["passed"]))
            else:
                print(f"  Result: FAIL")
                print(f"  Error:  {result.get('error')}")
                all_passed = False
                summary_rows.append((config["name"], 0.0, 0.0, 0.0, False))

    # ── Summary table ──
    print(f"\n{'=' * 78}")
    print("  Summary")
    print(f"{'=' * 78}")
    print(f"  {'Model':<35} {'Cosine':>10} {'MaxAbsDiff':>12} {'MeanAbsDiff':>12} {'Status':>8}")
    print(f"  {'─'*35} {'─'*10} {'─'*12} {'─'*12} {'─'*8}")
    for name, cos, mad, mead, ok in summary_rows:
        st = "PASS" if ok else "FAIL"
        if ok:
            print(f"  {name:<35} {cos:>10.6f} {mad:>12.6e} {mead:>12.6e} {st:>8}")
        else:
            print(f"  {name:<35} {'—':>10} {'—':>12} {'—':>12} {st:>8}")

    print(f"\n  Overall: {pass_count}/{len(MODELS)} PASSED"
          + (" — ALL PASSED" if all_passed else " — SOME FAILED"))
    print(f"{'=' * 78}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
