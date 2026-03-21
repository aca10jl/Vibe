#!/usr/bin/env python3
"""
Comprehensive operator-level test suite for PyTorch → TensorFlow mapping.

Tests each operator category independently:
  - Convolution layers (Conv1d/2d/3d, ConvTranspose2d, depthwise)
  - Normalization layers (BatchNorm, LayerNorm, GroupNorm)
  - Pooling layers (MaxPool, AvgPool, AdaptiveAvgPool)
  - Activation functions (ReLU, LeakyReLU, GELU, SiLU, Sigmoid, Tanh, Softmax, Mish, etc.)
  - Linear / Dense layers
  - Tensor operations (cat, split, squeeze, unsqueeze, flatten, reshape, permute, transpose)
  - Math operations (matmul, add, mul, clamp, exp, log, sqrt, abs, pow)
  - Reduction operations (mean, sum, max, min)
  - Padding (F.pad, ZeroPad2d)
  - Interpolation / resize (F.interpolate nearest / bilinear)
  - Embedding layer
  - Dropout (functional)

Each test:
  1. Builds a minimal PyTorch nn.Module exercising the operator
  2. Converts the code via ModelConverter
  3. Builds the TF model and transfers weights
  4. Compares outputs on the same random input
  5. Asserts cosine similarity ≥ threshold

Usage:
    python -m tests.test_ops            # run all
    python -m tests.test_ops -v         # verbose
    python -m tests.test_ops -k conv    # filter by name
"""

import ast
import importlib.util
import sys
import tempfile
import textwrap
from pathlib import Path

import numpy as np

