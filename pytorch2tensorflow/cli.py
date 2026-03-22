"""
Command-Line Interface for PyTorch → TensorFlow Converter

Usage:
    # Convert model code
    python -m pytorch2tensorflow convert-model model.py -o tf_model.py

    # Convert weights
    python -m pytorch2tensorflow convert-weights ckpt.pth --tf-model tf_model.py -o weights/

    # Validate accuracy
    python -m pytorch2tensorflow validate --pt-model model.py --tf-model tf_model.py \\
        --pt-weights ckpt.pth --input-shape 3,224,224

    # Export to PB
    python -m pytorch2tensorflow export --tf-model tf_model.py \\
        --tf-weights weights/ --input-shape 3,224,224 -o output/

    # Full pipeline
    python -m pytorch2tensorflow full --pt-model model.py --pt-weights ckpt.pth \\
        --input-shape 3,224,224 -o output/
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("pytorch2tensorflow")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_convert_model(args: argparse.Namespace) -> None:
    """Convert PyTorch model .py file to TensorFlow."""
    from pytorch2tensorflow.converter import ModelConverter

    converter = ModelConverter(
        add_channel_convert=not args.no_channel_convert,
        channels_first=args.channels_first,
    )
    output = args.output or args.input.replace(".py", "_tf.py")

    print(f"Converting model: {args.input} → {output}")
    result = converter.convert_file(args.input, output)
    print(f"Model converted successfully. Output: {output}")
    print(f"Output size: {len(result)} characters, {result.count(chr(10))} lines")


def cmd_convert_weights(args: argparse.Namespace) -> None:
    """Convert PyTorch .pth weights to TensorFlow format."""
    from pytorch2tensorflow.weight_converter import WeightConverter

    converter = WeightConverter(strict=not args.no_strict)

    if args.numpy_only:
        # Convert to numpy arrays without requiring a TF model
        output_dir = args.output or "converted_weights"
        print(f"Converting weights to numpy: {args.input} → {output_dir}")
        converted = converter.convert_state_dict_to_numpy(args.input, output_dir)
        print(f"Converted {len(converted)} weight tensors to numpy format.")
        for name, arr in list(converted.items())[:10]:
            print(f"  {name}: shape={arr.shape}, dtype={arr.dtype}")
        if len(converted) > 10:
            print(f"  ... and {len(converted) - 10} more")
    else:
        if not args.tf_model:
            print("Error: --tf-model required when not using --numpy-only")
            sys.exit(1)

        print(f"Converting weights: {args.input}")
        print(f"TF model: {args.tf_model}")

        # Import and build TF model
        tf_model = _load_tf_model(
            args.tf_model, args.input_shape,
            class_name=getattr(args, "tf_class_name", None),
            model_args=getattr(args, "model_args", None),
        )

        output_path = args.output or "converted_weights"
        stats = converter.convert(args.input, tf_model, output_path)
        print(f"Weight conversion complete:")
        print(f"  Assigned: {stats['assigned']}/{stats['total_pytorch_weights']}")
        print(f"  Skipped:  {stats['skipped']}")
        print(f"  Errors:   {stats['errors']}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate output accuracy between PyTorch and TF models."""
    from pytorch2tensorflow.validator import AccuracyValidator

    input_shapes = [tuple(int(d) for d in s.split(",")) for s in args.input_shape]

    validator = AccuracyValidator(
        atol=args.atol,
        rtol=args.rtol,
        cosine_threshold=args.cosine_threshold,
    )

    # Load models
    pt_model = _load_pytorch_model(
        args.pt_model, args.pt_weights,
        class_name=getattr(args, "class_name", None),
        model_args=getattr(args, "model_args", None),
    )
    tf_model = _load_tf_model(
        args.tf_model, input_shapes[0], args.tf_weights,
        class_name=getattr(args, "tf_class_name", None),
        model_args=getattr(args, "model_args", None),
    )

    print("Running validation...")
    result = validator.validate(
        pt_model,
        tf_model,
        input_shapes,
        num_samples=args.num_samples,
    )
    print(result)

    if not result.passed:
        sys.exit(1)


def cmd_export(args: argparse.Namespace) -> None:
    """Export TF model to PB format."""
    from pytorch2tensorflow.exporter import PBExporter

    input_shapes = [tuple(int(d) for d in s.split(",")) for s in args.input_shape]

    exporter = PBExporter()

    # Load TF model
    tf_model = _load_tf_model(
        args.tf_model, input_shapes[0], args.tf_weights,
        class_name=getattr(args, "tf_class_name", None),
        model_args=getattr(args, "model_args", None),
    )

    output_dir = args.output or "export_output"
    batch_size = getattr(args, "batch_size", 1) or 1
    results = exporter.export_and_verify(
        tf_model,
        output_dir,
        input_shapes,
        soc_version=args.soc_version,
        batch_size=batch_size,
    )

    print(f"\nExport Results:")
    print(f"  SavedModel:    {results['saved_model_dir']}")
    print(f"  Frozen Graph:  {results['frozen_graph_path']}")
    print(f"  Batch Size:    {batch_size}")
    print(f"  Ascend Compat: {'PASS' if results['ascend_compatibility']['compatible'] else 'FAIL'}")
    print(f"\nATC Command:")
    print(f"  {results['atc_command']}")

    if results["ascend_compatibility"]["warnings"]:
        print(f"\nWarnings:")
        for w in results["ascend_compatibility"]["warnings"]:
            print(f"  - {w}")


