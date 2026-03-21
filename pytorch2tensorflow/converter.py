"""
PyTorch Model → TensorFlow/Keras Model Converter

Converts PyTorch nn.Module model definitions (.py files) into
TensorFlow/Keras model code. Supports:
    - AST-based code transformation (preserves structure & comments)
    - nn.Module → tf.keras.Model subclass conversion
    - nn.Sequential → tf.keras.Sequential conversion
    - Layer parameter adaptation (channels-first → channels-last, etc.)
    - Functional API operation mapping
    - Custom layer generation for unsupported ops
"""

import ast
import re
import textwrap
from pathlib import Path
from typing import Optional

from pytorch2tensorflow.layer_mapping import (
    ACTIVATION_MAP,
    CONV_PARAM_MAP,
    FUNCTIONAL_MAP,
    IMPORT_MAP,
    INTERPOLATION_MAP,
    LAYER_MAP,
    PADDING_MAP,
    TENSOR_METHOD_MAP,
)


class ModelConverter:
    """Convert PyTorch model .py files to TensorFlow/Keras equivalents."""

    def __init__(
        self,
        add_channel_convert: bool = True,
        channels_first: bool = False,
    ):
        """
        Args:
            add_channel_convert: If True, insert channel-order permutation
                (NCHW → NHWC) at input and output of the model.
            channels_first: If True, keep NCHW data format (matching PyTorch).
                TF layers will use data_format='channels_first' so that
                tensor shapes, axis indices, and padding orders remain
                identical to the original PyTorch model.  When True,
                add_channel_convert is ignored.
        """
        self.channels_first = channels_first
        self.add_channel_convert = add_channel_convert and not channels_first
        self._custom_layers_needed: set[str] = set()
        # Track conv layers that need explicit padding (stride>1 + padding>0)
        # Each entry is (attr_pattern, pad_value, ndim) where attr_pattern
        # matches the attribute call (e.g. "self.conv") in the call() method
        self._explicit_padding_convs: list[tuple[str, int, int]] = []

    # ────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────

    def convert_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
    ) -> str:
        """Convert a PyTorch model file to TensorFlow.

        Args:
            input_path: Path to the PyTorch model .py file.
            output_path: Optional path to write the converted file.
                If None, returns the converted code as a string.

        Returns:
            The converted TensorFlow model code.
        """
        source = Path(input_path).read_text(encoding="utf-8")
        converted = self.convert_source(source)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(converted, encoding="utf-8")

        return converted

    def convert_source(self, source: str) -> str:
        """Convert PyTorch model source code to TensorFlow.

        Args:
            source: PyTorch model Python source code.

        Returns:
            Converted TensorFlow/Keras model source code.
        """
        self._custom_layers_needed.clear()
        self._explicit_padding_convs.clear()

        # Step 1: Convert imports
        result = self._convert_imports(source)

        # Step 2: Convert class definitions (nn.Module → tf.keras.Model)
        result = self._convert_class_definitions(result)

        # Step 3: Convert __init__ layer definitions
        result = self._convert_init_layers(result)

        # Step 4: Convert forward() → call()
        result = self._convert_forward_to_call(result)

        # Step 4b: Inject explicit padding for stride>1 conv layers
        result = self._inject_explicit_padding(result)

        # Step 5: Convert functional operations
        result = self._convert_functional_ops(result)

        # Step 6: Convert tensor methods
        result = self._convert_tensor_methods(result)

        # Step 7: Convert torch.* operations
        result = self._convert_torch_ops(result)

        # Step 8: Handle data format (NCHW → NHWC)
        result = self._handle_data_format(result)

        # Step 9: Add channel conversion helpers if needed
        result = self._add_channel_conversion_helpers(result)

        # Step 10: Prepend custom layer definitions if needed
        result = self._prepend_custom_layers(result)

        # Step 11: Clean up
        result = self._cleanup(result)

        return result

    # ────────────────────────────────────────
    # Import conversion
    # ────────────────────────────────────────

    def _convert_imports(self, source: str) -> str:
        lines = source.split("\n")
        new_lines = []
        tf_imported = False

        for line in lines:
            stripped = line.strip()
            matched = False
            for pt_import, tf_import in IMPORT_MAP.items():
                if stripped == pt_import or stripped.startswith(pt_import + " "):
                    if tf_import == "import tensorflow as tf":
                        if not tf_imported:
                            new_lines.append("import tensorflow as tf")
                            tf_imported = True
                    else:
                        new_lines.append(tf_import)
                    matched = True
                    break

            if not matched:
                # Handle remaining torch imports
                if "import torch" in stripped or "from torch" in stripped:
                    if not tf_imported:
                        new_lines.append("import tensorflow as tf")
                        tf_imported = True
                    new_lines.append(f"# {stripped}  # Removed PyTorch import")
                else:
                    new_lines.append(line)

        if not tf_imported:
            new_lines.insert(0, "import tensorflow as tf")

        return "\n".join(new_lines)

    # ────────────────────────────────────────
    # Class definition conversion
    # ────────────────────────────────────────

    def _convert_class_definitions(self, source: str) -> str:
        # nn.Module → tf.keras.Model
        source = re.sub(
            r"class\s+(\w+)\s*\(\s*nn\.Module\s*\)",
            r"class \1(tf.keras.Model)",
            source,
        )
        # Handle other base classes
        source = re.sub(
            r"class\s+(\w+)\s*\(\s*nn\.Sequential\s*\)",
            r"class \1(tf.keras.Sequential)",
            source,
        )
        return source

    # ────────────────────────────────────────
    # __init__ layer conversion
    # ────────────────────────────────────────

    def _convert_init_layers(self, source: str) -> str:
        # super().__init__()
        source = re.sub(
            r"super\(\s*\w*\s*,?\s*self\s*\)\.__init__\(\)",
            "super().__init__()",
            source,
        )
        source = re.sub(
            r"super\(\).__init__\(\)",
            "super().__init__()",
            source,
        )

        # Convert nn.Sequential
        source = self._convert_nn_sequential(source)

        # Convert individual layers
        for pt_layer, tf_layer in LAYER_MAP.items():
            if pt_layer in source:
                source = self._convert_layer_call(source, pt_layer, tf_layer)

        return source

    def _convert_nn_sequential(self, source: str) -> str:
        """Convert nn.Sequential blocks to tf.keras.Sequential.

        PyTorch: nn.Sequential(layer1, layer2, ...)  — positional args
        TF:      tf.keras.Sequential([layer1, layer2, ...])  — list arg

        Must wrap arguments in [...] brackets.
        """
        # First replace the name
        source = source.replace("nn.Sequential", "tf.keras.Sequential")

        # Then wrap args in a list: Sequential(...) → Sequential([...])
        # Use a function to find matching parens (handles nested calls).
        result = []
        i = 0
        marker = "tf.keras.Sequential("
        while i < len(source):
            pos = source.find(marker, i)
            if pos == -1:
                result.append(source[i:])
                break
            # Copy text up to and including the marker
            result.append(source[i : pos + len(marker)])
            # Find the matching closing paren
            depth = 1
            j = pos + len(marker)
            while j < len(source) and depth > 0:
                if source[j] == "(":
                    depth += 1
                elif source[j] == ")":
                    depth -= 1
                j += 1
            # j now points one past the closing ')'
            inner = source[pos + len(marker) : j - 1]  # content between ( and )
            # Only wrap if inner is non-empty and not already a list
            stripped_inner = inner.strip()
            if stripped_inner and not stripped_inner.startswith("["):
                result.append("[")
                result.append(inner)
                result.append("])")
            else:
                result.append(inner)
                result.append(")")
            i = j

        return "".join(result)

    def _convert_layer_call(self, source: str, pt_layer: str, tf_layer: str) -> str:
        """Convert a specific layer constructor call."""
        # If tf_layer already contains '(' (e.g. "Activation('gelu')"),
        # replace the entire `nn.GELU()` call with the tf_layer value directly,
        # stripping the original arguments.
        if "(" in tf_layer:
            # Match the full call nn.GELU(...) and replace with tf_layer
            pattern = re.escape(pt_layer) + r"\s*\([^)]*\)"
            source = re.sub(pattern, tf_layer, source)
            return source

        pattern = re.escape(pt_layer) + r"\s*\("

        def _replace_layer(match: re.Match) -> str:
            return tf_layer + "("

        source = re.sub(pattern, _replace_layer, source)

        # Handle special parameter conversions
        if "Conv" in pt_layer:
            source = self._convert_conv_params(source, tf_layer)
        if "BatchNorm" in pt_layer:
            source = self._convert_batchnorm_params(source)
        if "Linear" in pt_layer:
            source = self._convert_linear_params(source)
        if "AdaptiveAvgPool" in pt_layer or "AdaptiveMaxPool" in pt_layer:
            source = self._convert_adaptive_pool_params(source, tf_layer)
        if "LayerNorm" in pt_layer:
            source = self._convert_layernorm_params(source)
        if "GroupNorm" in pt_layer:
            source = self._convert_groupnorm_params(source)

        # In channels_first mode, pooling/upsampling layers also need data_format
        if self.channels_first and ("Pool" in pt_layer or "Upsamp" in pt_layer):

            def _add_pool_data_format(match: re.Match) -> str:
                call = match.group(1)
                if "data_format" in call:
                    return call + ")"
                return call + ", data_format='channels_first')"

            source = re.sub(
                r"(" + re.escape(tf_layer) + r"\([^)]*)\)",
                _add_pool_data_format,
                source,
            )

        return source

    def _convert_conv_params(self, source: str, tf_layer: str) -> str:
        """Convert Conv layer parameters from PyTorch to TF convention.

        PyTorch Conv: nn.Conv2d(in_channels, out_channels, kernel_size, ...)
        TF Conv:      tf.keras.layers.Conv2D(filters, kernel_size, ...)

        The first positional arg (in_channels) must be removed since TF
        infers input channels automatically.
        """
        # Remove in_channels (first positional arg) from Conv layer calls.
        # PyTorch: Conv2d(in_channels, out_channels, ...) — 2 positional args
        # TF:      Conv2D(filters, ...) — only needs out_channels
        # Strategy: match the full call from layer name to closing paren,
        # then drop only the first positional arg via a callback.
        conv_call_full = (
            r"(" + re.escape(tf_layer) + r")"  # specific layer name
            r"\(([^)]*)\)"                      # entire argument list
        )

        def _drop_first_pos_arg(match: re.Match) -> str:
            layer = match.group(1)
            args_str = match.group(2).strip()
            if not args_str:
                return f"{layer}()"
            # Split on commas, being careful with nested parens
            parts = [p.strip() for p in args_str.split(",")]
            # Count leading positional args (no keyword '=' sign).
            # Must distinguish keyword '=' from comparison operators (==, !=, <=, >=).
            num_positional = 0
            for p in parts:
                if re.search(r"(?<![=!<>])=(?!=)", p):
                    break
                num_positional += 1
            # Only drop first arg if there are >=2 positional args
            if num_positional >= 2:
                parts = parts[1:]
            return f"{layer}({', '.join(parts)})"

        source = re.sub(conv_call_full, _drop_first_pos_arg, source)

        # Rename Conv keyword args, but ONLY inside tf.keras.layers.XXX(...) calls.
        # Using a callback to avoid renaming identically-named function parameters
        # (e.g. `def __init__(self, ..., stride=1)` must NOT become `strides=1`).
        conv_call_re = r"(" + re.escape(tf_layer) + r"\([^)]*)"
        keyword_renames = [
            (r"\bpadding\s*=\s*(\d+)", self._padding_value_to_tf),
            (r"\bstride\s*=", "strides="),
            (r"\bdilation\s*=", "dilation_rate="),
            (r"\bbias\s*=", "use_bias="),
        ]
        for kw_pattern, replacement in keyword_renames:
            def _rename_in_call(match: re.Match, _kw=kw_pattern, _rep=replacement) -> str:
                call_str = match.group(0)
                if callable(_rep):
                    return re.sub(_kw, _rep, call_str)
                return re.sub(_kw, _rep, call_str)
            source = re.sub(conv_call_re, _rename_in_call, source)

        # Fix stride>1 + padding asymmetry (must run after keyword renames)
        if not self.channels_first:
            source = self._fix_stride_padding(source, tf_layer)

        # Add data_format for Conv layers
        if self.channels_first:
            # Insert data_format='channels_first' before the closing paren
            # Use a function to avoid adding it twice on repeated calls
            def _add_conv_data_format(match: re.Match) -> str:
                call = match.group(1)
                if "data_format" in call:
                    return call + ")"
                return call + ", data_format='channels_first')"

            source = re.sub(
                r"(tf\.keras\.layers\.Conv\w+\([^)]+)\)",
                _add_conv_data_format,
                source,
            )
        # else: channels_last (NHWC) is the TF default, no explicit param needed

        return source

    def _padding_value_to_tf(self, match: re.Match) -> str:
        val = int(match.group(1))
        if val == 0:
            return "padding='valid'"
        else:
            return f"padding='same'"

    def _fix_stride_padding(self, source: str, tf_layer: str) -> str:
        """Fix Conv layers with stride>1 and padding>0.

        TF's padding='same' uses asymmetric padding for stride>1, which
        differs from PyTorch's symmetric padding. For these cases, we
        convert to padding='valid' and inject explicit tf.pad() calls
        in the call() method.
        """
        # Determine conv dimensionality for pad shape
        if "1D" in tf_layer or "1d" in tf_layer:
            ndim = 1
        elif "3D" in tf_layer or "3d" in tf_layer:
            ndim = 3
        else:
            ndim = 2

        # Find Conv calls with strides>1 and padding='same'
        # Pattern: self.xxx = tf.keras.layers.Conv2D(..., strides=N, ..., padding='same', ...)
        conv_init_pattern = (
            r"(self\.(\w+)\s*=\s*" + re.escape(tf_layer) + r"\([^)]*)"
        )

        def _check_and_fix(match: re.Match) -> str:
            call_str = match.group(0)
            attr_name = match.group(2)

            # Check if strides > 1
            stride_m = re.search(r"strides\s*=\s*(\d+)", call_str)
            if not stride_m:
                return call_str
            stride_val = int(stride_m.group(1))
            if stride_val <= 1:
                return call_str

            # Check if padding='same' and extract original padding value
            if "padding='same'" not in call_str:
                return call_str

            # Get the original padding value from the _padding_value_to_tf call
            # We already converted padding=N to padding='same', so we need to
            # extract what N was. Look for kernel_size to estimate padding.
            kernel_m = re.search(r"kernel_size\s*=\s*(\d+)", call_str)
            if not kernel_m:
                # Try second positional arg (filters is first, kernel_size is second)
                parts = call_str.split("(", 1)[1].split(",")
                for i, p in enumerate(parts):
                    p = p.strip()
                    if p.isdigit() and i >= 1:  # second positional = kernel_size
                        kernel_m = type('M', (), {'group': lambda self, n: p})()
                        break
            if not kernel_m:
                return call_str

            kernel_size = int(kernel_m.group(1))
            pad_val = kernel_size // 2  # PyTorch padding=1 typically = kernel//2

            # Record for explicit padding injection
            self._explicit_padding_convs.append(
                (f"self.{attr_name}", pad_val, ndim)
            )

            # Change padding='same' to padding='valid'
            call_str = call_str.replace("padding='same'", "padding='valid'")
            return call_str

        source = re.sub(conv_init_pattern, _check_and_fix, source)
        return source

    def _convert_batchnorm_params(self, source: str) -> str:
        """Convert BatchNorm parameters.

        PyTorch: nn.BatchNorm2d(num_features, eps=..., momentum=...)
        TF:      tf.keras.layers.BatchNormalization(epsilon=..., momentum=...)

        The num_features positional arg must be removed since TF infers it.
        """
        # Remove num_features (first positional arg) from BatchNormalization calls
        # Match: BatchNormalization(expr) or BatchNormalization(expr, ...)
        # Handle case where num_features is the only arg
        source = re.sub(
            r"(tf\.keras\.layers\.BatchNormalization)\(\s*[^,)]+\s*\)",
            r"\1()",
            source,
        )
        # Handle case where num_features is followed by keyword args
        source = re.sub(
            r"(tf\.keras\.layers\.BatchNormalization)\(\s*[^,)]+\s*,\s*",
            r"\1(",
            source,
        )
        # eps → epsilon
        source = re.sub(r"\beps\s*=", "epsilon=", source)
        # momentum handling: PyTorch default=0.1, TF default=0.99
        # TF momentum = 1 - PyTorch momentum
        source = re.sub(r"\bmomentum\s*=\s*([\d.]+)", self._convert_bn_momentum, source)
        # affine → trainable (center/scale)
        source = re.sub(r"\baffine\s*=\s*False", "center=False, scale=False", source)
        # track_running_stats not needed in TF
        source = re.sub(r",?\s*track_running_stats\s*=\s*(True|False)", "", source)

        # In channels_first mode, BN axis must be 1 (channel dim in NCHW)
        # TF default axis=-1 is correct for NHWC, but wrong for NCHW
        if self.channels_first:

            def _add_bn_axis(match: re.Match) -> str:
                call = match.group(1)
                if "axis=" in call:
                    return call + ")"
                return call + ", axis=1)"

            source = re.sub(
                r"(tf\.keras\.layers\.BatchNormalization\([^)]*)\)",
                _add_bn_axis,
                source,
            )
            # Clean up empty-args case: BatchNormalization(, axis=1) → BatchNormalization(axis=1)
            source = source.replace("BatchNormalization(, ", "BatchNormalization(")

        return source

    def _convert_bn_momentum(self, match: re.Match) -> str:
        pt_momentum = float(match.group(1))
        tf_momentum = 1.0 - pt_momentum
        return f"momentum={tf_momentum}"

    def _convert_linear_params(self, source: str) -> str:
        """Convert Linear → Dense parameters.

        PyTorch: nn.Linear(in_features, out_features, bias=True)
        TF:      tf.keras.layers.Dense(units, use_bias=True)

        The in_features (first positional arg) must be removed since TF infers it.
        """
        # Remove in_features (first positional arg) from Dense calls.
        # Match: Dense(expr1, expr2, ...) where expr1 and expr2 are positional
        linear_pattern = (
            r"(tf\.keras\.layers\.Dense)"
            r"\(\s*"
            r"([^,)]+)"       # first positional arg (in_features)
            r"\s*,\s*"
            r"([^,)=]+)"      # second positional arg (out_features) — no '='
            r"(?=\s*[,)])"    # must be followed by , or )
        )

        def _drop_in_features(match: re.Match) -> str:
            layer = match.group(1)
            out_features = match.group(3).strip()
            return f"{layer}({out_features}"

        source = re.sub(linear_pattern, _drop_in_features, source)

        # bias → use_bias (scoped to Dense layer calls only)
        def _rename_bias(match: re.Match) -> str:
            return re.sub(r"\bbias\s*=", "use_bias=", match.group(0))
        source = re.sub(r"(tf\.keras\.layers\.Dense\([^)]*)", _rename_bias, source)
        return source

    def _convert_layernorm_params(self, source: str) -> str:
        """Convert LayerNorm → LayerNormalization parameters.

        PyTorch: nn.LayerNorm(normalized_shape, eps=...)
        TF:      tf.keras.layers.LayerNormalization(epsilon=...)

        The normalized_shape (first positional arg) must be removed since TF
        LayerNormalization normalizes over the last axis by default.
        """
        pattern = (
            r"(tf\.keras\.layers\.LayerNormalization)"
            r"\(\s*"
            r"(?:\([^)]*\)|[^,)]+)"  # first positional arg (normalized_shape, could be tuple)
            r"((?:\s*,\s*[^)]*)?)"   # rest of args (optional)
            r"\)"
        )

        def _drop_normalized_shape(match: re.Match) -> str:
            layer = match.group(1)
            rest = match.group(2).strip()
            if rest.startswith(","):
                rest = rest[1:].strip()
            # Rename eps → epsilon
            rest = re.sub(r"\beps\s*=", "epsilon=", rest)
            return f"{layer}({rest})"

        source = re.sub(pattern, _drop_normalized_shape, source)
        return source

    def _convert_groupnorm_params(self, source: str) -> str:
        """Convert GroupNorm → GroupNormalization parameters.

        PyTorch: nn.GroupNorm(num_groups, num_channels, eps=...)
        TF:      tf.keras.layers.GroupNormalization(groups=num_groups, epsilon=...)

        The num_channels (second positional arg) must be removed since TF infers it.
        """
        pattern = (
            r"(tf\.keras\.layers\.GroupNormalization)"
            r"\(\s*"
            r"([^,)]+)"              # first positional arg (num_groups)
            r"\s*,\s*"
            r"([^,)=]+)"             # second positional arg (num_channels) — no '='
            r"((?:\s*,\s*[^)]*)?)"   # rest of args (optional)
            r"\)"
        )

        def _drop_num_channels(match: re.Match) -> str:
            layer = match.group(1)
            num_groups = match.group(2).strip()
            rest = match.group(4).strip()
            if rest.startswith(","):
                rest = rest[1:].strip()
            # Rename eps → epsilon
            rest = re.sub(r"\beps\s*=", "epsilon=", rest)
            if rest:
                return f"{layer}({num_groups}, {rest})"
            return f"{layer}({num_groups})"

        source = re.sub(pattern, _drop_num_channels, source)
        return source

    def _convert_adaptive_pool_params(self, source: str, tf_layer: str) -> str:
        """Convert AdaptiveAvgPool/AdaptiveMaxPool → GlobalAveragePooling/GlobalMaxPool.

        PyTorch: nn.AdaptiveAvgPool2d((1, 1)) or nn.AdaptiveAvgPool2d(1)
        TF:      tf.keras.layers.GlobalAveragePooling2D()

        GlobalAveragePooling always pools over all spatial dims, so the
        output_size argument must be removed entirely.
        Uses paren-depth matching to handle nested parens like ((1, 1)).
        """
        marker = tf_layer + "("
        result = []
        i = 0
        while i < len(source):
            pos = source.find(marker, i)
            if pos == -1:
                result.append(source[i:])
                break
            result.append(source[i:pos])
            # Find the matching closing paren (handles nested parens)
            depth = 1
            j = pos + len(marker)
            while j < len(source) and depth > 0:
                if source[j] == "(":
                    depth += 1
                elif source[j] == ")":
                    depth -= 1
                j += 1
            # Replace with empty args (or data_format for channels_first)
            if self.channels_first:
                result.append(f"{tf_layer}(data_format='channels_first')")
            else:
                result.append(f"{tf_layer}()")
            i = j

        return "".join(result)

    # ────────────────────────────────────────
    # forward() → call() conversion
    # ────────────────────────────────────────

    def _convert_forward_to_call(self, source: str) -> str:
        """Convert forward() method to call() method."""
        # def forward(self, x) → def call(self, x, training=False)
        source = re.sub(
            r"def\s+forward\s*\(\s*self\s*,\s*([^)]*)\)",
            r"def call(self, \1, training=False)",
            source,
        )
        # Handle training mode references
        source = source.replace("self.training", "training")
        return source

    def _inject_explicit_padding(self, source: str) -> str:
        """Inject tf.pad() calls before Conv layers that need explicit padding.

        When stride>1 with padding>0, TF's padding='same' differs from
        PyTorch's symmetric padding. We convert to padding='valid' and
        add explicit tf.pad() calls in the call() method.
        """
        if not self._explicit_padding_convs:
            return source

        for attr_pattern, pad_val, ndim in self._explicit_padding_convs:
            # Find "self.conv(expr)" in the call method and prepend tf.pad()
            # We need to match the conv call and insert padding before it.
            escaped = re.escape(attr_pattern)

            if ndim == 1:
                pad_str = f"[[0, 0], [{pad_val}, {pad_val}], [0, 0]]"
            elif ndim == 2:
                pad_str = (
                    f"[[0, 0], [{pad_val}, {pad_val}], "
                    f"[{pad_val}, {pad_val}], [0, 0]]"
                )
            else:  # 3D
                pad_str = (
                    f"[[0, 0], [{pad_val}, {pad_val}], "
                    f"[{pad_val}, {pad_val}], "
                    f"[{pad_val}, {pad_val}], [0, 0]]"
                )

            # Match: ... = self.conv(expr) or return self.conv(expr) or self.conv(self.other(x))
            # We insert tf.pad before the call
            def _add_pad(m: re.Match, _pad=pad_str) -> str:
                full = m.group(0)
                indent = m.group(1)
                arg = m.group(2)
                # Replace self.conv(arg) with self.conv(tf.pad(arg, paddings))
                return full.replace(
                    f"{attr_pattern}({arg})",
                    f"{attr_pattern}(tf.pad({arg}, {_pad}))",
                )

            # Match self.attr(single_word_arg) — handles simple cases
            source = re.sub(
                r"([ \t]*)([^\n]*)" + escaped + r"\((\w+)\)",
                lambda m, _a=attr_pattern, _p=pad_str: m.group(0).replace(
                    f"{_a}({m.group(3)})",
                    f"{_a}(tf.pad({m.group(3)}, {_p}))",
                ),
                source,
            )

        self._explicit_padding_convs.clear()
        return source

    # ────────────────────────────────────────
    # Functional ops conversion
    # ────────────────────────────────────────

    def _convert_functional_ops(self, source: str) -> str:
        """Convert F.xxx functional operations."""
        # Handle torch.flatten specially before generic replacement
        source = self._convert_torch_flatten(source)

        for pt_func, tf_func in {**FUNCTIONAL_MAP, **ACTIVATION_MAP}.items():
            if pt_func in source:
                source = self._convert_specific_functional(source, pt_func, tf_func)
        return source

    def _convert_torch_flatten(self, source: str) -> str:
        """Convert torch.flatten(x, start_dim) to tf.reshape.

        torch.flatten(x, 1) flattens from dim 1 onwards.
        Because TF uses NHWC while PyTorch uses NCHW, we must transpose
        4D tensors to NCHW order before flattening so that the Dense layer
        sees elements in the same order as the PyTorch Linear layer.

            → tf.reshape(tf.transpose(x, [0,3,1,2]), [tf.shape(x)[0], -1])

        torch.flatten(x, 0) flattens everything:
            → tf.reshape(x, [-1])
        torch.flatten(x) defaults to start_dim=0.
        """
        def _replace_flatten(match: re.Match) -> str:
            tensor = match.group(1)
            start_dim = match.group(2).strip() if match.group(2) else "0"
            if start_dim == "1":
                # Transpose NHWC→NCHW before flatten so element order
                # matches what the Dense/Linear kernel expects.
                return (
                    f"tf.reshape("
                    f"tf.transpose({tensor}, [0, 3, 1, 2]) "
                    f"if len({tensor}.shape) == 4 else {tensor}, "
                    f"[tf.shape({tensor})[0], -1])"
                )
            elif start_dim == "0":
                return f"tf.reshape({tensor}, [-1])"
            else:
                return f"tf.reshape({tensor}, [*tf.shape({tensor})[:{start_dim}], -1])"

        # Match torch.flatten(x, start_dim) or torch.flatten(x)
        source = re.sub(
            r"torch\.flatten\s*\(\s*(\w+)\s*(?:,\s*(\d+))?\s*\)",
            _replace_flatten,
            source,
        )
        return source

    def _convert_specific_functional(
        self, source: str, pt_func: str, tf_func: str
    ) -> str:
        """Convert a specific functional call with parameter adaptation."""
        # Handle F.interpolate specially
        if pt_func == "F.interpolate":
            source = self._convert_interpolate(source)
            return source

        # Handle F.softmax dim→axis
        if "softmax" in pt_func:
            source = source.replace(pt_func, tf_func)
            source = re.sub(r"\bdim\s*=", "axis=", source)
            return source

        # Handle F.pad — requires padding format conversion
        if pt_func == "F.pad":
            source = self._convert_pad(source)
            return source

        # Handle F.dropout — parameter adaptation
        if pt_func.startswith("F.dropout"):
            source = self._convert_dropout(source, pt_func)
            return source

        # Handle torch.cat — needs dim→axis
        if pt_func == "torch.cat":
            source = source.replace("torch.cat", "tf.concat")
            source = re.sub(r"\bdim\s*=", "axis=", source)
            return source

        # Handle torch.clamp — rename min=/max= kwargs
        if pt_func in ("torch.clamp", "torch.clip"):
            source = source.replace(pt_func, tf_func)
            # Rename min= → clip_value_min=, max= → clip_value_max=
            # within tf.clip_by_value calls (simple keyword rename)
            source = re.sub(
                r"\bmin\s*=\s*(?=-?[\d.])",
                "clip_value_min=",
                source,
            )
            source = re.sub(
                r"\bmax\s*=\s*(?=-?[\d.])",
                "clip_value_max=",
                source,
            )
            return source

        # Handle F.interpolate variants
        if pt_func in ("F.upsample", "F.upsample_nearest", "F.upsample_bilinear"):
            source = self._convert_interpolate(source)
            return source

        # Generic replacement
        source = source.replace(pt_func, tf_func)
        # Common parameter renames
        source = re.sub(r"\bdim\s*=", "axis=", source)
        source = re.sub(r"\bkeepdim\s*=", "keepdims=", source)

        return source

    def _convert_interpolate(self, source: str) -> str:
        """Convert F.interpolate to tf.image.resize.

        PyTorch: F.interpolate(x, size=(H,W), scale_factor=2, mode='bilinear')
            - Input is NCHW
        TF: tf.image.resize(x, size=[H,W], method='bilinear')
            - Input is NHWC
        """
        # Handle scale_factor by replacing with a helper expression
        # scale_factor=N → size=tf.shape(x)[1:3]*N  (for NHWC spatial dims)
        pattern = r"F\.interpolate\s*\(\s*(\w+)\s*,\s*scale_factor\s*=\s*(\w+)"

        def _replace_scale_factor(match: re.Match) -> str:
            tensor = match.group(1)
            factor = match.group(2)
            return (
                f"tf.image.resize({tensor}, "
                f"size=[tf.shape({tensor})[1] * {factor}, "
                f"tf.shape({tensor})[2] * {factor}]"
            )

        source = re.sub(pattern, _replace_scale_factor, source)

        # Handle size= parameter (already absolute sizes)
        source = re.sub(r"F\.interpolate\s*\(", "tf.image.resize(", source)
        source = re.sub(r"F\.upsample\s*\(", "tf.image.resize(", source)

        # mode → method
        for pt_mode, tf_mode in INTERPOLATION_MAP.items():
            source = source.replace(f"mode='{pt_mode}'", f"method='{tf_mode}'")
            source = source.replace(f'mode="{pt_mode}"', f"method='{tf_mode}'")

        # align_corners — not supported in TF, remove
        source = re.sub(r",?\s*align_corners\s*=\s*(True|False)", "", source)
        return source

    def _convert_pad(self, source: str) -> str:
        """Convert F.pad to tf.pad.

        PyTorch F.pad uses a flat tuple in reverse order:
            F.pad(x, (left, right, top, bottom), mode='reflect')
        TensorFlow tf.pad uses nested paddings for each dimension (NHWC):
            tf.pad(x, [[0,0], [top,bottom], [left,right], [0,0]], mode='REFLECT')
        """
        # Match F.pad calls with their full arguments
        pattern = r"F\.pad\s*\(\s*(\w+)\s*,\s*\(([^)]*)\)(?:\s*,\s*([^)]*))?\)"

        def _replace_pad(match: re.Match) -> str:
            tensor_name = match.group(1)
            pad_values_str = match.group(2)
            extra_args = match.group(3) or ""

            # Parse padding values
            pad_values = [v.strip() for v in pad_values_str.split(",") if v.strip()]

            # Build TF paddings — format depends on channels_first setting.
            # PyTorch pad order: (left, right, top, bottom[, front, back])
            # from innermost dim to outermost dim.
            #
            # NCHW: [batch, channels, height, width]
            # NHWC: [batch, height, width, channels]
            use_nchw = self.channels_first

            if len(pad_values) == 2:
                # 1D: (left, right) → pad last dim (W)
                if use_nchw:
                    paddings = f"[[0, 0], [0, 0], [0, 0], [{pad_values[0]}, {pad_values[1]}]]"
                else:
                    paddings = f"[[0, 0], [0, 0], [{pad_values[0]}, {pad_values[1]}], [0, 0]]"
            elif len(pad_values) == 4:
                left, right, top, bottom = pad_values
                if use_nchw:
                    # NCHW: [N, C, H, W]
                    paddings = f"[[0, 0], [0, 0], [{top}, {bottom}], [{left}, {right}]]"
                else:
                    # NHWC: [N, H, W, C]
                    paddings = f"[[0, 0], [{top}, {bottom}], [{left}, {right}], [0, 0]]"
            elif len(pad_values) == 6:
                left, right, top, bottom, front, back = pad_values
                if use_nchw:
                    paddings = f"[[0, 0], [0, 0], [{front}, {back}], [{top}, {bottom}], [{left}, {right}]]"
                else:
                    paddings = f"[[0, 0], [{front}, {back}], [{top}, {bottom}], [{left}, {right}], [0, 0]]"
            else:
                # Fallback: keep as expression (may be dynamic)
                paddings = f"({pad_values_str})"

            # Parse mode and value from extra args
            mode = "CONSTANT"
            constant_values = ""
            if extra_args:
                # Extract mode
                mode_match = re.search(r"""mode\s*=\s*['"](\w+)['"]""", extra_args)
                if mode_match:
                    pt_mode = mode_match.group(1)
                    mode = PADDING_MAP.get(pt_mode, pt_mode.upper())

                # Extract value (for constant padding)
                val_match = re.search(r"value\s*=\s*([^,)]+)", extra_args)
                if val_match and mode == "CONSTANT":
                    constant_values = f", constant_values={val_match.group(1).strip()}"

            return f"tf.pad({tensor_name}, {paddings}, mode='{mode}'{constant_values})"

        source = re.sub(pattern, _replace_pad, source)
        return source

    def _convert_dropout(self, source: str, pt_func: str) -> str:
        """Convert F.dropout to tf.nn.dropout.

        PyTorch: F.dropout(x, p=0.5, training=self.training)
        TF:      tf.nn.dropout(x, rate=0.5) during training, identity otherwise
        """
        # Match F.dropout(...) calls
        pattern = re.escape(pt_func) + r"\s*\(\s*(\w+)\s*,([^)]*)\)"

        def _replace_dropout(match: re.Match) -> str:
            tensor = match.group(1)
            args_str = match.group(2)

            # Extract p value
            p_match = re.search(r"p\s*=\s*([\d.]+)", args_str)
            p_val = p_match.group(1) if p_match else "0.5"

            # Check for training flag
            has_training = "training" in args_str

            if has_training:
                return (
                    f"tf.nn.dropout({tensor}, rate={p_val}) "
                    f"if training else {tensor}"
                )
            else:
                return f"tf.nn.dropout({tensor}, rate={p_val})"

        source = re.sub(pattern, _replace_dropout, source)
        return source

    # ────────────────────────────────────────
    # Tensor method conversion
    # ────────────────────────────────────────

    def _convert_tensor_methods(self, source: str) -> str:
        """Convert tensor methods like .view(), .permute(), etc."""
        # .view() → tf.reshape()
        source = re.sub(
            r"(\w+)\.view\s*\(([^)]*)\)",
            r"tf.reshape(\1, [\2])",
            source,
        )

        # .permute() → tf.transpose()
        source = re.sub(
            r"(\w+)\.permute\s*\(([^)]*)\)",
            r"tf.transpose(\1, perm=[\2])",
            source,
        )

        # .transpose(a, b) → tf.transpose()
        source = re.sub(
            r"(\w+)\.transpose\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)",
            r"tf.transpose(\1, perm=[\2, \3])",
            source,
        )

        # .contiguous() → remove (no-op in TF)
        source = re.sub(r"\.contiguous\(\)", "", source)

        # .unsqueeze(dim) → tf.expand_dims(x, axis=dim)
        # Use negative lookbehind to avoid matching tf.expand_dims(...) or similar
        source = re.sub(
            r"(?<!\.)(\w+)\.unsqueeze\s*\(([^)]*)\)",
            lambda m: f"tf.expand_dims({m.group(1)}, axis={m.group(2)})" if m.group(1) != "tf" else m.group(0),
            source,
        )

        # .squeeze(dim) → tf.squeeze(x, axis=dim)
        # Avoid re-matching already-converted tf.squeeze(...)
        source = re.sub(
            r"(?<!\.)(\w+)\.squeeze\s*\(([^)]*)\)",
            lambda m: f"tf.squeeze({m.group(1)}, axis={m.group(2)})" if m.group(1) != "tf" else m.group(0),
            source,
        )

        # .flatten(start_dim) → tf.reshape
        def _replace_method_flatten(match: re.Match) -> str:
            tensor = match.group(1)
            start_dim = match.group(2)
            if start_dim == "1":
                return (
                    f"tf.reshape("
                    f"tf.transpose({tensor}, [0, 3, 1, 2]) "
                    f"if len({tensor}.shape) == 4 else {tensor}, "
                    f"[tf.shape({tensor})[0], -1])"
                )
            elif start_dim == "0":
                return f"tf.reshape({tensor}, [-1])"
            else:
                return f"tf.reshape({tensor}, [*tf.shape({tensor})[:{start_dim}], -1])"

        source = re.sub(
            r"(\w+)\.flatten\s*\((\d+)\)",
            _replace_method_flatten,
            source,
        )

        # .mean(dim) / .sum(dim)
        def _replace_reduce(tf_func):
            def _replacer(match):
                tensor = match.group(1)
                args = match.group(2)
                # Rename dim= → axis=, keepdim= → keepdims= inline
                args = re.sub(r"\bdim\s*=", "axis=", args)
                args = re.sub(r"\bkeepdim\s*=", "keepdims=", args)
                return f"{tf_func}({tensor}, {args})"
            return _replacer

        source = re.sub(
            r"(\w+)\.mean\s*\(([^)]*)\)",
            _replace_reduce("tf.reduce_mean"),
            source,
        )
        source = re.sub(
            r"(\w+)\.sum\s*\(([^)]*)\)",
            _replace_reduce("tf.reduce_sum"),
            source,
        )

        # .clamp(min, max) → tf.clip_by_value
        source = re.sub(
            r"(\w+)\.clamp\s*\(\s*min\s*=\s*([^,)]+)\s*,\s*max\s*=\s*([^)]+)\)",
            r"tf.clip_by_value(\1, \2, \3)",
            source,
        )
        source = re.sub(
            r"(\w+)\.clamp\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)",
            r"tf.clip_by_value(\1, \2, \3)",
            source,
        )

        # .detach() → tf.stop_gradient
        source = re.sub(
            r"(\w+)\.detach\(\)",
            r"tf.stop_gradient(\1)",
            source,
        )

        # .item() → .numpy()
        source = re.sub(r"\.item\(\)", ".numpy()", source)

        # .size(dim) → .shape[dim]
        source = re.sub(
            r"(\w+)\.size\s*\(\s*(\d+)\s*\)",
            r"\1.shape[\2]",
            source,
        )
        source = re.sub(
            r"(\w+)\.size\s*\(\s*\)",
            r"tf.shape(\1)",
            source,
        )

        # .repeat() → tf.tile
        source = re.sub(
            r"(\w+)\.repeat\s*\(([^)]+)\)",
            r"tf.tile(\1, [\2])",
            source,
        )

        # .expand() → tf.broadcast_to
        source = re.sub(
            r"(\w+)\.expand\s*\(([^)]+)\)",
            r"tf.broadcast_to(\1, [\2])",
            source,
        )

        # .clone() → tf.identity
        source = re.sub(r"(\w+)\.clone\(\)", r"tf.identity(\1)", source)

        # Type casting
        source = re.sub(r"(\w+)\.float\(\)", r"tf.cast(\1, tf.float32)", source)
        source = re.sub(r"(\w+)\.long\(\)", r"tf.cast(\1, tf.int64)", source)
        source = re.sub(r"(\w+)\.int\(\)", r"tf.cast(\1, tf.int32)", source)
        source = re.sub(r"(\w+)\.half\(\)", r"tf.cast(\1, tf.float16)", source)
        source = re.sub(r"(\w+)\.bool\(\)", r"tf.cast(\1, tf.bool)", source)

        # Device operations (no-op in TF)
        source = re.sub(r"(\w+)\.to\s*\([^)]*\)", r"\1", source)
        source = re.sub(r"(\w+)\.cuda\([^)]*\)", r"\1", source)
        source = re.sub(r"(\w+)\.cpu\(\)", r"\1", source)

        # .numel() → tf.size(x)
        source = re.sub(
            r"(\w+)\.numel\(\)",
            r"tf.size(\1)",
            source,
        )

        # model.parameters() → model.trainable_variables
        source = re.sub(
            r"(\w+)\.parameters\(\)",
            r"\1.trainable_variables",
            source,
        )

        # .state_dict() → .get_weights() (approximate)
        source = re.sub(
            r"(\w+)\.state_dict\(\)",
            r"\1.get_weights()",
            source,
        )

        return source

    # ────────────────────────────────────────
    # torch.* operations conversion
    # ────────────────────────────────────────

    def _convert_torch_ops(self, source: str) -> str:
        """Convert remaining torch.xxx operations."""
        for pt_op, tf_op in FUNCTIONAL_MAP.items():
            if tf_op and pt_op in source:
                source = source.replace(pt_op, tf_op)

        # torch.no_grad() → tf.stop_gradient or context manager
        source = re.sub(
            r"with\s+torch\.no_grad\(\)\s*:",
            "# Inference mode (no gradient tracking in TF eager):",
            source,
        )
        source = re.sub(
            r"@torch\.no_grad\(\)",
            "@tf.function",
            source,
        )

        # Parameter renames
        source = re.sub(r"\bdim\s*=", "axis=", source)
        source = re.sub(r"\bkeepdim\s*=", "keepdims=", source)

        # nn.Parameter → tf.Variable
        source = re.sub(
            r"nn\.Parameter\s*\(([^)]*)\)",
            r"tf.Variable(\1)",
            source,
        )

        # torch.Tensor → tf.Tensor
        source = source.replace("torch.Tensor", "tf.Tensor")

        # nn.ModuleList → list (Python list works in tf.keras.Model)
        source = source.replace("nn.ModuleList", "list")
        source = source.replace("nn.ModuleDict", "dict")

        return source

    # ────────────────────────────────────────
    # Data format handling (NCHW → NHWC)
    # ────────────────────────────────────────

    def _handle_data_format(self, source: str) -> str:
        """Handle NCHW → NHWC data format conversion.

        PyTorch uses NCHW (batch, channels, height, width).
        TensorFlow uses NHWC (batch, height, width, channels).

        When channels_first=True, the model stays in NCHW format so no
        axis/shape conversion is needed — only a note is added.

        This affects (NHWC mode only):
        - Concat/stack axis: dim=1 (channels in NCHW) → axis=-1 (channels in NHWC)
        - Shape indexing: shape[1]=C, shape[2]=H, shape[3]=W (NCHW)
                        → shape[1]=H, shape[2]=W, shape[3]=C (NHWC)
        """
        if self.channels_first:
            # NCHW mode: no axis/shape conversion needed.
            # Add a note so readers know the model uses channels_first.
            if "Conv2D" in source or "Conv2d" in source:
                header = (
                    "\n# NOTE: This model uses data_format='channels_first' (NCHW),\n"
                    "# matching the original PyTorch dimension ordering.\n"
                    "# Input tensors should be in NCHW format "
                    "(batch, channels, height, width).\n"
                )
                import_end = source.rfind("import ")
                if import_end >= 0:
                    line_end = source.index("\n", import_end)
                    source = source[: line_end + 1] + header + source[line_end + 1 :]
            return source

        if self.add_channel_convert:
            # Add note about data format
            if "Conv2D" in source or "Conv2d" in source:
                header = (
                    "\n# NOTE: This model was converted from PyTorch (NCHW) to "
                    "TensorFlow (NHWC).\n"
                    "# Input tensors should be in NHWC format "
                    "(batch, height, width, channels).\n"
                    "# Use nchw_to_nhwc() / nhwc_to_nchw() helpers if needed.\n"
                )
                # Insert after imports
                import_end = source.rfind("import ")
                if import_end >= 0:
                    line_end = source.index("\n", import_end)
                    source = source[: line_end + 1] + header + source[line_end + 1 :]

            # Convert channel-axis references from NCHW dim=1 to NHWC axis=-1
            # tf.concat(..., axis=1) → tf.concat(..., axis=-1)
            source = re.sub(
                r"(tf\.concat\s*\([^)]*),\s*axis\s*=\s*1\s*\)",
                r"\1, axis=-1)",
                source,
            )

            # Convert NCHW axis references in reduction ops to NHWC
            # NCHW→NHWC axis mapping: 0→0, 1→3, 2→1, 3→2
            nchw_to_nhwc_axis = {0: 0, 1: 3, 2: 1, 3: 2}

            def _convert_reduction_axis(match: re.Match) -> str:
                """Convert axis= values from NCHW to NHWC in reduction ops."""
                prefix = match.group(1)
                axis_val = match.group(2).strip()
                # Handle tuple axis like (2, 3)
                if axis_val.startswith("(") and axis_val.endswith(")"):
                    inner = axis_val[1:-1]
                    dims = [d.strip() for d in inner.split(",") if d.strip()]
                    converted = []
                    for d in dims:
                        try:
                            idx = int(d)
                            converted.append(str(nchw_to_nhwc_axis.get(idx, idx)))
                        except ValueError:
                            converted.append(d)
                    return f"{prefix}axis=({', '.join(converted)})"
                # Handle single axis value
                try:
                    idx = int(axis_val)
                    return f"{prefix}axis={nchw_to_nhwc_axis.get(idx, idx)}"
                except ValueError:
                    return match.group(0)

            # Apply to tf.reduce_mean, tf.reduce_sum, tf.reduce_max, tf.reduce_min
            source = re.sub(
                r"(tf\.reduce_(?:mean|sum|max|min)\s*\([^)]*?)\baxis\s*=\s*(\([^)]+\)|\d+)",
                _convert_reduction_axis,
                source,
            )

            # Convert NCHW shape indexing to NHWC:
            # .shape[2] (H in NCHW) → .shape[1] (H in NHWC)
            # .shape[3] (W in NCHW) → .shape[2] (W in NHWC)
            # Use placeholders to avoid double-conversion (e.g. [3]→[2]→[1])
            source = re.sub(r"\.shape\[3\]", ".shape[__NHWC_2__]", source)
            source = re.sub(r"\.shape\[2\]", ".shape[__NHWC_1__]", source)
            source = source.replace("__NHWC_2__", "2")
            source = source.replace("__NHWC_1__", "1")

        return source

    def _add_channel_conversion_helpers(self, source: str) -> str:
        """Add helper functions for channel order conversion."""
        if not self.add_channel_convert:
            return source

        if "Conv2D" not in source and "Conv1D" not in source:
            return source

        helpers = '''

def nchw_to_nhwc(x):
    """Convert tensor from PyTorch format (NCHW) to TensorFlow format (NHWC)."""
    if len(x.shape) == 4:
        return tf.transpose(x, perm=[0, 2, 3, 1])
    return x


def nhwc_to_nchw(x):
    """Convert tensor from TensorFlow format (NHWC) to PyTorch format (NCHW)."""
    if len(x.shape) == 4:
        return tf.transpose(x, perm=[0, 3, 1, 2])
    return x

'''
        return source + helpers

    # ────────────────────────────────────────
    # Custom layers
    # ────────────────────────────────────────

    def _prepend_custom_layers(self, source: str) -> str:
        """Add custom layer definitions for ops not natively in TF."""
        custom_code = ""

        if "PixelShuffle" in source:
            self._custom_layers_needed.add("PixelShuffle")
            custom_code += '''

class PixelShuffle(tf.keras.layers.Layer):
    """Equivalent of torch.nn.PixelShuffle."""

    def __init__(self, upscale_factor, **kwargs):
        super().__init__(**kwargs)
        self.upscale_factor = upscale_factor

    def call(self, x):
        return tf.nn.depth_to_space(x, self.upscale_factor)

    def get_config(self):
        config = super().get_config()
        config["upscale_factor"] = self.upscale_factor
        return config

'''

        if "ReflectionPadding2D" in source:
            self._custom_layers_needed.add("ReflectionPadding2D")
            custom_code += '''

class ReflectionPadding2D(tf.keras.layers.Layer):
    """Equivalent of torch.nn.ReflectionPad2d."""

    def __init__(self, padding=(1, 1), **kwargs):
        super().__init__(**kwargs)
        if isinstance(padding, int):
            self.padding = ((padding, padding), (padding, padding))
        elif len(padding) == 2:
            self.padding = ((padding[0], padding[0]), (padding[1], padding[1]))
        else:
            self.padding = ((padding[0], padding[1]), (padding[2], padding[3]))

    def call(self, x):
        return tf.pad(x, [[0, 0], self.padding[0], self.padding[1], [0, 0]],
                       mode="REFLECT")

    def get_config(self):
        config = super().get_config()
        config["padding"] = self.padding
        return config

'''

        if custom_code:
            # Insert after imports
            lines = source.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i + 1
            lines.insert(insert_idx, custom_code)
            source = "\n".join(lines)

        return source

    # ────────────────────────────────────────
    # Cleanup
    # ────────────────────────────────────────

    def _cleanup(self, source: str) -> str:
        """Final cleanup pass."""
        # Remove duplicate blank lines
        source = re.sub(r"\n{4,}", "\n\n\n", source)

        # Remove leftover torch references (best effort)
        source = source.replace("torch.device", "'cpu'")

        # Catch-all: flag any remaining torch.xxx calls that slipped through
        # Convert known stragglers
        source = source.replace("torch.save", "# torch.save  # TODO: use tf.saved_model.save or model.save_weights")
        source = source.replace("torch.load", "# torch.load  # TODO: use tf.saved_model.load or model.load_weights")

        # Warn about any remaining torch.* references (excluding comments)
        lines = source.split("\n")
        new_lines = []
        for line in lines:
            stripped = line.lstrip()
            # Skip lines that are already comments
            if stripped.startswith("#"):
                new_lines.append(line)
                continue
            # Check for remaining torch references in code (not in strings/comments)
            code_part = line.split("#")[0]  # ignore inline comments
            if re.search(r"\btorch\.\w+", code_part):
                # Add a warning comment
                new_lines.append(f"{line}  # WARNING: unconverted torch reference")
            else:
                new_lines.append(line)
        source = "\n".join(new_lines)

        # Ensure file ends with newline
        if not source.endswith("\n"):
            source += "\n"

        return source