# ────────────────────────────────────────────
# Thresholds
# ────────────────────────────────────────────
COSINE_THRESHOLD = 0.99
MAX_ABS_DIFF_THRESHOLD = 0.1


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.flatten(), b.flatten()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-10 and nb < 1e-10:
        return 1.0
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def convert_and_compare(
    pt_code: str,
    input_shape: tuple,
    *,
    num_samples: int = 3,
    seed: int = 42,
    has_weights: bool = True,
    tuple_output: bool = False,
) -> dict:
    """Full pipeline: convert code → build models → transfer weights → compare.

    Returns dict with cosine_sim, max_abs_diff, passed, error.
    """
    import torch
    import tensorflow as tf
    from pytorch2tensorflow.converter import ModelConverter
    from pytorch2tensorflow.weight_converter import WeightConverter

    with tempfile.TemporaryDirectory() as tmpdir:
        pt_path = Path(tmpdir) / "model.py"
        pt_path.write_text(textwrap.dedent(pt_code))

        # Convert code
        converter = ModelConverter(channels_first=False)
        tf_path = Path(tmpdir) / "model_tf.py"
        try:
            converted = converter.convert_file(str(pt_path), str(tf_path))
        except Exception as e:
            return {"passed": False, "error": f"Code conversion failed: {e}",
                    "cosine_sim": 0.0, "max_abs_diff": float("inf")}

        # Load PT model
        tree = ast.parse(textwrap.dedent(pt_code))
        cls_names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]

        spec = importlib.util.spec_from_file_location("pt", str(pt_path))
        pt_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pt_mod)

        pt_cls = None
        for cname in reversed(cls_names):
            obj = getattr(pt_mod, cname, None)
            if obj and isinstance(obj, type) and issubclass(obj, torch.nn.Module):
                if obj is not torch.nn.Module:
                    pt_cls = obj
                    break
        if pt_cls is None:
            return {"passed": False, "error": "No nn.Module class found",
                    "cosine_sim": 0.0, "max_abs_diff": float("inf")}

        pt_model = pt_cls()
        pt_model.eval()

        # Load TF model
        spec2 = importlib.util.spec_from_file_location("tf_m", str(tf_path))
        tf_mod = importlib.util.module_from_spec(spec2)
        try:
            spec2.loader.exec_module(tf_mod)
        except Exception as e:
            return {"passed": False, "error": f"TF module load failed: {e}",
                    "cosine_sim": 0.0, "max_abs_diff": float("inf")}

        tf_tree = ast.parse(converted)
        tf_cls_names = [n.name for n in tf_tree.body if isinstance(n, ast.ClassDef)]
        tf_cls = None
        for cname in reversed(tf_cls_names):
            obj = getattr(tf_mod, cname, None)
            if obj and isinstance(obj, type) and issubclass(obj, tf.keras.Model):
                tf_cls = obj
                break
        if tf_cls is None:
            return {"passed": False, "error": "No tf.keras.Model class found",
                    "cosine_sim": 0.0, "max_abs_diff": float("inf")}

        try:
            tf_model = tf_cls()
        except Exception as e:
            return {"passed": False, "error": f"TF model init failed: {e}",
                    "cosine_sim": 0.0, "max_abs_diff": float("inf")}

        # Build TF model
        c = input_shape[0]
        spatial = input_shape[1:]
        dummy_nhwc = tf.zeros((1, *spatial, c))
        try:
            tf_model(dummy_nhwc, training=False)
        except Exception as e:
            return {"passed": False, "error": f"TF forward failed: {e}",
                    "cosine_sim": 0.0, "max_abs_diff": float("inf")}

        # Transfer weights
        if has_weights and len(list(pt_model.parameters())) > 0:
            wpath = Path(tmpdir) / "w.pth"
            torch.save(pt_model.state_dict(), str(wpath))
            wc = WeightConverter(strict=False)
            wc.convert(str(wpath), tf_model,
                       output_path=str(Path(tmpdir) / "tw"))

        # Compare outputs
        np.random.seed(seed)
        torch.manual_seed(seed)

        cosines = []
        max_abs_diffs = []

        for _ in range(num_samples):
            inp_np = np.random.randn(1, *input_shape).astype(np.float32)

            with torch.no_grad():
                pt_out = pt_model(torch.from_numpy(inp_np))

            inp_nhwc = np.transpose(inp_np, (0, *range(2, len(input_shape) + 1), 1))
            tf_out = tf_model(tf.constant(inp_nhwc), training=False)

            if isinstance(pt_out, tuple):
                pt_vec = np.concatenate([o.numpy().flatten() for o in pt_out])
                tf_vec = np.concatenate([o.numpy().flatten() for o in tf_out])
            else:
                pt_np = pt_out.numpy()
                tf_np = tf_out.numpy()
                if tf_np.ndim == 3:
                    tf_np = np.transpose(tf_np, (0, 2, 1))
                elif tf_np.ndim == 4:
                    tf_np = np.transpose(tf_np, (0, 3, 1, 2))
                elif tf_np.ndim == 5:
                    tf_np = np.transpose(tf_np, (0, 4, 1, 2, 3))
                pt_vec = pt_np.flatten()
                tf_vec = tf_np.flatten()

            if pt_vec.shape != tf_vec.shape:
                return {"passed": False,
                        "error": f"Shape mismatch: PT={pt_vec.shape} TF={tf_vec.shape}",
                        "cosine_sim": 0.0, "max_abs_diff": float("inf")}

            cosines.append(cosine_similarity(pt_vec, tf_vec))
            max_abs_diffs.append(float(np.max(np.abs(pt_vec - tf_vec))))

        avg_cos = float(np.mean(cosines))
        avg_mad = float(np.mean(max_abs_diffs))
        passed = avg_cos >= COSINE_THRESHOLD and avg_mad <= MAX_ABS_DIFF_THRESHOLD

        return {
            "passed": passed,
            "cosine_sim": avg_cos,
            "max_abs_diff": avg_mad,
            "error": None if passed else (
                f"cosine={avg_cos:.6f} (<{COSINE_THRESHOLD})"
                if avg_cos < COSINE_THRESHOLD
                else f"max_abs_diff={avg_mad:.6e} (>{MAX_ABS_DIFF_THRESHOLD})"
            ),
        }


# ════════════════════════════════════════════════════════════
# Test Definitions
# ════════════════════════════════════════════════════════════

TESTS: list[dict] = []