def cmd_auto(args: argparse.Namespace) -> None:
    """One-click auto-conversion pipeline."""
    from pytorch2tensorflow.auto_convert import auto_convert

    input_shapes = None
    if args.input_shape:
        input_shapes = [
            tuple(int(d) for d in s.split(",")) for s in args.input_shape
        ]

    result = auto_convert(
        pt_model_path=args.pt_model,
        pt_weights_path=args.pt_weights,
        input_shapes=input_shapes,
        output_dir=args.output or "conversion_output",
        channels_first=getattr(args, "channels_first", False),
        soc_version=args.soc_version,
        verbose=True,
    )

    if not result.success:
        sys.exit(1)


def cmd_full_pipeline(args: argparse.Namespace) -> None:
    """Run the complete conversion pipeline."""
    from pytorch2tensorflow.converter import ModelConverter
    from pytorch2tensorflow.weight_converter import WeightConverter
    from pytorch2tensorflow.validator import AccuracyValidator
    from pytorch2tensorflow.exporter import PBExporter

    input_shapes = [tuple(int(d) for d in s.split(",")) for s in args.input_shape]
    output_dir = Path(args.output or "conversion_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Convert model code
    print("=" * 60)
    print("Step 1: Converting model code...")
    print("=" * 60)
    channels_first = getattr(args, "channels_first", False)
    model_converter = ModelConverter(channels_first=channels_first)
    tf_model_path = str(output_dir / "model_tf.py")
    model_converter.convert_file(args.pt_model, tf_model_path)
    print(f"  Model code saved to {tf_model_path}")

    # Step 2: Load models and convert weights
    print("\n" + "=" * 60)
    print("Step 2: Converting weights...")
    print("=" * 60)
    pt_weights = getattr(args, "pt_weights", None)
    pt_model = _load_pytorch_model(
        args.pt_model, pt_weights,
        class_name=getattr(args, "class_name", None),
        model_args=getattr(args, "model_args", None),
    )
    tf_model = _load_tf_model(
        tf_model_path, input_shapes[0],
        class_name=getattr(args, "class_name", None),
        model_args=getattr(args, "model_args", None),
    )

    weight_converter = WeightConverter(strict=False)
    tf_weights_path = str(output_dir / "weights")
    if pt_weights:
        stats = weight_converter.convert(pt_weights, tf_model, tf_weights_path)
    else:
        print("  No weights file provided, using random initialization")
        stats = weight_converter.convert_from_state_dict(
            pt_model.state_dict(), tf_model, tf_weights_path,
        )
    print(f"  Assigned: {stats['assigned']}/{stats['total_pytorch_weights']}")

    # Step 3: Validate accuracy
    print("\n" + "=" * 60)
    print("Step 3: Validating accuracy...")
    print("=" * 60)
    validator = AccuracyValidator()
    result = validator.validate(pt_model, tf_model, input_shapes)
    print(result)

    # Step 4: Export to PB
    print("\n" + "=" * 60)
    print("Step 4: Exporting to PB...")
    print("=" * 60)
    exporter = PBExporter()
    batch_size = getattr(args, "batch_size", 1) or 1
    export_results = exporter.export_and_verify(
        tf_model,
        str(output_dir / "export"),
        input_shapes,
        soc_version=args.soc_version,
        batch_size=batch_size,
    )
    print(f"  Frozen Graph:  {export_results['frozen_graph_path']}")
    print(f"  Ascend Compat: {'PASS' if export_results['ascend_compatibility']['compatible'] else 'FAIL'}")
    print(f"\n  ATC Command:\n  {export_results['atc_command']}")

    # Summary
    print("\n" + "=" * 60)
    print("Conversion Pipeline Complete!")
    print("=" * 60)
    print(f"  Model code:    {tf_model_path}")
    print(f"  TF weights:    {tf_weights_path}")
    print(f"  Frozen graph:  {export_results['frozen_graph_path']}")
    print(f"  SavedModel:    {export_results['saved_model_dir']}")
    print(f"  Accuracy:      {'PASS' if result.passed else 'FAIL'}")
    print(f"  Ascend:        {'PASS' if export_results['ascend_compatibility']['compatible'] else 'FAIL'}")


# ────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────

def _load_pytorch_model(
    model_path: str,
    weights_path: str = None,
    class_name: str = None,
    model_args: str = None,
):
    """Dynamically load a PyTorch model from a .py file.

    Args:
        model_path: Path to the PyTorch model .py file.
        weights_path: Optional path to .pth weights file.
        class_name: Optional class name to use. If None, uses the first
            nn.Module subclass found in the file.
        model_args: Optional arguments string for model instantiation,
            e.g. "num_classes=10, in_channels=3".
    """
    import importlib.util
    import torch

    spec = importlib.util.spec_from_file_location("pt_model", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the model class
    model_cls = None
    if class_name:
        # Use the specified class name
        model_cls = getattr(module, class_name, None)
        if model_cls is None:
            available = [
                name for name in dir(module)
                if isinstance(getattr(module, name), type)
                and issubclass(getattr(module, name), torch.nn.Module)
                and getattr(module, name) is not torch.nn.Module
            ]
            raise ValueError(
                f"Class '{class_name}' not found in {model_path}. "
                f"Available nn.Module classes: {available}"
            )
    else:
        # Auto-detect: use first nn.Module subclass
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, torch.nn.Module)
                and obj is not torch.nn.Module
            ):
                model_cls = obj
                break

    if model_cls is None:
        raise ValueError(f"No nn.Module subclass found in {model_path}")

    # Instantiate model with optional arguments
    if model_args:
        model = eval(f"model_cls({model_args})")
    else:
        model = model_cls()

    if weights_path:
        state_dict = torch.load(weights_path, map_location="cpu", weights_only=False)
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
    input_shape=None,
    weights_path: str = None,
    class_name: str = None,
    model_args: str = None,
):
    """Dynamically load a TF model from a .py file.

    Args:
        model_path: Path to the TF model .py file.
        input_shape: Input shape for building the model.
        weights_path: Optional path to saved TF weights.
        class_name: Optional class name to use. If None, uses the first
            tf.keras.Model subclass found in the file.
        model_args: Optional arguments string for model instantiation.
    """
    import importlib.util
    import tensorflow as tf

    spec = importlib.util.spec_from_file_location("tf_model", model_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the model class
    model_cls = None
    if class_name:
        model_cls = getattr(module, class_name, None)
        if model_cls is None:
            available = [
                name for name in dir(module)
                if isinstance(getattr(module, name), type)
                and issubclass(getattr(module, name), tf.keras.Model)
                and getattr(module, name) is not tf.keras.Model
            ]
            raise ValueError(
                f"Class '{class_name}' not found in {model_path}. "
                f"Available tf.keras.Model classes: {available}"
            )
    else:
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, tf.keras.Model)
                and obj is not tf.keras.Model
            ):
                model_cls = obj
                break

    if model_cls is None:
        raise ValueError(f"No tf.keras.Model subclass found in {model_path}")

    if model_args:
        model = eval(f"model_cls({model_args})")
    else:
        model = model_cls()

    # Build model with dummy input
    if input_shape:
        if isinstance(input_shape, (list, tuple)) and isinstance(input_shape[0], int):
            # Single shape like (3, 224, 224) → NHWC (224, 224, 3)
            if len(input_shape) == 3:
                nhwc_shape = (input_shape[1], input_shape[2], input_shape[0])
            else:
                nhwc_shape = input_shape
            dummy = tf.zeros((1, *nhwc_shape))
            model(dummy, training=False)

    if weights_path:
        model.load_weights(weights_path)

    return model


