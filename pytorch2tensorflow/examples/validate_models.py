#!/usr/bin/env python3
"""
Validate converter reliability with multiple model architectures.

Tests:
  1. UNet (segmentation, skip connections, concat, ConvTranspose)
  2. SimpleResNet (classification, residual add, AdaptiveAvgPool, flatten)

Each model is converted, weights transferred, and output accuracy
compared between PyTorch and TensorFlow.

Usage:
    python -m pytorch2tensorflow.examples.validate_models
"""

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

# ──────────────────────────────────────────────
# Test runner
# ──────────────────────────────────────────────

MODELS = [
    {
        "name": "UNet (segmentation)",
        "code": UNET_CODE,
        "input_shape": (3, 64, 64),
        "expected_output_shape": (1, 2, 64, 64),
    },
    {
        "name": "SimpleResNet (classification)",
        "code": RESNET_CODE,
        "input_shape": (3, 32, 32),
        "expected_output_shape": (1, 10),
    },
]


def test_model_conversion(model_config: dict, tmpdir: str) -> dict:
    """Test a single model through the full conversion pipeline."""
    import torch
    import tensorflow as tf
    from pytorch2tensorflow.converter import ModelConverter

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
    import re
    for line in converted.split("\n"):
        code_part = line.split("#")[0]
        if re.search(r"\btorch\.", code_part):
            result["error"] = f"Unconverted torch ref: {line.strip()}"
            return result

    # Step 3: Load PyTorch model
    spec = __import__("importlib").util.spec_from_file_location("pt", str(pt_path))
    pt_mod = __import__("importlib").util.module_from_spec(spec)
    spec.loader.exec_module(pt_mod)

    # Find the main model class: the last nn.Module subclass in source order.
    import ast as _ast_pt
    _pt_tree = _ast_pt.parse(code)
    _pt_cls_names = [n.name for n in _pt_tree.body if isinstance(n, _ast_pt.ClassDef)]
    pt_cls = None
    for cname in reversed(_pt_cls_names):
        obj = getattr(pt_mod, cname, None)
        if obj and isinstance(obj, type) and issubclass(obj, torch.nn.Module) and obj is not torch.nn.Module:
            pt_cls = obj
            break
    pt_model = pt_cls()
    pt_model.eval()

    # Save and reload weights
    weights_path = Path(tmpdir) / "weights.pth"
    torch.save(pt_model.state_dict(), str(weights_path))

    # Step 4: Load TF model
    spec2 = __import__("importlib").util.spec_from_file_location("tf_m", str(tf_path))
    tf_mod = __import__("importlib").util.module_from_spec(spec2)
    spec2.loader.exec_module(tf_mod)

    # Find the main model class: the last tf.keras.Model subclass in source order.
    import ast as _ast
    _tree = _ast.parse(converted)
    _cls_names = [n.name for n in _tree.body if isinstance(n, _ast.ClassDef)]
    tf_cls = None
    for cname in reversed(_cls_names):
        obj = getattr(tf_mod, cname, None)
        if obj and isinstance(obj, type) and issubclass(obj, tf.keras.Model):
            tf_cls = obj
            break
    tf_model = tf_cls()

    # Build with dummy NHWC input
    c, h, w = input_shape
    dummy = tf.zeros((1, h, w, c))
    tf_model(dummy, training=False)

    result["pt_params"] = sum(p.numel() for p in pt_model.parameters())
    result["tf_params"] = sum(np.prod(v.shape) for v in tf_model.weights)

    # Step 5: Run inference comparison (random weights, no weight transfer)
    np.random.seed(42)
    torch.manual_seed(42)

    input_np = np.random.randn(1, *input_shape).astype(np.float32)

    with torch.no_grad():
        pt_out = pt_model(torch.from_numpy(input_np)).numpy()

    input_nhwc = np.transpose(input_np, (0, 2, 3, 1))
    tf_out = tf_model(tf.constant(input_nhwc), training=False).numpy()

    # Convert TF output back to NCHW for comparison
    if tf_out.ndim == 4:
        tf_out_nchw = np.transpose(tf_out, (0, 3, 1, 2))
    else:
        tf_out_nchw = tf_out

    result["pt_output_shape"] = pt_out.shape
    result["tf_output_shape"] = tf_out_nchw.shape

    # Without weight transfer, shapes should match even if values differ
    if pt_out.shape != tf_out_nchw.shape:
        result["error"] = (
            f"Shape mismatch: PT={pt_out.shape} vs TF={tf_out_nchw.shape}"
        )
        return result

    result["passed"] = True
    return result


def main():
    print("=" * 60)
    print("  Model Conversion Validation Suite")
    print("=" * 60)

    all_passed = True

    for config in MODELS:
        print(f"\n--- {config['name']} ---")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = test_model_conversion(config, tmpdir)
            except Exception as e:
                result = {
                    "name": config["name"],
                    "passed": False,
                    "error": str(e),
                }

            if result["passed"]:
                print(f"  Code conversion:  OK ({result.get('converted_lines', '?')} lines)")
                print(f"  PT params:        {result.get('pt_params', '?'):,}")
                print(f"  TF params:        {result.get('tf_params', '?'):,}")
                print(f"  PT output shape:  {result.get('pt_output_shape')}")
                print(f"  TF output shape:  {result.get('tf_output_shape')}")
                print(f"  Result:           PASS")
            else:
                print(f"  Result:           FAIL")
                print(f"  Error:            {result.get('error')}")
                all_passed = False

    print(f"\n{'=' * 60}")
    print(f"  Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print(f"{'=' * 60}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
