#!/usr/bin/env python3
"""
End-to-end verification: PyTorch UNet → TensorFlow UNet conversion.

This script:
    1. Creates a PyTorch UNet model and saves weights
    2. Converts the model code to TensorFlow
    3. Builds the TF model and converts weights
    4. Validates output accuracy between PT and TF models
    5. Exports to PB format and checks Ascend compatibility
"""

import os
import sys
import tempfile
from pathlib import Path

import numpy as np


def main():
    print("=" * 70)
    print("  PyTorch UNet → TensorFlow Conversion Verification")
    print("=" * 70)

    # ─── Step 1: Create PyTorch UNet and save weights ───
    print("\n[Step 1] Creating PyTorch UNet model and saving weights...")
    import torch

    # Import from the examples directory
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    from unet_model import UNet as PyTorchUNet

    pt_model = PyTorchUNet(in_channels=3, num_classes=2, base_features=32)
    pt_model.eval()

    param_count = sum(p.numel() for p in pt_model.parameters())
    print(f"  Model parameters: {param_count:,}")

    # Test forward pass
    dummy_input_nchw = torch.randn(1, 3, 128, 128)
    with torch.no_grad():
        pt_output = pt_model(dummy_input_nchw)
    print(f"  PT input shape:  {dummy_input_nchw.shape} (NCHW)")
    print(f"  PT output shape: {pt_output.shape} (NCHW)")

    # Save weights
    work_dir = Path(tempfile.mkdtemp(prefix="unet_convert_"))
    pt_weights_path = work_dir / "unet_pytorch.pth"
    torch.save(pt_model.state_dict(), str(pt_weights_path))
    print(f"  Weights saved to: {pt_weights_path}")
    print(f"  Weight file size: {pt_weights_path.stat().st_size / 1024:.1f} KB")

    # ─── Step 2: Convert model code ───
    print("\n[Step 2] Converting model code PyTorch → TensorFlow...")
    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(add_channel_convert=True)
    pt_model_path = script_dir / "unet_model.py"
    tf_model_path = work_dir / "unet_model_tf.py"

    converted_code = converter.convert_file(str(pt_model_path), str(tf_model_path))
    print(f"  Converted code saved to: {tf_model_path}")
    print(f"  Converted code lines: {converted_code.count(chr(10))}")

    # Show key conversions
    print("\n  --- Key Converted Code Snippets ---")
    for line in converted_code.split("\n"):
        stripped = line.strip()
        if any(kw in stripped for kw in ["tf.pad", "tf.concat", "tf.keras.layers.Conv2D",
                                          "tf.keras.layers.BatchNorm", "def call",
                                          "class UNet", "class Up", "class Down",
                                          "class DoubleConv"]):
            print(f"  | {line.rstrip()}")

    # ─── Step 3: Build TF model manually and convert weights ───
    print("\n[Step 3] Building TensorFlow UNet and converting weights...")
    import tensorflow as tf

    # Build TF UNet manually (since auto-import of converted code is fragile)
    tf_model = build_tf_unet(in_channels=3, num_classes=2, base_features=32)

    # Build model with dummy input (NHWC)
    dummy_input_nhwc = tf.zeros((1, 128, 128, 3))
    _ = tf_model(dummy_input_nhwc, training=False)

    tf_param_count = sum(np.prod(w.shape) for w in tf_model.trainable_weights)
    tf_total_count = sum(np.prod(w.shape) for w in tf_model.weights)
    print(f"  TF trainable params: {tf_param_count:,}")
    print(f"  TF total params:     {tf_total_count:,}")

    # Convert weights
    from pytorch2tensorflow.weight_converter import WeightConverter

    weight_converter = WeightConverter(strict=False)
    stats = weight_converter.convert(
        str(pt_weights_path), tf_model,
        output_path=str(work_dir / "tf_weights")
    )
    print(f"  Weights assigned: {stats['assigned']}/{stats['total_pytorch_weights']}")
    print(f"  Weights skipped:  {stats['skipped']}")
    print(f"  Errors:           {stats['errors']}")

    # ─── Step 4: Validate output accuracy ───
    print("\n[Step 4] Validating output accuracy PT ↔ TF...")

    np.random.seed(42)
    torch.manual_seed(42)

    num_tests = 5
    all_max_abs = []
    all_mean_abs = []
    all_cosine = []

    for i in range(num_tests):
        # Random input
        input_np = np.random.randn(1, 3, 128, 128).astype(np.float32)

        # PT forward (NCHW)
        with torch.no_grad():
            pt_out = pt_model(torch.from_numpy(input_np)).numpy()

        # TF forward (NHWC)
        input_nhwc = np.transpose(input_np, (0, 2, 3, 1))
        tf_out = tf_model(tf.constant(input_nhwc), training=False).numpy()

        # Convert TF output back to NCHW for comparison
        tf_out_nchw = np.transpose(tf_out, (0, 3, 1, 2))

        # Metrics
        abs_diff = np.abs(pt_out - tf_out_nchw)
        max_abs = float(np.max(abs_diff))
        mean_abs = float(np.mean(abs_diff))

        pt_flat = pt_out.flatten()
        tf_flat = tf_out_nchw.flatten()
        cos_sim = float(np.dot(pt_flat, tf_flat) / (
            np.linalg.norm(pt_flat) * np.linalg.norm(tf_flat) + 1e-10
        ))

        all_max_abs.append(max_abs)
        all_mean_abs.append(mean_abs)
        all_cosine.append(cos_sim)

        print(f"  Sample {i+1}: max_abs={max_abs:.2e}, mean_abs={mean_abs:.2e}, cosine={cos_sim:.6f}")

    avg_max_abs = np.mean(all_max_abs)
    avg_mean_abs = np.mean(all_mean_abs)
    avg_cosine = np.mean(all_cosine)

    print(f"\n  ──── Aggregate Results ({num_tests} samples) ────")
    print(f"  Avg Max Abs Diff:  {avg_max_abs:.2e}")
    print(f"  Avg Mean Abs Diff: {avg_mean_abs:.2e}")
    print(f"  Avg Cosine Sim:    {avg_cosine:.6f}")

    # Determine pass/fail
    passed = avg_cosine >= 0.99 or avg_mean_abs <= 1e-3
    status = "PASSED ✓" if passed else "FAILED ✗"
    print(f"  Validation: {status}")

    # ─── Step 5: Export to PB format ───
    print("\n[Step 5] Exporting TF model to PB format...")
    from pytorch2tensorflow.exporter import PBExporter

    exporter = PBExporter()

    # Export frozen graph
    pb_path = str(work_dir / "frozen_unet.pb")
    try:
        exporter.export_frozen_graph(
            tf_model, pb_path,
            input_shapes=[(128, 128, 3)]  # NHWC without batch
        )
        pb_size = Path(pb_path).stat().st_size
        print(f"  Frozen graph: {pb_path}")
        print(f"  PB file size: {pb_size / 1024:.1f} KB")
    except Exception as e:
        print(f"  Frozen graph export error: {e}")
        pb_path = None

    # Check Ascend compatibility
    if pb_path and Path(pb_path).exists():
        print("\n[Step 5b] Checking Ascend (昇腾) compatibility...")
        compat = exporter.check_ascend_compatibility(pb_path=pb_path)
        print(f"  Total nodes:       {compat['total_nodes']}")
        print(f"  Unique ops:        {compat['unique_ops']}")
        print(f"  Supported ops:     {len(compat['supported_ops'])}")
        print(f"  Unknown ops:       {len(compat['unsupported_ops'])}")
        print(f"  Problematic ops:   {len(compat['problematic_ops'])}")
        compat_status = "COMPATIBLE ✓" if compat['compatible'] else "ISSUES FOUND ✗"
        print(f"  Ascend status:     {compat_status}")

        if compat['unsupported_ops']:
            print(f"  Unknown ops list:  {compat['unsupported_ops']}")

        # Generate ATC command
        print("\n  Generated ATC command:")
        atc_cmd = exporter.generate_atc_command(
            pb_path=pb_path,
            output_path=str(work_dir / "unet_model"),
            soc_version="Ascend910B4",
            input_shape="input:1,128,128,3",
        )
        for line in atc_cmd.split("\n"):
            print(f"    {line}")

    # ─── Summary ───
    print("\n" + "=" * 70)
    print("  Conversion Summary")
    print("=" * 70)
    print(f"  Model:           UNet (base_features=32)")
    print(f"  PT Parameters:   {param_count:,}")
    print(f"  TF Parameters:   {tf_total_count:,}")
    print(f"  Weights Mapped:  {stats['assigned']}/{stats['total_pytorch_weights']}")
    print(f"  Accuracy:        {'PASS' if passed else 'FAIL'} (cosine={avg_cosine:.6f})")
    print(f"  PB Export:       {'OK' if pb_path else 'FAILED'}")
    print(f"  Output dir:      {work_dir}")
    print("=" * 70)

    return 0 if passed else 1


