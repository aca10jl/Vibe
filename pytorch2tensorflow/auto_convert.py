"""
One-Click Auto Conversion: PyTorch → TensorFlow → PB (Ascend-Ready)

Automatically detects model input/output signatures, converts model code
and weights, validates accuracy, exports to PB, and checks Ascend
operator compatibility — all in a single function call.

Usage:
    from pytorch2tensorflow.auto_convert import auto_convert

    result = auto_convert(
        pt_model_path="model.py",
        pt_weights_path="weights.pth",
        input_shapes=[(3, 224, 224)],
        output_dir="output/",
    )
"""

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AutoConvertResult:
    """Result of the full auto-conversion pipeline."""

    success: bool
    tf_model_path: str = ""
    tf_weights_path: str = ""
    pb_path: str = ""
    saved_model_dir: str = ""
    atc_command: str = ""
    validation_passed: bool = False
    ascend_compatible: bool = False
    cosine_similarity: float = 0.0
    input_nodes: list = field(default_factory=list)
    output_nodes: list = field(default_factory=list)
    ascend_report: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        lines = [
            f"Auto-Conversion {status}",
            f"  TF Model:      {self.tf_model_path}",
            f"  TF Weights:    {self.tf_weights_path}",
            f"  Frozen PB:     {self.pb_path}",
            f"  Validation:    {'PASS' if self.validation_passed else 'FAIL'}"
            f" (cosine={self.cosine_similarity:.6f})",
            f"  Ascend:        {'PASS' if self.ascend_compatible else 'FAIL'}",
        ]
        if self.ascend_report.get("unsupported_ops"):
            lines.append(
                f"  Unsupported:   {self.ascend_report['unsupported_ops']}"
            )
        if self.errors:
            lines.append(f"  Errors:")
            for e in self.errors:
                lines.append(f"    - {e}")
        return "\n".join(lines)


