"""
Example: Converting a PyTorch ResNet BasicBlock to TensorFlow.

This demonstrates the full pipeline:
    1. Define a PyTorch model
    2. Convert model code to TensorFlow
    3. Convert weights
    4. Validate accuracy
    5. Export to PB
"""

# ─────────────────────────────────────────────
# Step 0: A sample PyTorch model (ResNet BasicBlock)
# ─────────────────────────────────────────────

PYTORCH_MODEL_CODE = '''
import torch
import torch.nn as nn
import torch.nn.functional as F


class BasicBlock(nn.Module):
    """ResNet Basic Block."""
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.downsample = downsample
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)
        return out


class SimpleResNet(nn.Module):
    """A simple ResNet-like model for demonstration."""

    def __init__(self, num_classes=10):
        super(SimpleResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.layer1 = BasicBlock(64, 64)
        self.layer2 = BasicBlock(64, 128, stride=2,
                                 downsample=nn.Sequential(
                                     nn.Conv2d(64, 128, 1, stride=2, bias=False),
                                     nn.BatchNorm2d(128)))

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x
'''


def run_example():
    """Run the conversion example."""
    import tempfile
    from pathlib import Path

    from pytorch2tensorflow.converter import ModelConverter

    # Step 1: Write PyTorch model to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        pt_model_path = Path(tmpdir) / "model.py"
        pt_model_path.write_text(PYTORCH_MODEL_CODE)

        # Step 2: Convert model code
        converter = ModelConverter()
        tf_model_path = Path(tmpdir) / "model_tf.py"
        converted_code = converter.convert_file(
            str(pt_model_path), str(tf_model_path)
        )

        print("=" * 60)
        print("Converted TensorFlow Model Code:")
        print("=" * 60)
        print(converted_code)
        print("=" * 60)

        # Step 3: Show weight conversion example (no actual weights needed)
        print("\nTo convert weights, run:")
        print(
            "  python -m pytorch2tensorflow convert-weights "
            "checkpoint.pth --tf-model model_tf.py -o weights/"
        )

        print("\nTo validate accuracy, run:")
        print(
            "  python -m pytorch2tensorflow validate "
            "--pt-model model.py --tf-model model_tf.py "
            "--pt-weights checkpoint.pth --input-shape 3,224,224"
        )

        print("\nTo export to PB for Ascend, run:")
        print(
            "  python -m pytorch2tensorflow export "
            "--tf-model model_tf.py --tf-weights weights/ "
            "--input-shape 3,224,224 -o export/"
        )


if __name__ == "__main__":
    run_example()
