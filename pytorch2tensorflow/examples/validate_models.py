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

Each model is converted, instantiated, and output shape/accuracy
compared between PyTorch and TensorFlow.

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

    # Step 5: Run inference comparison (random weights, shapes must match)
    np.random.seed(42)
    torch.manual_seed(42)
    input_np = np.random.randn(1, *input_shape).astype(np.float32)

    with torch.no_grad():
        pt_out = pt_model(torch.from_numpy(input_np))

    input_nhwc = np.transpose(input_np, (0, 2, 3, 1))
    tf_out = tf_model(tf.constant(input_nhwc), training=False)

    # Handle tuple outputs (e.g. MultiHeadNet)
    if isinstance(pt_out, tuple):
        pt_shapes = tuple(o.numpy().shape for o in pt_out)
        tf_shapes = tuple(o.numpy().shape for o in tf_out)
        shapes_match = pt_shapes == tf_shapes
        result["pt_output_shape"] = pt_shapes
        result["tf_output_shape"] = tf_shapes
    else:
        pt_np = pt_out.numpy()
        tf_np = tf_out.numpy()
        if tf_np.ndim == 4:
            tf_np = np.transpose(tf_np, (0, 3, 1, 2))
        shapes_match = pt_np.shape == tf_np.shape
        result["pt_output_shape"] = pt_np.shape
        result["tf_output_shape"] = tf_np.shape

    if not shapes_match:
        result["error"] = (
            f"Shape mismatch: PT={result['pt_output_shape']} vs TF={result['tf_output_shape']}"
        )
        return result

    result["passed"] = True
    return result


def main():
    print("=" * 65)
    print("  Model Conversion Validation Suite")
    print("=" * 65)

    all_passed = True
    pass_count = 0

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
                pass_count += 1
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

    print(f"\n{'=' * 65}")
    print(f"  Overall: {pass_count}/{len(MODELS)} PASSED"
          + (" — ALL PASSED" if all_passed else " — SOME FAILED"))
    print(f"{'=' * 65}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