def auto_convert(
    pt_model_path: str,
    pt_weights_path: Optional[str] = None,
    input_shapes: Optional[list[tuple]] = None,
    output_dir: str = "conversion_output",
    channels_first: bool = False,
    num_classes: Optional[int] = None,
    validate: bool = True,
    export_pb: bool = True,
    soc_version: str = "Ascend910B4",
    verbose: bool = True,
) -> AutoConvertResult:
    """One-click full auto-conversion pipeline.

    Auto-detects model structure, converts code + weights, validates
    accuracy, and exports PB for Ascend deployment.

    Args:
        pt_model_path: Path to PyTorch model .py file.
        pt_weights_path: Path to .pth weights (optional).
        input_shapes: Input shapes as list of (C, H, W) tuples.
            If None, attempts to auto-detect from model code.
        output_dir: Directory for all output files.
        channels_first: Keep NCHW format (matching PyTorch).
        num_classes: Number of output classes (for auto-detection).
        validate: Whether to run accuracy validation.
        export_pb: Whether to export PB and check Ascend compatibility.
        soc_version: Target Ascend SoC version.
        verbose: Print progress messages.

    Returns:
        AutoConvertResult with all paths and metrics.
    """
    result = AutoConvertResult(success=False)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    def _print(msg: str):
        if verbose:
            print(msg)

    # ──────────────────────────────────────────────
    # Step 1: Detect model info from source code
    # ──────────────────────────────────────────────
    _print("=" * 60)
    _print("[1/5] Analyzing PyTorch model...")
    _print("=" * 60)

    pt_source = Path(pt_model_path).read_text(encoding="utf-8")
    model_info = _detect_model_info(pt_source, pt_model_path)
    _print(f"  Model class:  {model_info['class_name']}")
    _print(f"  Forward args: {model_info['forward_args']}")

    if input_shapes is None:
        input_shapes = model_info.get("input_shapes")
        if input_shapes:
            _print(f"  Auto-detected input shapes: {input_shapes}")
        else:
            _print("  WARNING: Could not auto-detect input shapes.")
            _print("  Using default: [(3, 224, 224)]")
            input_shapes = [(3, 224, 224)]

    # ──────────────────────────────────────────────
    # Step 2: Convert model code
    # ──────────────────────────────────────────────
    _print(f"\n{'=' * 60}")
    _print("[2/5] Converting model code → TensorFlow...")
    _print("=" * 60)

    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(channels_first=channels_first)
    tf_model_path = str(out_path / "model_tf.py")
    converted_code = converter.convert_file(pt_model_path, tf_model_path)
    result.tf_model_path = tf_model_path

    line_count = converted_code.count("\n")
    _print(f"  Output: {tf_model_path} ({line_count} lines)")

    # ──────────────────────────────────────────────
    # Step 3: Load models & convert weights
    # ──────────────────────────────────────────────
    _print(f"\n{'=' * 60}")
    _print("[3/5] Loading models & converting weights...")
    _print("=" * 60)

    try:
        import torch
        import tensorflow as tf

        # Load PyTorch model
        pt_model = _load_pytorch_model(pt_model_path, pt_weights_path)
        _print(f"  PT params: {sum(p.numel() for p in pt_model.parameters()):,}")

        # Load TF model
        tf_model = _load_tf_model(tf_model_path, input_shapes, channels_first)
        tf_param_count = sum(np.prod(w.shape) for w in tf_model.weights)
        _print(f"  TF params: {tf_param_count:,}")

        # Convert weights if available
        if pt_weights_path:
            from pytorch2tensorflow.weight_converter import WeightConverter

            weight_converter = WeightConverter(strict=False)
            tf_weights_path = str(out_path / "weights.weights.h5")
            stats = weight_converter.convert(
                pt_weights_path, tf_model, output_path=tf_weights_path,
            )
            result.tf_weights_path = tf_weights_path
            _print(
                f"  Weights: {stats['assigned']}/{stats['total_pytorch_weights']} mapped"
            )
        else:
            _print("  No weights provided, skipping weight conversion.")

    except Exception as e:
        result.errors.append(f"Model loading failed: {e}")
        _print(f"  ERROR: {e}")
        return result

    # ──────────────────────────────────────────────
    # Step 4: Validate accuracy
    # ──────────────────────────────────────────────
    if validate and pt_weights_path:
        _print(f"\n{'=' * 60}")
        _print("[4/5] Validating accuracy...")
        _print("=" * 60)

        try:
            from pytorch2tensorflow.validator import AccuracyValidator

            nchw_to_nhwc = not channels_first
            validator = AccuracyValidator(
                atol=1e-4, rtol=1e-3, cosine_threshold=0.99,
            )
            val_result = validator.validate(
                pt_model, tf_model, input_shapes,
                num_samples=5, nchw_to_nhwc=nchw_to_nhwc,
            )
            result.validation_passed = val_result.passed
            result.cosine_similarity = val_result.cosine_similarity
            _print(f"  Max abs diff:  {val_result.max_abs_diff:.2e}")
            _print(f"  Cosine sim:    {val_result.cosine_similarity:.6f}")
            _print(
                f"  Result:        {'PASS' if val_result.passed else 'FAIL'}"
            )
        except Exception as e:
            result.errors.append(f"Validation failed: {e}")
            _print(f"  ERROR: {e}")
    else:
        _print(f"\n[4/5] Skipping validation (no weights).")

    # ──────────────────────────────────────────────
    # Step 5: Export PB & check Ascend compatibility
    # ──────────────────────────────────────────────
    if export_pb:
        _print(f"\n{'=' * 60}")
        _print("[5/5] Exporting PB & checking Ascend compatibility...")
        _print("=" * 60)

        try:
            from pytorch2tensorflow.exporter import PBExporter

            exporter = PBExporter(channels_first=channels_first)

            # Determine TF input shapes
            if channels_first:
                tf_input_shapes = input_shapes
            else:
                tf_input_shapes = [
                    (s[1], s[2], s[0]) if len(s) == 3 else s
                    for s in input_shapes
                ]

            export_result = exporter.export_and_verify(
                tf_model, str(out_path), tf_input_shapes,
                soc_version=soc_version,
            )

            result.pb_path = export_result["frozen_graph_path"]
            result.saved_model_dir = export_result["saved_model_dir"]
            result.atc_command = export_result["atc_command"]
            result.input_nodes = export_result.get("input_nodes", [])
            result.ascend_report = export_result["ascend_compatibility"]
            result.ascend_compatible = export_result["ascend_compatibility"][
                "compatible"
            ]

            import os
            pb_size = os.path.getsize(result.pb_path)
            _print(f"  PB file:     {result.pb_path} ({pb_size / 1024:.0f} KB)")
            _print(f"  Input nodes: {result.input_nodes}")

            compat = result.ascend_report
            _print(
                f"  Ascend:      "
                f"{'PASS' if result.ascend_compatible else 'FAIL'} "
                f"({compat['unique_ops']} op types)"
            )
            if compat.get("unsupported_ops"):
                _print(f"  Unsupported: {compat['unsupported_ops']}")

            _print(f"\n  ATC command:")
            for line in result.atc_command.split("\n"):
                _print(f"    {line}")

        except Exception as e:
            result.errors.append(f"Export failed: {e}")
            _print(f"  ERROR: {e}")
    else:
        _print(f"\n[5/5] Skipping PB export.")

    # ──────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────
    result.success = len(result.errors) == 0
    _print(f"\n{'=' * 60}")
    _print(str(result))
    _print("=" * 60)

    return result


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────