# ────────────────────────────────────────
# Argument parser
# ────────────────────────────────────────

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytorch2tensorflow",
        description="PyTorch to TensorFlow Model Converter for Ascend Deployment",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── convert-model ──
    p_model = subparsers.add_parser("convert-model", help="Convert PyTorch model code to TF")
    p_model.add_argument("input", help="Path to PyTorch model .py file")
    p_model.add_argument("-o", "--output", help="Output TF model .py file path")
    p_model.add_argument(
        "--no-channel-convert", action="store_true",
        help="Skip adding channel conversion helpers",
    )
    p_model.add_argument(
        "--channels-first", action="store_true",
        help="Keep NCHW data format (matching PyTorch). Layers will use "
             "data_format='channels_first' so tensor shapes stay identical.",
    )

    # ── convert-weights ──
    p_weights = subparsers.add_parser("convert-weights", help="Convert .pth weights to TF")
    p_weights.add_argument("input", help="Path to PyTorch .pth checkpoint")
    p_weights.add_argument("--tf-model", help="Path to TF model .py file")
    p_weights.add_argument("--input-shape", nargs="+", help="Input shape (e.g., 3,224,224)")
    p_weights.add_argument("-o", "--output", help="Output path for TF weights")
    p_weights.add_argument("--numpy-only", action="store_true", help="Export as numpy only")
    p_weights.add_argument("--no-strict", action="store_true", help="Non-strict weight matching")

    # ── convert-weights ── (add class/args options)
    p_weights.add_argument(
        "--tf-class-name", help="TF model class name to use (default: auto-detect)")
    p_weights.add_argument(
        "--model-args", help="Model instantiation arguments, e.g. 'num_classes=10'")

    # ── validate ──
    p_val = subparsers.add_parser("validate", help="Validate PT↔TF output accuracy")
    p_val.add_argument("--pt-model", required=True, help="PyTorch model .py path")
    p_val.add_argument("--tf-model", required=True, help="TF model .py path")
    p_val.add_argument("--pt-weights", help="PyTorch weights .pth path")
    p_val.add_argument("--tf-weights", help="TF weights path")
    p_val.add_argument("--input-shape", nargs="+", required=True, help="Input shapes")
    p_val.add_argument("--num-samples", type=int, default=5, help="Number of test samples")
    p_val.add_argument("--atol", type=float, default=1e-5, help="Absolute tolerance")
    p_val.add_argument("--rtol", type=float, default=1e-4, help="Relative tolerance")
    p_val.add_argument("--cosine-threshold", type=float, default=0.9999)
    p_val.add_argument(
        "--class-name", help="PyTorch model class name to use (default: auto-detect)")
    p_val.add_argument(
        "--tf-class-name", help="TF model class name to use (default: auto-detect)")
    p_val.add_argument(
        "--model-args", help="Model instantiation arguments, e.g. 'num_classes=10, in_channels=3'")

    # ── export ──
    p_export = subparsers.add_parser("export", help="Export TF model to PB format")
    p_export.add_argument("--tf-model", required=True, help="TF model .py path")
    p_export.add_argument("--tf-weights", help="TF weights path")
    p_export.add_argument("--input-shape", nargs="+", required=True, help="Input shapes")
    p_export.add_argument("-o", "--output", help="Output directory")
    p_export.add_argument("--soc-version", default="Ascend310", help="Ascend SoC version")
    p_export.add_argument(
        "--tf-class-name", help="TF model class name to use (default: auto-detect)")
    p_export.add_argument(
        "--model-args", help="Model instantiation arguments, e.g. 'num_classes=10'")
    p_export.add_argument(
        "--batch-size", type=int, default=1,
        help="Batch size (N) for export. Default: 1")

    # ── auto ──
    p_auto = subparsers.add_parser(
        "auto", help="One-click auto-conversion (auto-detect inputs/outputs)"
    )
    p_auto.add_argument("--pt-model", required=True, help="PyTorch model .py path")
    p_auto.add_argument("--pt-weights", help="PyTorch weights .pth path (optional)")
    p_auto.add_argument("--input-shape", nargs="+", help="Input shapes (e.g., 3,224,224). Auto-detected if omitted.")
    p_auto.add_argument("-o", "--output", help="Output directory")
    p_auto.add_argument("--soc-version", default="Ascend310", help="Ascend SoC version")
    p_auto.add_argument(
        "--channels-first", action="store_true",
        help="Keep NCHW data format (matching PyTorch)",
    )
    p_auto.add_argument(
        "--class-name", help="PyTorch model class name to use (default: auto-detect)")
    p_auto.add_argument(
        "--model-args", help="Model instantiation arguments, e.g. 'num_classes=10'")
    p_auto.add_argument(
        "--batch-size", type=int, default=1,
        help="Batch size (N) for export. Default: 1")

    # ── full ──
    p_full = subparsers.add_parser("full", help="Run complete conversion pipeline")
    p_full.add_argument("--pt-model", required=True, help="PyTorch model .py path")
    p_full.add_argument("--pt-weights", help="PyTorch weights .pth path (random init if omitted)")
    p_full.add_argument("--input-shape", nargs="+", required=True, help="Input shapes")
    p_full.add_argument("-o", "--output", help="Output directory")
    p_full.add_argument("--soc-version", default="Ascend310", help="Ascend SoC version")
    p_full.add_argument(
        "--channels-first", action="store_true",
        help="Keep NCHW data format (matching PyTorch)",
    )
    p_full.add_argument(
        "--class-name", help="PyTorch model class name to use (default: auto-detect)")
    p_full.add_argument(
        "--model-args", help="Model instantiation arguments, e.g. 'num_classes=10'")
    p_full.add_argument(
        "--batch-size", type=int, default=1,
        help="Batch size (N) for export. Default: 1")

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "auto": cmd_auto,
        "convert-model": cmd_convert_model,
        "convert-weights": cmd_convert_weights,
        "validate": cmd_validate,
        "export": cmd_export,
        "full": cmd_full_pipeline,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