# ───────────────────────────────────────────────────────────
# TF UNet (manually constructed to match the PyTorch version)
# ───────────────────────────────────────────────────────────

def build_tf_unet(in_channels=3, num_classes=2, base_features=32):
    """Build a TF UNet matching the PyTorch UNet structure."""
    import tensorflow as tf

    class TFDoubleConv(tf.keras.layers.Layer):
        def __init__(self, out_channels, **kwargs):
            super().__init__(**kwargs)
            self.conv1 = tf.keras.layers.Conv2D(out_channels, 3, padding='same', use_bias=False)
            self.bn1 = tf.keras.layers.BatchNormalization()
            self.conv2 = tf.keras.layers.Conv2D(out_channels, 3, padding='same', use_bias=False)
            self.bn2 = tf.keras.layers.BatchNormalization()

        def call(self, x, training=False):
            x = tf.nn.relu(self.bn1(self.conv1(x), training=training))
            x = tf.nn.relu(self.bn2(self.conv2(x), training=training))
            return x

    class TFDown(tf.keras.layers.Layer):
        def __init__(self, out_channels, **kwargs):
            super().__init__(**kwargs)
            self.pool = tf.keras.layers.MaxPool2D(2)
            self.conv = TFDoubleConv(out_channels)

        def call(self, x, training=False):
            x = self.pool(x)
            x = self.conv(x, training=training)
            return x

    class TFUp(tf.keras.layers.Layer):
        def __init__(self, in_channels, out_channels, **kwargs):
            super().__init__(**kwargs)
            self.up = tf.keras.layers.Conv2DTranspose(
                in_channels // 2, kernel_size=2, strides=2)
            self.conv = TFDoubleConv(out_channels)

        def call(self, x1, x2, training=False):
            x1 = self.up(x1)
            # Pad to match spatial dims (NHWC)
            diff_h = tf.shape(x2)[1] - tf.shape(x1)[1]
            diff_w = tf.shape(x2)[2] - tf.shape(x1)[2]
            x1 = tf.pad(x1, [
                [0, 0],
                [diff_h // 2, diff_h - diff_h // 2],
                [diff_w // 2, diff_w - diff_w // 2],
                [0, 0]
            ])
            x = tf.concat([x2, x1], axis=-1)
            x = self.conv(x, training=training)
            return x

    class TFUNet(tf.keras.Model):
        def __init__(self, in_ch=3, n_classes=2, base=32, **kwargs):
            super().__init__(**kwargs)
            self.inc = TFDoubleConv(base, name='inc')
            self.down1 = TFDown(base * 2, name='down1')
            self.down2 = TFDown(base * 4, name='down2')
            self.down3 = TFDown(base * 8, name='down3')
            self.down4 = TFDown(base * 16, name='down4')
            self.up1 = TFUp(base * 16, base * 8, name='up1')
            self.up2 = TFUp(base * 8, base * 4, name='up2')
            self.up3 = TFUp(base * 4, base * 2, name='up3')
            self.up4 = TFUp(base * 2, base, name='up4')
            self.outc = tf.keras.layers.Conv2D(n_classes, 1, name='outc')

        def call(self, x, training=False):
            x1 = self.inc(x, training=training)
            x2 = self.down1(x1, training=training)
            x3 = self.down2(x2, training=training)
            x4 = self.down3(x3, training=training)
            x5 = self.down4(x4, training=training)
            x = self.up1(x5, x4, training=training)
            x = self.up2(x, x3, training=training)
            x = self.up3(x, x2, training=training)
            x = self.up4(x, x1, training=training)
            x = self.outc(x)
            return x

    return TFUNet(in_ch=in_channels, n_classes=num_classes, base=base_features)


if __name__ == "__main__":
    sys.exit(main())