def _detect_model_info(source: str, model_path: str) -> dict:
    """Detect model class name, forward args, and input shapes from source."""
    import ast
    import re

    info = {
        "class_name": None,
        "forward_args": [],
        "input_shapes": None,
    }

    # Parse AST to find the model class and forward signature
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Attribute):
                    base_name = ast.dump(base)
                elif isinstance(base, ast.Name):
                    base_name = base.id
                if "Module" in base_name:
                    info["class_name"] = node.name
                    # Find forward method
                    for item in node.body:
                        if (
                            isinstance(item, ast.FunctionDef)
                            and item.name == "forward"
                        ):
                            args = [
                                a.arg
                                for a in item.args.args
                                if a.arg != "self"
                            ]
                            info["forward_args"] = args
                    break
        if info["class_name"]:
            break

    # Try to detect input shapes from __main__ block
    shape_match = re.search(
        r"torch\.randn\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
        source,
    )
    if shape_match:
        _, c, h, w = (int(x) for x in shape_match.groups())
        info["input_shapes"] = [(c, h, w)]

    return info


def _load_pytorch_model(model_path: str, weights_path: Optional[str] = None):
    """Load a PyTorch model from .py file."""
    import torch

    spec = importlib.util.spec_from_file_location("pt_model_mod", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the main model class (last nn.Module subclass defined)
    model_cls = None
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, torch.nn.Module)
            and obj is not torch.nn.Module
        ):
            model_cls = obj

    if model_cls is None:
        raise ValueError(f"No nn.Module subclass found in {model_path}")

    model = model_cls()

    if weights_path:
        state_dict = torch.load(
            weights_path, map_location="cpu", weights_only=False,
        )
        if isinstance(state_dict, dict):
            for key in ("state_dict", "model_state_dict", "model"):
                if key in state_dict:
                    state_dict = state_dict[key]
                    break
        model.load_state_dict(state_dict, strict=False)

    model.eval()
    return model


def _load_tf_model(
    model_path: str,
    input_shapes: list[tuple],
    channels_first: bool = False,
):
    """Load a TF model from .py file and build with dummy input."""
    import tensorflow as tf

    spec = importlib.util.spec_from_file_location("tf_model_mod", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the main model class (last tf.keras.Model subclass)
    model_cls = None
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, tf.keras.Model)
            and obj is not tf.keras.Model
        ):
            model_cls = obj

    if model_cls is None:
        raise ValueError(f"No tf.keras.Model subclass found in {model_path}")

    model = model_cls()

    # Build model with dummy inputs
    dummy_inputs = []
    for shape in input_shapes:
        if channels_first:
            dummy_inputs.append(tf.zeros((1, *shape)))
        elif len(shape) == 3:
            # CHW → HWC
            dummy_inputs.append(tf.zeros((1, shape[1], shape[2], shape[0])))
        else:
            dummy_inputs.append(tf.zeros((1, *shape)))

    if len(dummy_inputs) == 1:
        model(dummy_inputs[0], training=False)
    else:
        model(dummy_inputs, training=False)

    return model