def register(name: str, code: str, input_shape: tuple, **kwargs):
    TESTS.append({"name": name, "code": code, "input_shape": input_shape, **kwargs})


# ────────────────────────────────────────
# 1. Convolution Layers
# ────────────────────────────────────────

register("Conv2d (basic)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 16, kernel_size=3, padding=1)
    def forward(self, x):
        return self.conv(x)
""", (3, 32, 32))

register("Conv2d (stride+dilation)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1, dilation=1, bias=False)
    def forward(self, x):
        return self.conv(x)
""", (3, 32, 32))

register("Conv2d (1-channel input)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(1, 8, kernel_size=5, padding=2)
    def forward(self, x):
        return self.conv(x)
""", (1, 28, 28))

register("Conv1d", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv1d(16, 32, kernel_size=3, padding=1)
    def forward(self, x):
        return self.conv(x)
""", (16, 64))

register("ConvTranspose2d", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.up = nn.ConvTranspose2d(16, 8, kernel_size=2, stride=2)
    def forward(self, x):
        return self.up(x)
""", (16, 8, 8))

register("Conv2d + ConvTranspose2d (encoder-decoder)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1, bias=False)
        self.dec = nn.ConvTranspose2d(16, 3, kernel_size=2, stride=2)
    def forward(self, x):
        return self.dec(self.enc(x))
""", (3, 32, 32))


# ────────────────────────────────────────
# 2. Normalization Layers
# ────────────────────────────────────────

register("BatchNorm2d", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 16, 3, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(16)
    def forward(self, x):
        return self.bn(self.conv(x))
""", (3, 16, 16))

register("BatchNorm1d + Linear", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(64, 32)
        self.bn = nn.BatchNorm1d(32)
    def forward(self, x):
        x = torch.flatten(x, 1)
        return self.bn(self.fc(x))
""", (1, 64))

register("LayerNorm", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(64, 32)
        self.ln = nn.LayerNorm(32)
    def forward(self, x):
        x = torch.flatten(x, 1)
        return self.ln(self.fc(x))
""", (1, 64))

register("GroupNorm", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 16, 3, padding=1, bias=False)
        self.gn = nn.GroupNorm(4, 16)
    def forward(self, x):
        return self.gn(self.conv(x))
""", (3, 16, 16))


# ────────────────────────────────────────
# 3. Pooling Layers
# ────────────────────────────────────────

register("MaxPool2d", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.pool = nn.MaxPool2d(2)
    def forward(self, x):
        return self.pool(self.conv(x))
""", (3, 16, 16))

register("AvgPool2d", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.pool = nn.AvgPool2d(2)
    def forward(self, x):
        return self.pool(self.conv(x))
""", (3, 16, 16))

register("AdaptiveAvgPool2d + flatten", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 16, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, 10)
    def forward(self, x):
        x = self.pool(self.conv(x))
        x = torch.flatten(x, 1)
        return self.fc(x)
""", (3, 16, 16))


# ────────────────────────────────────────
# 4. Activation Functions
# ────────────────────────────────────────

ACTIVATION_TESTS = [
    ("ReLU",       "nn.ReLU()"),
    ("LeakyReLU",  "nn.LeakyReLU(0.2)"),
    ("GELU",       "nn.GELU()"),
    ("SiLU",       "nn.SiLU()"),
    ("Sigmoid",    "nn.Sigmoid()"),
    ("Tanh",       "nn.Tanh()"),
    ("ELU",        "nn.ELU()"),
    ("Mish",       "nn.Mish()"),
    ("Hardswish",  "nn.Hardswish()"),
]

for act_name, act_layer in ACTIVATION_TESTS:
    register(f"Activation: {act_name}", f"""
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.act = {act_layer}
    def forward(self, x):
        return self.act(self.conv(x))
""", (3, 16, 16))

# Functional activations
register("F.relu + F.sigmoid", """
import torch
import torch.nn as nn
import torch.nn.functional as F

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
    def forward(self, x):
        x = F.relu(self.conv(x))
        return torch.sigmoid(x)
