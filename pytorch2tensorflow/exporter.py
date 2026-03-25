"""
TensorFlow Model → PB (SavedModel / FrozenGraph) Exporter

Exports TensorFlow/Keras models to PB format compatible with
Huawei Ascend (昇腾) ATC tool chain. Supports:
    - SavedModel format export
    - Frozen graph (.pb) export
    - Input/output node specification
    - Custom op handling
    - Ascend-specific optimizations (NHWC layout, supported op check)
    - ATC conversion command generation
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ops known to be supported on Ascend 310/910 platforms.
# This list covers the standard TF ops produced by our converter.
ASCEND_SUPPORTED_OPS = {
    # Convolution
    "Conv2D", "Conv2DBackpropInput", "Conv3D",
    "DepthwiseConv2dNative",
    # Matrix / Linear
    "MatMul", "BatchMatMulV2", "BiasAdd",
    # Activation
    "Relu", "Relu6", "LeakyRelu", "Sigmoid", "Tanh", "Softmax",
    "Elu", "Selu", "LogSoftmax",
    # Pooling
    "MaxPool", "AvgPool", "MaxPoolV2",
    "MaxPool3D", "AvgPool3D",
    # Reduction
    "Mean", "Sum", "Max", "Min", "Prod", "All", "Any",
    # Elementwise arithmetic
    "Add", "AddV2", "Mul", "Sub", "Neg", "RealDiv", "FloorDiv",
    "Rsqrt", "Sqrt", "Exp", "Log", "Pow", "Abs", "Square",
    "Minimum", "Maximum",
    # Comparison
    "Greater", "GreaterEqual", "Less", "LessEqual",
    "Equal", "NotEqual", "Where", "Select",
    # Shape / Layout
    "ConcatV2", "Reshape", "Transpose", "Pad", "PadV2", "MirrorPad",
    "StridedSlice", "Slice", "Split", "SplitV",
    "Squeeze", "ExpandDims", "Fill", "Tile", "Cast",
    "Shape", "Pack", "Unpack", "Range",
    "GatherV2", "GatherNd", "ScatterNd",
    "SpaceToBatchND", "BatchToSpaceND",
    "SpaceToDepth", "DepthToSpace",
    # Normalization
    "FusedBatchNormV3", "FusedBatchNorm",
    # Resize / Interpolation
    "ResizeBilinear", "ResizeNearestNeighbor", "ResizeBicubic",
    # Framework primitives
    "Placeholder", "Identity", "Const",
    "ReadVariableOp", "AssignVariableOp", "VarHandleOp",
    "NoOp", "Snapshot",
    # Control flow (basic)
    "StopGradient",
    # Random (for inference with fixed seed)
    "RandomUniform", "RandomStandardNormal",
    # Misc supported ops
    "OneHot", "TopKV2", "ArgMax", "ArgMin",
    "BroadcastTo", "ZerosLike", "OnesLike",
    "ClipByValue",
}

# Ops that may cause issues on Ascend
ASCEND_PROBLEMATIC_OPS = {
    "PyFunc", "Assert", "Print", "StringJoin",
    "DecodeJpeg", "DecodePng", "DecodeRaw",
    "TFRecordReader", "QueueDequeue",
    "While", "Switch", "Merge",  # dynamic control flow
}


class PBExporter:
    """Export TF models to PB format for Ascend deployment."""

    def __init__(
        self,
        input_names: Optional[list[str]] = None,
        output_names: Optional[list[str]] = None,
        opset_version: int = 11,
        channels_first: bool = False,
    ):
        """
        Args:
            input_names: Names of input nodes. Auto-detected if None.
            output_names: Names of output nodes. Auto-detected if None.
            opset_version: ONNX opset version (for optional ONNX export).
            channels_first: If True, model uses NCHW format; affects ATC
                input_format and shape generation.
        """
        self.input_names = input_names
        self.output_names = output_names
        self.opset_version = opset_version
        self.channels_first = channels_first

    def _to_nhwc_shape(self, shape: tuple) -> tuple:
        """Convert a CHW/CL shape to HWC/LC for NHWC mode.

        Handles:
          - 2D (C, L) → (L, C)         for Conv1d
          - 3D (C, H, W) → (H, W, C)   for Conv2d
          - 4D (C, D, H, W) → (D, H, W, C) for Conv3d
          - 1D or channels_first: returned as-is
        """
        if self.channels_first or len(shape) <= 1:
            return shape
        # Move first dim (channels) to last
        return (*shape[1:], shape[0])

    # ────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────

    def export_saved_model(
        self,
        tf_model,
        output_dir: str,
        input_shapes: Optional[list[tuple]] = None,
        batch_size: Optional[int] = None,
    ) -> str:
        """Export TF model as SavedModel directory.

        Args:
            tf_model: A tf.keras.Model instance.
            output_dir: Directory to save the SavedModel.
            input_shapes: Optional concrete input shapes for tracing.
            batch_size: Batch dimension. None means dynamic batch.

        Returns:
            Path to the SavedModel directory.
        """
        import tensorflow as tf

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if input_shapes:
            # Create concrete function with fixed input shapes
            nhwc_shapes = [self._to_nhwc_shape(s) for s in input_shapes]

            input_specs = [
                tf.TensorSpec(shape=(batch_size, *s), dtype=tf.float32)
                for s in nhwc_shapes
            ]

            @tf.function(input_signature=input_specs)
            def serving_fn(*inputs):
                if len(inputs) == 1:
                    out = tf_model(inputs[0], training=False)
                else:
                    out = tf_model(*inputs, training=False)
                # Convert tuple/list outputs to dict for SavedModel signatures
                if isinstance(out, (tuple, list)):
                    return {f"output_{i}": o for i, o in enumerate(out)}
                return out

            # Wrap in a plain tf.Module to avoid Keras auto-tracing
            # submodules with multi-arg call() (e.g. UNet's Up(x1, x2))
            wrapper = tf.Module()
            wrapper._model_vars = tf_model.variables
            wrapper.serve = serving_fn

            tf.saved_model.save(
                wrapper,
                str(output_path),
                signatures={"serving_default": serving_fn},
            )
        else:
            tf.saved_model.save(tf_model, str(output_path))

        logger.info("SavedModel exported to %s", output_path)
        return str(output_path)

    def export_frozen_graph(
        self,
        tf_model,
        output_path: str,
        input_shapes: Optional[list[tuple]] = None,
        batch_size: int = 1,
    ) -> str:
        """Export TF model as a frozen graph (.pb file).

        This is the preferred format for Ascend ATC tool.

        Args:
            tf_model: A tf.keras.Model instance.
            output_path: Path for the output .pb file.
            input_shapes: Input shapes for tracing (without batch dim).
            batch_size: Batch dimension for the frozen graph.

        Returns:
            Path to the frozen .pb file.
        """
        import tensorflow as tf

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Get concrete function
        if input_shapes:
            nhwc_shapes = [self._to_nhwc_shape(s) for s in input_shapes]

            input_specs = [
                tf.TensorSpec(shape=(batch_size, *s), dtype=tf.float32)
                for s in nhwc_shapes
            ]
        else:
            input_specs = None

        def _model_fn(x):
            out = tf_model(x, training=False)
            # Convert tuple/list to dict so each output gets a named node
            if isinstance(out, (tuple, list)):
                return {f"output_{i}": o for i, o in enumerate(out)}
            return out

        if input_specs:
            if len(input_specs) == 1:
                concrete_fn = tf.function(
                    _model_fn
                ).get_concrete_function(input_specs[0])
            else:
                concrete_fn = tf.function(
                    lambda *x: tf_model(*x, training=False)
                ).get_concrete_function(*input_specs)
        else:
            concrete_fn = tf.function(
                _model_fn
            ).get_concrete_function(
                tf.TensorSpec(shape=tf_model.input_shape, dtype=tf.float32)
            )

        # Freeze: convert variables to constants
        from tensorflow.python.framework.convert_to_constants import (
            convert_variables_to_constants_v2,
        )

        frozen_fn = convert_variables_to_constants_v2(concrete_fn)
        frozen_graph = frozen_fn.graph.as_graph_def()

        # Save frozen graph
        tf.io.write_graph(
            frozen_graph,
            str(output_file.parent),
            output_file.name,
            as_text=False,
        )

        # Log graph info
        input_nodes = [n.name for n in frozen_fn.inputs]
        output_nodes = [n.name for n in frozen_fn.outputs]
        logger.info("Frozen graph saved to %s", output_file)
        logger.info("Input nodes: %s", input_nodes)
        logger.info("Output nodes: %s", output_nodes)
        logger.info("Total ops: %d", len(frozen_graph.node))

        return str(output_file)

    def check_ascend_compatibility(
        self,
        pb_path: Optional[str] = None,
        tf_model=None,
        input_shapes: Optional[list[tuple]] = None,
    ) -> dict:
        """Check if the model uses only Ascend-supported ops.

        Args:
            pb_path: Path to a frozen .pb file. Provide this OR tf_model.
            tf_model: A tf.keras.Model instance.
            input_shapes: Input shapes (needed if tf_model is provided).

        Returns:
            Dict with compatibility report.
        """
        import tensorflow as tf

        if pb_path:
            graph_def = tf.compat.v1.GraphDef()
            with open(pb_path, "rb") as f:
                graph_def.ParseFromString(f.read())
        elif tf_model:
            if input_shapes:
                nhwc_shapes = [self._to_nhwc_shape(s) for s in input_shapes]
                input_specs = [
                    tf.TensorSpec(shape=(1, *s), dtype=tf.float32)
                    for s in nhwc_shapes
                ]
                concrete_fn = tf.function(
                    lambda x: tf_model(x, training=False)
                ).get_concrete_function(input_specs[0])
            else:
                concrete_fn = tf.function(
                    lambda x: tf_model(x, training=False)
                ).get_concrete_function(
                    tf.TensorSpec(shape=tf_model.input_shape, dtype=tf.float32)
                )
            from tensorflow.python.framework.convert_to_constants import (
                convert_variables_to_constants_v2,
            )
            frozen_fn = convert_variables_to_constants_v2(concrete_fn)
            graph_def = frozen_fn.graph.as_graph_def()
        else:
            raise ValueError("Provide either pb_path or tf_model")

        all_ops = set()
        op_counts = {}
        unsupported = set()
        problematic = set()

        for node in graph_def.node:
            op = node.op
            all_ops.add(op)
            op_counts[op] = op_counts.get(op, 0) + 1

            if op in ASCEND_PROBLEMATIC_OPS:
                problematic.add(op)
            elif op not in ASCEND_SUPPORTED_OPS:
                # Not in known-good list, flag as potentially unsupported
                unsupported.add(op)

        compatible = len(problematic) == 0
        report = {
            "compatible": compatible,
            "total_nodes": len(graph_def.node),
            "unique_ops": len(all_ops),
            "op_counts": dict(sorted(op_counts.items(), key=lambda x: -x[1])),
            "supported_ops": sorted(all_ops & ASCEND_SUPPORTED_OPS),
            "unsupported_ops": sorted(unsupported),
            "problematic_ops": sorted(problematic),
            "warnings": [],
        }

        if unsupported:
            report["warnings"].append(
                f"Found {len(unsupported)} ops not in known Ascend support list. "
                f"These may still work depending on your Ascend toolkit version: "
                f"{sorted(unsupported)}"
            )
        if problematic:
            report["warnings"].append(
                f"Found {len(problematic)} known problematic ops for Ascend: "
                f"{sorted(problematic)}. These will likely cause ATC conversion "
                f"to fail."
            )

        logger.info("Ascend compatibility check: %s", "PASS" if compatible else "FAIL")
        for w in report["warnings"]:
            logger.warning(w)

        return report

    def generate_atc_command(
        self,
        pb_path: str,
        output_path: str,
        soc_version: str = "Ascend910B4",
        input_shape: Optional[str] = None,
        input_format: str = "NHWC",
        framework: str = "3",  # 3 = TensorFlow
    ) -> str:
        """Generate the ATC command for converting PB to OM model.

        Args:
            pb_path: Path to the frozen .pb file.
            output_path: Desired output .om file path.
            soc_version: Target Ascend SoC (e.g., Ascend310, Ascend910).
            input_shape: Input shape string (e.g., "input:1,224,224,3").
            input_format: Input format (NHWC or NCHW).
            framework: Framework ID (3 = TensorFlow).

        Returns:
            The ATC command string.
        """
        cmd_parts = [
            "atc",
            f"--model={pb_path}",
            f"--framework={framework}",
            f"--output={output_path}",
            f"--soc_version={soc_version}",
            f"--input_format={input_format}",
        ]

        if input_shape:
            cmd_parts.append(f"--input_shape=\"{input_shape}\"")

        cmd = " \\\n    ".join(cmd_parts)

        logger.info("Generated ATC command:\n%s", cmd)
        return cmd

    def export_and_verify(
        self,
        tf_model,
        output_dir: str,
        input_shapes: list[tuple],
        soc_version: str = "Ascend910B4",
        batch_size: int = 1,
    ) -> dict:
        """Full pipeline: export + compatibility check + ATC command.

        Args:
            tf_model: A tf.keras.Model instance.
            output_dir: Directory for all output files.
            input_shapes: Input shapes (without batch dim).
            soc_version: Target Ascend SoC version.
            batch_size: Batch dimension for export.

        Returns:
            Dict with all export results.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Export SavedModel (use None for dynamic batch in SavedModel)
        saved_model_dir = self.export_saved_model(
            tf_model,
            str(out_path / "saved_model"),
            input_shapes,
            batch_size=None,
        )

        # Export Frozen Graph (use specified batch_size)
        pb_path = self.export_frozen_graph(
            tf_model,
            str(out_path / "frozen_model.pb"),
            input_shapes,
            batch_size=batch_size,
        )

        # Check Ascend compatibility
        compat = self.check_ascend_compatibility(pb_path=pb_path)

        # Auto-detect input node names from frozen graph
        input_node_names = self._detect_input_names(pb_path)

        # Generate ATC command with correct input shapes
        input_format = "NCHW" if self.channels_first else "NHWC"
        shape_parts = []
        for idx, shape in enumerate(input_shapes):
            name = input_node_names[idx] if idx < len(input_node_names) else f"input_{idx}"
            nhwc = self._to_nhwc_shape(shape)
            shape_str = ",".join(str(d) for d in (batch_size, *nhwc))
            shape_parts.append(f"{name}:{shape_str}")

        atc_input_shape = ";".join(shape_parts)
        atc_cmd = self.generate_atc_command(
            pb_path=pb_path,
            output_path=str(out_path / "model"),
            soc_version=soc_version,
            input_shape=atc_input_shape,
            input_format=input_format,
        )

        return {
            "saved_model_dir": saved_model_dir,
            "frozen_graph_path": pb_path,
            "ascend_compatibility": compat,
            "atc_command": atc_cmd,
            "input_nodes": input_node_names,
        }

    def _detect_input_names(self, pb_path: str) -> list[str]:
        """Auto-detect input node names from a frozen graph.

        Finds Placeholder nodes which represent model inputs.
        """
        import tensorflow as tf

        graph_def = tf.compat.v1.GraphDef()
        with open(pb_path, "rb") as f:
            graph_def.ParseFromString(f.read())

        input_names = []
        for node in graph_def.node:
            if node.op == "Placeholder":
                input_names.append(node.name)

        if not input_names:
            input_names = ["input"]
            logger.warning("No Placeholder nodes found, defaulting to 'input'")

        return input_names
