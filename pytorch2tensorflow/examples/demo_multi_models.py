#!/usr/bin/env python3
"""
Demo: Convert multiple PyTorch model architectures to TensorFlow in one go.

This script demonstrates the converter's versatility by converting
several common model patterns and printing the converted TensorFlow code.

Usage:
    python -m pytorch2tensorflow.examples.demo_multi_models
"""

import tempfile
from pathlib import Path

from pytorch2tensorflow.converter import ModelConverter

# ────────────────────────────────────────────
# Demo Models
# ────────────────────────────────────────────

MODELS = {
    "LeNet (Classic CNN)": '''
import torch
import torch.nn as nn

class LeNet(nn.Module):
    """Classic LeNet-5 for MNIST."""
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
        return self.fc3(x)
''',

    "ResNet Bottleneck Block": '''
import torch
import torch.nn as nn

class Bottleneck(nn.Module):
    """ResNet-50 style bottleneck: 1x1 -> 3x3 -> 1x1 with residual."""
    def __init__(self, in_ch, mid_ch, out_ch, downsample=None):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, mid_ch, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(mid_ch)
        self.conv2 = nn.Conv2d(mid_ch, mid_ch, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(mid_ch)
        self.conv3 = nn.Conv2d(mid_ch, out_ch, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(out_ch)
        self.downsample = downsample

    def forward(self, x):
        identity = x
        out = torch.relu(self.bn1(self.conv1(x)))
        out = torch.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        return torch.relu(out + identity)
''',

    "Multi-Head Network (Classification + Regression)": '''
import torch
import torch.nn as nn

class MultiHeadNet(nn.Module):
    """Shared backbone with two output heads."""
    def __init__(self):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.cls_head = nn.Linear(32, 10)
        self.reg_head = nn.Linear(32, 4)

    def forward(self, x):
        feat = torch.flatten(self.backbone(x), 1)
        return self.cls_head(feat), self.reg_head(feat)
''',

    "Encoder-Decoder with Skip Connection": '''
import torch
import torch.nn as nn

class EncoderDecoder(nn.Module):
    """Small encoder-decoder with skip connection and ConvTranspose."""
    def __init__(self, in_ch=3, out_ch=1):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(in_ch, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(),
        )
        self.up = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec = nn.Conv2d(64, out_ch, kernel_size=1)

    def forward(self, x):
        e = self.enc(x)
        b = self.bottleneck(self.pool(e))
        d = self.up(b)
        return self.dec(torch.cat([d, e], dim=1))
''',
}


def main():
    converter = ModelConverter(channels_first=False)

    print("=" * 70)
    print("  PyTorch → TensorFlow Multi-Model Conversion Demo")
    print("=" * 70)

    for name, pt_code in MODELS.items():
        print(f"\n{'─' * 70}")
        print(f"  {name}")
        print(f"{'─' * 70}")

        with tempfile.TemporaryDirectory() as tmpdir:
            pt_path = Path(tmpdir) / "model.py"
            tf_path = Path(tmpdir) / "model_tf.py"
            pt_path.write_text(pt_code)

            converted = converter.convert_file(str(pt_path), str(tf_path))

            # Print only class/function definitions and key lines
            for line in converted.split("\n"):
                # Skip helper functions at the bottom
                if line.strip().startswith("def nchw_to_nhwc") or \
                   line.strip().startswith("def nhwc_to_nchw"):
                    break
                print(f"  {line}")

    print(f"\n{'=' * 70}")
    print("  All models converted successfully!")
    print("=" * 70)
    print("\nTo run full validation with shape comparison:")
    print("  python -m pytorch2tensorflow.examples.validate_models")


if __name__ == "__main__":
    main()