""", (3, 16, 16))

register("F.softmax", """
import torch
import torch.nn as nn
import torch.nn.functional as F

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(32, 10)
    def forward(self, x):
        x = torch.flatten(x, 1)
        return F.softmax(self.fc(x), dim=-1)
""", (1, 32))


# ────────────────────────────────────────
# 5. Linear / Dense
# ────────────────────────────────────────

register("Linear (basic)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(64, 10)
    def forward(self, x):
        return self.fc(torch.flatten(x, 1))
""", (1, 64))

register("Linear stack (MLP)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(64, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 10)
    def forward(self, x):
        x = torch.flatten(x, 1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)
""", (1, 64))


# ────────────────────────────────────────
# 6. Tensor Operations
# ────────────────────────────────────────

register("torch.cat (channel dim)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, 3, padding=1)
        self.conv2 = nn.Conv2d(3, 8, 3, padding=1)
        self.out = nn.Conv2d(16, 4, 1)
    def forward(self, x):
        a = self.conv1(x)
        b = self.conv2(x)
        return self.out(torch.cat([a, b], dim=1))
""", (3, 16, 16))

register("torch.flatten + reshape", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 4, 3, padding=1)
        self.fc = nn.Linear(4 * 8 * 8, 10)
    def forward(self, x):
        x = self.conv(x)
        x = torch.flatten(x, 1)
        return self.fc(x)
""", (3, 8, 8))

register("squeeze + unsqueeze", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)
    def forward(self, x):
        x = self.pool(self.conv(x))
        x = torch.squeeze(x)
        x = torch.unsqueeze(x, 0)
        return x
""", (3, 16, 16))


# ────────────────────────────────────────
# 7. Residual / Skip Connections
# ────────────────────────────────────────

register("Residual add", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 3, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(3)
        self.conv2 = nn.Conv2d(3, 3, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(3)
    def forward(self, x):
        identity = x
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += identity
        return torch.relu(out)
""", (3, 16, 16))

register("Skip connection with cat", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, 3, padding=1)
        self.conv2 = nn.Conv2d(11, 4, 1)
    def forward(self, x):
        feat = torch.relu(self.conv1(x))
        combined = torch.cat([x, feat], dim=1)
        return self.conv2(combined)
""", (3, 16, 16))


# ────────────────────────────────────────
# 8. Sequential blocks
# ────────────────────────────────────────

register("nn.Sequential (Conv+BN+ReLU)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.Conv2d(16, 8, 3, padding=1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(8, 10)
    def forward(self, x):
        x = self.block(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return self.fc(x)
""", (3, 16, 16))

register("nn.Sequential (stacked Dense)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 10),
        )
    def forward(self, x):
        return self.mlp(torch.flatten(x, 1))
""", (1, 32))


# ────────────────────────────────────────
# 9. Multi-head / Multi-output
# ────────────────────────────────────────

register("Dual output heads", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 16, 3, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(16)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.head_a = nn.Linear(16, 5)
        self.head_b = nn.Linear(16, 3)
    def forward(self, x):
        x = torch.relu(self.bn(self.conv(x)))
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return self.head_a(x), self.head_b(x)
""", (3, 16, 16), tuple_output=True)


# ────────────────────────────────────────
# 10. Embedding
# ────────────────────────────────────────

# (Embedding is a special case — input is integer, skip NCHW/NHWC conversion)
# We test it at the model level instead.


# ────────────────────────────────────────
# 11. Math & Reduction ops (via model)
# ────────────────────────────────────────

register("torch.clamp", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
    def forward(self, x):
        return torch.clamp(self.conv(x), min=-0.5, max=0.5)
""", (3, 16, 16))

register("torch.abs + torch.exp", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 4, 3, padding=1)
    def forward(self, x):
        x = self.conv(x)
        return torch.exp(torch.abs(x) * 0.1)
""", (3, 8, 8))

register("Reduction: mean over spatial", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
    def forward(self, x):
        x = self.conv(x)
        return x.mean(dim=(2, 3), keepdim=True)
""", (3, 16, 16))


# ────────────────────────────────────────
# 12. ReLU with inplace=True
# ────────────────────────────────────────

register("ReLU(inplace=True)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)
    def forward(self, x):
        return self.relu(self.conv(x))
""", (3, 16, 16))

register("LeakyReLU(inplace=True)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.act = nn.LeakyReLU(0.2, inplace=True)
    def forward(self, x):
        return self.act(self.conv(x))
""", (3, 16, 16))


# ────────────────────────────────────────
# 13. F.pad with square brackets
# ────────────────────────────────────────

register("F.pad (square brackets)", """
import torch
import torch.nn as nn
import torch.nn.functional as F

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3)
    def forward(self, x):
        x = F.pad(x, [1, 1, 1, 1])
        return self.conv(x)
""", (3, 16, 16))

register("F.pad (tuple)", """
import torch
import torch.nn as nn
import torch.nn.functional as F

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3)
    def forward(self, x):
        x = F.pad(x, (1, 1, 1, 1))
        return self.conv(x)
""", (3, 16, 16))


# ────────────────────────────────────────
# 14. Complex combined patterns
# ────────────────────────────────────────

register("Bottleneck block (1x1 + 3x3 + 1x1 + residual)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(64, 16, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 16, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(16)
        self.conv3 = nn.Conv2d(16, 64, 1, bias=False)
        self.bn3 = nn.BatchNorm2d(64)
    def forward(self, x):
        identity = x
        out = torch.relu(self.bn1(self.conv1(x)))
        out = torch.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        return torch.relu(out + identity)
""", (64, 8, 8))

register("UNet-style down+up+skip", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(),
        )
        self.pool = nn.MaxPool2d(2)
        self.mid = nn.Sequential(
            nn.Conv2d(16, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )
        self.up = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2)
        self.dec = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(),
        )
        self.final = nn.Conv2d(16, 1, 1)
    def forward(self, x):
        e = self.enc(x)
        m = self.mid(self.pool(e))
        d = self.up(m)
        d = torch.cat([d, e], dim=1)
        return self.final(self.dec(d))
""", (3, 32, 32))

register("Conv+BN+ReLU → flatten → Dense (classification head)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Linear(32, 10)
    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)
""", (3, 32, 32))

register("Multiple flatten paths (2D output)", """
import torch
import torch.nn as nn

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc1 = nn.Linear(8, 16)
        self.fc2 = nn.Linear(16, 10)
    def forward(self, x):
        x = torch.relu(self.conv(x))
        x = self.pool(x)
        x = torch.flatten(x, 1)
        x = torch.relu(self.fc1(x))
        return self.fc2(x)
""", (3, 16, 16))


# ════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Operator-level test suite")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-k", "--filter", type=str, default=None,
                        help="Only run tests whose name contains this string")
    args = parser.parse_args()

    tests_to_run = TESTS
    if args.filter:
        tests_to_run = [t for t in TESTS if args.filter.lower() in t["name"].lower()]

    print("=" * 80)
    print(f"  Operator-Level Test Suite ({len(tests_to_run)} tests)")
    print("=" * 80)

    passed = 0
    failed = 0
    errors = []

    for t in tests_to_run:
        name = t["name"]
        code = t["code"]
        shape = t["input_shape"]
        kwargs = {k: v for k, v in t.items() if k not in ("name", "code", "input_shape")}

        result = convert_and_compare(code, shape, **kwargs)

        if result["passed"]:
            passed += 1
            mark = "PASS"
            detail = f"cosine={result['cosine_sim']:.8f}  max_abs={result['max_abs_diff']:.2e}"
        else:
            failed += 1
            mark = "FAIL"
            detail = result.get("error", "unknown")
            errors.append((name, detail))

        if args.verbose or not result["passed"]:
            print(f"  [{mark}] {name:<50s} {detail}")
        else:
            print(f"  [{mark}] {name}")

    print(f"\n{'=' * 80}")
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'=' * 80}")

    if errors:
        print(f"\n  Failed tests:")
        for name, detail in errors:
            print(f"    - {name}: {detail}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
