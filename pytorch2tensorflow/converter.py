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
        # Each entry is (class_name, attr_pattern, pad_value, ndim) where
        # class_name scopes the injection, and attr_pattern matches the
        # attribute call (e.g. "self.conv") in the call() method
        self._explicit_padding_convs: list[tuple[str | None, str, int, int]] = []
        # Flags for runtime helper function injection
        self._needs_pad_helper = False
        self._needs_interpolate_helper = False
        self._needs_flatten_helper = False
        self._needs_bilinear_upsample_helper = False

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
        self._needs_pad_helper = False
        self._needs_interpolate_helper = False
        self._needs_flatten_helper = False
        self._needs_bilinear_upsample_helper = False

        # Step 0: Normalize functional call aliases so all downstream
        # conversions only need to handle the canonical `F.xxx` form.
        result = self._normalize_functional_aliases(source)

        # Step 1: Convert imports
        result = self._convert_imports(result)

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
    # Step 0: Normalize aliases
    # ────────────────────────────────────────

    @staticmethod
    def _normalize_functional_aliases(source: str) -> str:
        """Normalize functional call aliases to canonical F.xxx form.

        Converts:
            torch.nn.functional.xxx(...)  → F.xxx(...)
            nn.functional.xxx(...)        → F.xxx(...)
            torch.nn.Module               → nn.Module  (for class defs)

        This ensures all downstream conversion logic only handles `F.xxx`.
        """
        source = re.sub(r"\btorch\.nn\.functional\.", "F.", source)
        source = re.sub(r"\bnn\.functional\.", "F.", source)
        source = re.sub(r"\btorch\.nn\.Module\b", "nn.Module", source)
        return source

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
        if re.match(r"nn\.(Max|Avg)Pool\dd", pt_layer) and "Adaptive" not in pt_layer:
            source = self._convert_pool_params(source, tf_layer)
        if "LayerNorm" in pt_layer:
            source = self._convert_layernorm_params(source)
        if "GroupNorm" in pt_layer:
            source = self._convert_groupnorm_params(source)
        if "Upsample" in pt_layer or "UpsamplingBilinear" in pt_layer or "UpsamplingNearest" in pt_layer:
            source = self._convert_upsample_params(source, tf_layer)

        # Strip inplace= parameter from activation layers (TF has no inplace)
        if any(act in pt_layer for act in ("ReLU", "LeakyReLU", "ELU", "PReLU",
                                            "GELU", "SiLU", "Mish", "SELU")):
            source = re.sub(
                r"(" + re.escape(tf_layer) + r"\([^)]*?),?\s*inplace\s*=\s*(?:True|False)\s*",
                r"\1",
                source,
            )
            # Also clean up leading comma: Layer(inplace=True) → Layer()
            source = re.sub(
                r"(" + re.escape(tf_layer) + r"\()\s*inplace\s*=\s*(?:True|False)\s*,?\s*",
                r"\1",
                source,
            )

        # In channels_first mode, pooling/upsampling layers also need data_format
        if self.channels_first and ("Pool" in pt_layer or "Upsamp" in pt_layer):
            # Use paren-depth aware matching to handle nested parens like size=(2, 2)
            marker = tf_layer + "("
            result_parts = []
            idx = 0
            while idx < len(source):
                pos = source.find(marker, idx)
                if pos == -1:
                    result_parts.append(source[idx:])
                    break
                result_parts.append(source[idx:pos])
                # Find the matching closing paren
                depth = 1
                j = pos + len(marker)
                while j < len(source) and depth > 0:
                    if source[j] == "(":
                        depth += 1
                    elif source[j] == ")":
                        depth -= 1
                    j += 1
                # j points one past the closing ')'
                call_content = source[pos + len(marker):j - 1]
                if "data_format" not in call_content:
                    result_parts.append(f"{marker}{call_content}, data_format='channels_first')")
                else:
                    result_parts.append(source[pos:j])
                idx = j
            source = "".join(result_parts)

        return source

    @staticmethod
    def _split_args_paren_aware(args_str: str) -> list[str]:
        """Split argument string by commas, respecting nested parens/brackets."""
        parts = []
        depth = 0
        current = []
        for ch in args_str:
            if ch in ("(", "["):
                depth += 1
                current.append(ch)
            elif ch in (")", "]"):
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return parts

    @staticmethod
    def _is_keyword_arg(part: str) -> bool:
        """Check if an argument part is a keyword argument (e.g. 'key=value')."""
        return bool(re.search(r"(?<![=!<>])=(?!=)", part))

    def _convert_conv_params(self, source: str, tf_layer: str) -> str:
        """Convert Conv layer parameters from PyTorch to TF convention.

        PyTorch Conv: nn.Conv2d(in_channels, out_channels, kernel_size, ...)
        TF Conv:      tf.keras.layers.Conv2D(filters, kernel_size, ...)

        Handles:
            - Dropping first positional arg (in_channels)
            - Removing keyword in_channels= / out_channels= → filters=
            - padding int/tuple → 'same'/'valid'
            - stride → strides, dilation → dilation_rate, bias → use_bias
            - Removing output_padding (not supported in TF)
        """
        # Use paren-depth aware extraction to handle nested tuples
        conv_call_full = re.escape(tf_layer) + r"\("

        def _process_conv_call(match: re.Match) -> str:
            start = match.start()
            # Find the matching closing paren
            depth = 1
            i = match.end()
            while i < len(source) and depth > 0:
                if source[i] == "(":
                    depth += 1
                elif source[i] == ")":
                    depth -= 1
                i += 1
            args_str = source[match.end():i - 1]
            parts = self._split_args_paren_aware(args_str)

            # --- Drop in_channels ---
            # Count leading positional args
            num_positional = 0
            for p in parts:
                if self._is_keyword_arg(p):
                    break
                num_positional += 1
            # Drop first positional if there are >= 2 positional args
            if num_positional >= 2:
                parts = parts[1:]

            # Remove keyword in_channels= and rename out_channels= to filters
            cleaned = []
            for p in parts:
                stripped = p.strip()
                if re.match(r"in_channels\s*=", stripped):
                    continue
                if re.match(r"out_channels\s*=", stripped):
                    p = re.sub(r"out_channels\s*=", "", p).strip()
                    # becomes first positional arg (filters)
                cleaned.append(p)
            parts = cleaned

            # --- Keyword renames ---
            renamed = []
            for p in parts:
                s = p.strip()
                # padding: int or tuple → 'same'/'valid'
                m = re.match(r"padding\s*=\s*(.+)$", s)
                if m:
                    val = m.group(1).strip()
                    if val == "0":
                        renamed.append("padding='valid'")
                    elif re.match(r"^\d+$", val):
                        renamed.append("padding='same'")
                    elif re.match(r"^\(\s*0\s*(,\s*0\s*)*\)$", val):
                        renamed.append("padding='valid'")
                    elif re.match(r"^\([\d\s,]+\)$", val):
                        renamed.append("padding='same'")
                    elif val in ("'same'", '"same"', "'valid'", '"valid"'):
                        renamed.append(p)
                    else:
                        renamed.append("padding='same'")
                    continue
                # stride → strides
                s2 = re.sub(r"^stride\s*=", "strides=", s)
                if s2 != s:
                    renamed.append(s2)
                    continue
                # dilation → dilation_rate
                s2 = re.sub(r"^dilation\s*=", "dilation_rate=", s)
                if s2 != s:
                    renamed.append(s2)
                    continue
                # bias → use_bias
                s2 = re.sub(r"^bias\s*=", "use_bias=", s)
                if s2 != s:
                    renamed.append(s2)
                    continue
                # output_padding — not supported in TF, remove
                if re.match(r"output_padding\s*=", s):
                    continue
                renamed.append(p)
            parts = renamed

            return f"{tf_layer}({', '.join(parts)})"

        # Apply to each Conv call (non-overlapping, left to right)
        result = []
        last_end = 0
        for match in re.finditer(conv_call_full, source):
            start = match.start()
            # Find matching closing paren
            depth = 1
            i = match.end()
            while i < len(source) and depth > 0:
                if source[i] == "(":
                    depth += 1
                elif source[i] == ")":
                    depth -= 1
                i += 1
            args_str = source[match.end():i - 1]
            parts = self._split_args_paren_aware(args_str)

            # --- Drop in_channels ---
            num_positional = 0
            for p in parts:
                if self._is_keyword_arg(p):
                    break
                num_positional += 1
            if num_positional >= 2:
                parts = parts[1:]

            # Remove keyword in_channels= and rename out_channels=
            cleaned = []
            for p in parts:
                stripped = p.strip()
                if re.match(r"in_channels\s*=", stripped):
                    continue
                if re.match(r"out_channels\s*=", stripped):
                    p = re.sub(r"out_channels\s*=", "", p).strip()
                cleaned.append(p)
            parts = cleaned

            # --- Keyword renames ---
            renamed = []
            for p in parts:
                s = p.strip()
                # padding: int or tuple → 'same'/'valid'
                m = re.match(r"padding\s*=\s*(.+)$", s)
                if m:
                    val = m.group(1).strip()
                    if val == "0":
                        renamed.append("padding='valid'")
                    elif re.match(r"^\d+$", val):
                        renamed.append("padding='same'")
                    elif re.match(r"^\(\s*0\s*(,\s*0\s*)*\)$", val):
                        renamed.append("padding='valid'")
                    elif re.match(r"^\([\d\s,]+\)$", val):
                        renamed.append("padding='same'")
                    elif val in ("'same'", '"same"', "'valid'", '"valid"'):
                        renamed.append(p)
                    else:
                        renamed.append("padding='same'")
                    continue
                s2 = re.sub(r"^stride\s*=", "strides=", s)
                if s2 != s:
                    renamed.append(s2)
                    continue
                s2 = re.sub(r"^dilation\s*=", "dilation_rate=", s)
                if s2 != s:
                    renamed.append(s2)
                    continue
                s2 = re.sub(r"^bias\s*=", "use_bias=", s)
                if s2 != s:
                    renamed.append(s2)
                    continue
                if re.match(r"output_padding\s*=", s):
                    continue
                renamed.append(p)
            parts = renamed

            result.append(source[last_end:start])
            result.append(f"{tf_layer}({', '.join(parts)})")
            last_end = i

        result.append(source[last_end:])
        source = "".join(result)

        # Fix stride>1 + padding asymmetry (must run after keyword renames)
        if not self.channels_first:
            source = self._fix_stride_padding(source, tf_layer)

        # Add data_format for Conv layers
        if self.channels_first:
            # Use paren-depth aware matching (same as pool/upsample fix)
            conv_marker_pattern = re.compile(r"tf\.keras\.layers\.Conv\w+\(")
            conv_result_parts = []
            cidx = 0
            for cm in conv_marker_pattern.finditer(source):
                conv_result_parts.append(source[cidx:cm.start()])
                cmarker = cm.group(0)
                depth = 1
                cj = cm.end()
                while cj < len(source) and depth > 0:
                    if source[cj] == "(":
                        depth += 1
                    elif source[cj] == ")":
                        depth -= 1
                    cj += 1
                call_inner = source[cm.end():cj - 1]
                if "data_format" not in call_inner:
                    conv_result_parts.append(f"{cmarker}{call_inner}, data_format='channels_first')")
                else:
                    conv_result_parts.append(source[cm.start():cj])
                cidx = cj
            conv_result_parts.append(source[cidx:])
            source = "".join(conv_result_parts)
        # else: channels_last (NHWC) is the TF default, no explicit param needed

        return source

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

        def _find_enclosing_class(pos: int) -> str | None:
            """Find the class name enclosing a given position in source."""
            # Search backwards for the most recent 'class Xxx' definition
            class_pattern = re.compile(r"^class\s+(\w+)\s*[\(:]", re.MULTILINE)
            best = None
            for m in class_pattern.finditer(source[:pos]):
                best = m.group(1)
            return best

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

            # Find enclosing class to scope the padding injection
            class_name = _find_enclosing_class(match.start())

            # Record for explicit padding injection (with class scope)
            self._explicit_padding_convs.append(
                (class_name, f"self.{attr_name}", pad_val, ndim)
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
        # Handle keyword form: num_features=N
        source = re.sub(
            r"(tf\.keras\.layers\.BatchNormalization\()\s*num_features\s*=\s*[^,)]+,?\s*",
            r"\1",
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

        Handles:
            - Dropping first positional arg (in_features)
            - Removing keyword in_features= and renaming out_features=
            - bias → use_bias
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

        # Handle keyword form: Dense(in_features=X, out_features=Y, ...)
        # Remove in_features=, rename out_features= to positional
        def _fix_dense_kwargs(match: re.Match) -> str:
            call = match.group(0)
            # Remove in_features=...
            call = re.sub(r"in_features\s*=\s*[^,)]+,?\s*", "", call)
            # Rename out_features= to positional (just remove the keyword)
            call = re.sub(r"out_features\s*=\s*", "", call)
            # Clean up leading comma after Dense(
            call = re.sub(r"(Dense\()\s*,\s*", r"\1", call)
            return call
        source = re.sub(r"tf\.keras\.layers\.Dense\([^)]*\)", _fix_dense_kwargs, source)

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

    def _convert_upsample_params(self, source: str, tf_layer: str) -> str:
        """Convert nn.Upsample parameters to tf.keras.layers.UpSampling2D.

        PyTorch: nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        TF:      tf.keras.layers.UpSampling2D(size=(2, 2), interpolation='bilinear')
             or: BilinearUpsample2D(scale_factor=2, data_format='channels_first')
                 when align_corners=True and mode='bilinear'

        Parameter mapping:
            scale_factor=N  → size=(N, N)
            mode='nearest'  → interpolation='nearest'
            mode='bilinear' → interpolation='bilinear'
            align_corners   → triggers BilinearUpsample2D when True with bilinear mode
        """
        # First, check if any call has align_corners=True with bilinear mode.
        # If so, replace the entire call with BilinearUpsample2D.
        upsample_marker = tf_layer + "("
        us_result = []
        us_idx = 0
        while us_idx < len(source):
            pos = source.find(upsample_marker, us_idx)
            if pos == -1:
                us_result.append(source[us_idx:])
                break
            us_result.append(source[us_idx:pos])
            # Find matching closing paren
            depth = 1
            uj = pos + len(upsample_marker)
            while uj < len(source) and depth > 0:
                if source[uj] == "(":
                    depth += 1
                elif source[uj] == ")":
                    depth -= 1
                uj += 1
            call_str = source[pos:uj]

            # Check if this is bilinear + align_corners=True
            has_bilinear = bool(re.search(r"mode\s*=\s*['\"]bilinear['\"]", call_str))
            has_align_true = bool(re.search(r"align_corners\s*=\s*True", call_str))

            if has_bilinear and has_align_true:
                # Extract scale_factor
                sf_match = re.search(r"scale_factor\s*=\s*([^,)]+)", call_str)
                scale_factor = sf_match.group(1).strip() if sf_match else "2"
                df_arg = ", data_format='channels_first'" if self.channels_first else ""
                call_str = f"BilinearUpsample2D(scale_factor={scale_factor}{df_arg})"
                self._needs_bilinear_upsample_helper = True
            else:
                # Standard conversion: scale_factor → size, mode → interpolation, strip align_corners
                def _replace_scale_factor(match: re.Match) -> str:
                    factor = match.group(1).strip()
                    if factor.startswith("("):
                        return f"size={factor}"
                    return f"size=({factor}, {factor})"

                call_str = re.sub(
                    r"scale_factor\s*=\s*([^,)]+)",
                    _replace_scale_factor,
                    call_str,
                )
                for pt_mode in ("nearest", "bilinear", "bicubic"):
                    call_str = call_str.replace(f"mode='{pt_mode}'", f"interpolation='{pt_mode}'")
                    call_str = call_str.replace(f'mode="{pt_mode}"', f"interpolation='{pt_mode}'")
                # Remove align_corners
                call_str = re.sub(r",?\s*align_corners\s*=\s*\w+", "", call_str)
                call_str = re.sub(r"\(\s*,", "(", call_str)  # clean leading comma

            us_result.append(call_str)
            us_idx = uj
        source = "".join(us_result)

        return source

    def _convert_pool_params(self, source: str, tf_layer: str) -> str:
        """Convert MaxPool/AvgPool parameters from PyTorch to TF convention.

        PyTorch: nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        TF:      tf.keras.layers.MaxPool2D(pool_size=3, strides=2, padding='same')

        Parameter mapping:
            kernel_size  → pool_size
            stride       → strides
            padding (int)→ 'same'/'valid'
            ceil_mode, return_indices, count_include_pad → removed
        """
        pool_call_full = re.escape(tf_layer) + r"\("

        result = []
        last_end = 0
        for match in re.finditer(pool_call_full, source):
            start = match.start()
            depth = 1
            i = match.end()
            while i < len(source) and depth > 0:
                if source[i] == "(":
                    depth += 1
                elif source[i] == ")":
                    depth -= 1
                i += 1
            args_str = source[match.end():i - 1]
            parts = self._split_args_paren_aware(args_str)

            renamed = []
            padding_val = None
            stride_val = None
            pool_size_val = None
            for p in parts:
                s = p.strip()
                # kernel_size → pool_size
                m = re.match(r"kernel_size\s*=\s*(.+)$", s)
                if m:
                    pool_size_val = m.group(1).strip()
                    renamed.append(f"pool_size={pool_size_val}")
                    continue
                # stride → strides
                m = re.match(r"stride\s*=\s*(.+)$", s)
                if m:
                    stride_val = m.group(1).strip()
                    renamed.append(f"strides={stride_val}")
                    continue
                # padding
                m = re.match(r"padding\s*=\s*(.+)$", s)
                if m:
                    val = m.group(1).strip()
                    padding_val = val
                    if val == "0":
                        renamed.append("padding='valid'")
                    elif re.match(r"^\d+$", val):
                        renamed.append("padding='same'")
                    elif re.match(r"^\(\s*0\s*(,\s*0\s*)*\)$", val):
                        renamed.append("padding='valid'")
                    elif re.match(r"^\([\d\s,]+\)$", val):
                        renamed.append("padding='same'")
                    elif val in ("'same'", '"same"', "'valid'", '"valid"'):
                        renamed.append(p)
                    else:
                        renamed.append("padding='same'")
                    continue
                # Remove unsupported params
                if re.match(r"(ceil_mode|return_indices|count_include_pad)\s*=", s):
                    continue
                # First positional arg (no '=') is kernel_size
                if not self._is_keyword_arg(s) and pool_size_val is None:
                    pool_size_val = s
                    renamed.append(f"pool_size={s}")
                    continue
                renamed.append(p)
            parts = renamed

            # Handle stride + padding asymmetry (same as Conv fix)
            # If stride > 1 and padding > 0, TF 'same' differs from PyTorch
            # Use explicit tf.pad approach
            if padding_val and re.match(r"^\d+$", padding_val) and int(padding_val) > 0:
                if stride_val and re.match(r"^\d+$", stride_val) and int(stride_val) > 1:
                    # Find the attribute name for this pool layer
                    # Look backwards from start for self.xxx = pattern
                    attr_match = re.search(
                        r"self\.(\w+)\s*=\s*$",
                        source[:start],
                    )
                    if attr_match:
                        attr_name = attr_match.group(1)
                        pad_val = int(padding_val)
                        # Determine dimensionality
                        if "1D" in tf_layer or "1d" in tf_layer:
                            ndim = 1
                        elif "3D" in tf_layer or "3d" in tf_layer:
                            ndim = 3
                        else:
                            ndim = 2
                        # Find enclosing class
                        class_pattern = re.compile(r"^class\s+(\w+)\s*[\(:]", re.MULTILINE)
                        class_name = None
                        for cm in class_pattern.finditer(source[:start]):
                            class_name = cm.group(1)
                        self._explicit_padding_convs.append(
                            (class_name, f"self.{attr_name}", pad_val, ndim)
                        )
                        # Change padding to 'valid'
                        parts = [
                            "padding='valid'" if p.strip().startswith("padding=") else p
                            for p in parts
                        ]

            result.append(source[last_end:start])
            result.append(f"{tf_layer}({', '.join(parts)})")
            last_end = i

        result.append(source[last_end:])
        return "".join(result)

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

        Padding injection is scoped to the class where the conv/pool was
        defined, so self.conv1 in ClassA won't get padding meant for ClassB.
        """
        if not self._explicit_padding_convs:
            return source

        # Build a map of class boundaries: {class_name: (start, end)}
        class_pattern = re.compile(r"^class\s+(\w+)\s*[\(:]", re.MULTILINE)
        class_ranges = []  # [(class_name, start, end)]
        matches = list(class_pattern.finditer(source))
        for idx, m in enumerate(matches):
            start = m.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(source)
            class_ranges.append((m.group(1), start, end))

        for target_class, attr_pattern, pad_val, ndim in self._explicit_padding_convs:
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

            # Find the class range for target_class
            if target_class:
                target_ranges = [
                    (s, e) for cn, s, e in class_ranges if cn == target_class
                ]
            else:
                # No class context — apply globally (fallback)
                target_ranges = [(0, len(source))]

            # Apply padding only within the target class scope
            pat = re.compile(
                r"([ \t]*)([^\n]*)" + escaped + r"\((\w+)\)"
            )
            for range_start, range_end in target_ranges:
                segment = source[range_start:range_end]
                new_segment = pat.sub(
                    lambda m, _a=attr_pattern, _p=pad_str: m.group(0).replace(
                        f"{_a}({m.group(3)})",
                        f"{_a}(tf.pad({m.group(3)}, {_p}))",
                    ),
                    segment,
                )
                source = source[:range_start] + new_segment + source[range_end:]
                # Adjust ranges if length changed
                diff = len(new_segment) - len(segment)
                class_ranges = [
                    (cn, s if s <= range_start else s + diff,
                     e if e <= range_start else e + diff)
                    for cn, s, e in class_ranges
                ]

        self._explicit_padding_convs.clear()
        return source

    # ────────────────────────────────────────
    # Functional ops conversion
    # ────────────────────────────────────────

    def _convert_functional_ops(self, source: str) -> str:
        """Convert F.xxx functional operations."""
        # Handle torch.flatten specially before generic replacement
        source = self._convert_torch_flatten(source)

        # Sort by key length descending so longer matches (e.g. torch.log_softmax)
        # are processed before shorter substrings (e.g. torch.log)
        all_ops = {**FUNCTIONAL_MAP, **ACTIVATION_MAP}
        for pt_func, tf_func in sorted(all_ops.items(), key=lambda x: len(x[0]), reverse=True):
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
                if self.channels_first:
                    return f"tf.reshape({tensor}, [tf.shape({tensor})[0], -1])"
                return (
                    f"tf.reshape("
                    f"tf.transpose({tensor}, [0, 3, 1, 2]) "
                    f"if len({tensor}.shape) == 4 else {tensor}, "
                    f"[tf.shape({tensor})[0], -1])"
                )
            elif start_dim == "0":
                return f"tf.reshape({tensor}, [-1])"
            else:
                # Variable or non-literal start_dim — use runtime helper
                self._needs_flatten_helper = True
                cf_str = "True" if self.channels_first else "False"
                return f"_pt_flatten({tensor}, {start_dim}, channels_first={cf_str})"

        # Match torch.flatten(x, start_dim) or torch.flatten(x)
        # start_dim can be a digit or a variable/expression
        source = re.sub(
            r"torch\.flatten\s*\(\s*(\w+)\s*(?:,\s*([\w.]+))?\s*\)",
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

        When scale_factor is a variable/expression (not a simple literal),
        we emit a call to a runtime helper `_pt_interpolate_size()`.
        """
        channels_first = self.channels_first

        # Spatial dim indices depend on data format
        if channels_first:
            h_idx, w_idx = 2, 3  # NCHW
        else:
            h_idx, w_idx = 1, 2  # NHWC

        # Handle scale_factor — may be literal or variable/expression
        # Capture scale_factor value which can be any expression (number, var, tuple, etc.)
        pattern = r"F\.interpolate\s*\(\s*(\w+)\s*,\s*scale_factor\s*=\s*([^,)]+)"

        def _replace_scale_factor(match: re.Match) -> str:
            tensor = match.group(1)
            factor = match.group(2).strip()

            # Simple numeric literal — inline the computation
            if re.match(r"^-?\d+(\.\d+)?$", factor):
                return (
                    f"tf.image.resize({tensor}, "
                    f"size=[tf.shape({tensor})[{h_idx}] * {factor}, "
                    f"tf.shape({tensor})[{w_idx}] * {factor}]"
                )

            # Variable/expression — use runtime helper for safety
            self._needs_interpolate_helper = True
            cf_str = "True" if channels_first else "False"
            return (
                f"tf.image.resize({tensor}, "
                f"size=_pt_scale_factor_to_size({tensor}, {factor}, "
                f"channels_first={cf_str})"
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

        When the padding argument is a variable/expression (not inline literal),
        we emit a call to a runtime helper `_pt_padding_to_tf()` that converts
        PyTorch flat padding format to TF nested padding format at runtime.
        """
        channels_first = self.channels_first

        def _convert_pad_call(match: re.Match) -> str:
            """Replace a single F.pad(...) call."""
            full_call = match.group(0)
            # Find the opening paren after F.pad
            start = match.start()
            paren_start = full_call.index("(")

            # Parse all arguments using paren-aware splitting
            inner = full_call[paren_start + 1:-1]  # strip outer parens
            args = self._split_args_paren_aware(inner)
            if len(args) < 2:
                return full_call  # malformed, leave as-is

            tensor_expr = args[0].strip()
            pad_arg_raw = args[1].strip()
            extra_args = args[2:]

            # Parse mode and value from extra args
            mode = "CONSTANT"
            constant_values = ""
            for arg in extra_args:
                arg = arg.strip()
                mode_match = re.match(r"""mode\s*=\s*['"](\w+)['"]""", arg)
                if mode_match:
                    pt_mode = mode_match.group(1)
                    mode = PADDING_MAP.get(pt_mode, pt_mode.upper())
                    continue
                # Positional mode (string literal without keyword)
                pos_mode_match = re.match(r"""^['"](\w+)['"]$""", arg)
                if pos_mode_match:
                    pt_mode = pos_mode_match.group(1)
                    mode = PADDING_MAP.get(pt_mode, pt_mode.upper())
                    continue
                val_match = re.match(r"value\s*=\s*(.+)", arg)
                if val_match and mode == "CONSTANT":
                    constant_values = f", constant_values={val_match.group(1).strip()}"

            mode_str = f", mode='{mode}'" if mode != "CONSTANT" else ""

            # Try to parse inline literal: (1,1,1,1) or [1,1,1,1]
            inline_match = re.match(r"[\(\[](.*?)[\)\]]$", pad_arg_raw)
            if inline_match:
                pad_values_str = inline_match.group(1)
                pad_values = [v.strip() for v in pad_values_str.split(",") if v.strip()]

                # Check if all values are simple literals/numbers (statically resolvable)
                all_simple = all(
                    re.match(r"^-?\d+(\.\d+)?$", v) for v in pad_values
                )
                if all_simple:
                    return self._build_static_tf_pad(
                        tensor_expr, pad_values, mode, constant_values, channels_first
                    )

            # Dynamic/variable padding — use runtime helper
            self._needs_pad_helper = True
            cf_str = "True" if channels_first else "False"
            return (
                f"tf.pad({tensor_expr}, "
                f"_pt_padding_to_tf({pad_arg_raw}, len({tensor_expr}.shape), "
                f"channels_first={cf_str})"
                f"{mode_str}{constant_values})"
            )

        # Match F.pad(...) with balanced parentheses
        result = []
        i = 0
        while i < len(source):
            # Look for F.pad(
            match = re.search(r"F\.pad\s*\(", source[i:])
            if not match:
                result.append(source[i:])
                break

            # Add everything before the match
            result.append(source[i:i + match.start()])

            # Find balanced closing paren
            call_start = i + match.start()
            paren_pos = i + match.end() - 1  # position of '('
            depth = 1
            j = paren_pos + 1
            while j < len(source) and depth > 0:
                if source[j] == "(":
                    depth += 1
                elif source[j] == ")":
                    depth -= 1
                j += 1

            full_call = source[call_start:j]
            fake_match = re.match(r".*", full_call)  # dummy match for group(0)

            class _FakeMatch:
                def __init__(self, text):
                    self._text = text
                def group(self, n=0):
                    return self._text
                def start(self):
                    return 0
                def end(self):
                    return len(self._text)

            converted = _convert_pad_call(_FakeMatch(full_call))
            result.append(converted)
            i = j

        return "".join(result)

    @staticmethod
    def _build_static_tf_pad(
        tensor: str,
        pad_values: list,
        mode: str,
        constant_values: str,
        channels_first: bool,
    ) -> str:
        """Build tf.pad() with statically known padding values."""
        use_nchw = channels_first
        mode_str = f", mode='{mode}'" if mode != "CONSTANT" else ""

        if len(pad_values) == 2:
            if use_nchw:
                paddings = f"[[0, 0], [0, 0], [0, 0], [{pad_values[0]}, {pad_values[1]}]]"
            else:
                paddings = f"[[0, 0], [0, 0], [{pad_values[0]}, {pad_values[1]}], [0, 0]]"
        elif len(pad_values) == 4:
            left, right, top, bottom = pad_values
            if use_nchw:
                paddings = f"[[0, 0], [0, 0], [{top}, {bottom}], [{left}, {right}]]"
            else:
                paddings = f"[[0, 0], [{top}, {bottom}], [{left}, {right}], [0, 0]]"
        elif len(pad_values) == 6:
            left, right, top, bottom, front, back = pad_values
            if use_nchw:
                paddings = f"[[0, 0], [0, 0], [{front}, {back}], [{top}, {bottom}], [{left}, {right}]]"
            else:
                paddings = f"[[0, 0], [{front}, {back}], [{top}, {bottom}], [{left}, {right}], [0, 0]]"
        else:
            paddings = f"[{', '.join(pad_values)}]"

        return f"tf.pad({tensor}, {paddings}{mode_str}{constant_values})"

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

    def _convert_method_to_func(
        self,
        source: str,
        method: str,
        tf_func: str,
        args_transform=None,
        wrap_args: str | None = None,
    ) -> str:
        """Generic converter: expr.method(args) → tf_func(expr, args).

        Uses backward scanning to correctly handle complex expressions as
        the receiver (function calls, parenthesized exprs, chained attrs).

        Args:
            source: Source code string.
            method: PyTorch method name (e.g. "view", "sum").
            tf_func: TF function name (e.g. "tf.reshape", "tf.reduce_sum").
            args_transform: Optional callable(args_str) → transformed_args.
            wrap_args: If set, wraps positional args: e.g. "[]" turns
                `args` into `[args]`.
        """
        # Find all `.method(` occurrences
        pattern = re.compile(r"\." + re.escape(method) + r"\s*\(")
        result = []
        last_end = 0

        for m in pattern.finditer(source):
            dot_pos = m.start()  # position of the `.`
            open_paren = m.end() - 1  # position of `(`

            # Extract the expression preceding `.method(`
            expr, expr_start = self._scan_preceding_expr(source, dot_pos)
            if not expr:
                continue
            # Skip already-converted tf.xxx / np.xxx module names as receiver
            # e.g. "tf" in "tf.reshape(" or "tf.keras" in "tf.keras.layers.Dense("
            if re.match(r"^(tf|np|math)(\.[\w]+)*$", expr):
                continue

            # Find the matching closing paren for args
            depth = 1
            i = open_paren + 1
            while i < len(source) and depth > 0:
                if source[i] == "(":
                    depth += 1
                elif source[i] == ")":
                    depth -= 1
                i += 1
            if depth != 0:
                continue

            args_str = source[open_paren + 1:i - 1].strip()

            # Transform args if needed
            if args_transform:
                args_str = args_transform(args_str)
            if wrap_args and args_str:
                args_str = f"{wrap_args[0]}{args_str}{wrap_args[1]}"

            # Build replacement
            if args_str:
                replacement = f"{tf_func}({expr}, {args_str})"
            else:
                replacement = f"{tf_func}({expr})"

            result.append(source[last_end:expr_start])
            result.append(replacement)
            last_end = i

        result.append(source[last_end:])
        return "".join(result)

    def _convert_tensor_methods(self, source: str) -> str:
        """Convert tensor methods like .view(), .permute(), etc.

        Conversion order matters for chains like `(a-b).abs().mean()`:
        1. First: no-arg methods (.abs, .exp, ...) and simple transforms
           (.contiguous, .detach, .clone, type casts, device ops)
           These produce clean expressions for subsequent steps.
        2. Then: arg-taking methods (.view, .sum, .mean, .clamp, ...)
           These can now match function-call results like tf.abs(x).
        """
        # ── Phase 1: No-arg transforms (innermost first) ──

        # .contiguous() → remove (no-op in TF)
        source = re.sub(r"\.contiguous\(\)", "", source)

        # Device operations (no-op in TF) — strip .cuda()/.cpu()/.to(...)
        for dev_suffix in (".cuda()", ".cpu()"):
            source = source.replace(dev_suffix, "")
        source = re.sub(r"\.to\s*\([^)]*\)", "", source)

        # .item() → .numpy()
        source = re.sub(r"\.item\(\)", ".numpy()", source)

        # .detach() → tf.stop_gradient
        source = self._convert_method_to_func(source, "detach", "tf.stop_gradient")

        # .clone() → tf.identity
        source = self._convert_method_to_func(source, "clone", "tf.identity")

        # Type casting: .float() → tf.cast(x, tf.float32), etc.
        cast_map = {
            "float": "tf.float32",
            "long": "tf.int64",
            "int": "tf.int32",
            "half": "tf.float16",
            "bool": "tf.bool",
            "double": "tf.float64",
        }
        for pt_method, tf_dtype in cast_map.items():
            suffix = f".{pt_method}()"
            while suffix in source:
                pos = source.find(suffix)
                expr, expr_start = self._scan_preceding_expr(source, pos)
                if expr:
                    source = (source[:expr_start]
                              + f"tf.cast({expr}, {tf_dtype})"
                              + source[pos + len(suffix):])
                else:
                    break

        # No-arg tensor methods: x.abs() → tf.abs(x), (expr).abs() → tf.abs(expr)
        noarg_method_map = {
            "abs": "tf.abs",
            "exp": "tf.exp",
            "log": "tf.math.log",
            "sqrt": "tf.math.sqrt",
            "neg": "tf.negative",
            "sign": "tf.sign",
            "ceil": "tf.math.ceil",
            "floor": "tf.math.floor",
            "round": "tf.math.round",
            "sigmoid": "tf.math.sigmoid",
            "tanh": "tf.math.tanh",
            "relu": "tf.nn.relu",
        }
        for pt_method, tf_func in noarg_method_map.items():
            source = self._convert_noarg_method(source, pt_method, tf_func)

        # ── Phase 2: Arg-taking methods ──

        def _rename_dim_keepdim(args: str) -> str:
            args = re.sub(r"\bdim\s*=", "axis=", args)
            args = re.sub(r"\bkeepdim\s*=", "keepdims=", args)
            return args

        # .view() → tf.reshape(x, [args])
        source = self._convert_method_to_func(
            source, "view", "tf.reshape", wrap_args="[]")

        # .reshape() → tf.reshape(x, [args])
        source = self._convert_method_to_func(
            source, "reshape", "tf.reshape", wrap_args="[]")

        # .permute() → tf.transpose(x, perm=[args])
        source = self._convert_method_to_func(
            source, "permute", "tf.transpose",
            args_transform=lambda a: f"perm=[{a}]")

        # .transpose(a, b) → tf.transpose(x, perm=[a, b])
        source = self._convert_method_to_func(
            source, "transpose", "tf.transpose",
            args_transform=lambda a: f"perm=[{a}]")

        # .contiguous() → remove (no-op in TF)
        source = re.sub(r"\.contiguous\(\)", "", source)

        # .unsqueeze(dim) → tf.expand_dims(x, axis=dim)
        source = self._convert_method_to_func(
            source, "unsqueeze", "tf.expand_dims",
            args_transform=lambda a: f"axis={a}")

        # .squeeze(dim) → tf.squeeze(x, axis=dim)
        source = self._convert_method_to_func(
            source, "squeeze", "tf.squeeze",
            args_transform=lambda a: f"axis={a}" if a else "")

        # .flatten(start_dim) → tf.reshape
        def _replace_method_flatten(match: re.Match) -> str:
            tensor = match.group(1)
            start_dim = match.group(2)
            if start_dim == "1":
                if self.channels_first:
                    return f"tf.reshape({tensor}, [tf.shape({tensor})[0], -1])"
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

        # .softmax(dim) / .log_softmax(dim) → tf.nn.softmax / tf.nn.log_softmax
        source = self._convert_method_to_func(
            source, "softmax", "tf.nn.softmax", args_transform=_rename_dim_keepdim)
        source = self._convert_method_to_func(
            source, "log_softmax", "tf.nn.log_softmax", args_transform=_rename_dim_keepdim)

        # .mean(dim) / .sum(dim) / .max(dim) / .min(dim)
        source = self._convert_method_to_func(
            source, "mean", "tf.reduce_mean", args_transform=_rename_dim_keepdim)
        source = self._convert_method_to_func(
            source, "sum", "tf.reduce_sum", args_transform=_rename_dim_keepdim)

        # .clamp(min, max) → tf.clip_by_value
        def _clamp_args(args: str) -> str:
            args = re.sub(r"\bmin\s*=", "clip_value_min=", args)
            args = re.sub(r"\bmax\s*=", "clip_value_max=", args)
            return args
        source = self._convert_method_to_func(
            source, "clamp", "tf.clip_by_value", args_transform=_clamp_args)
        source = self._convert_method_to_func(
            source, "clip", "tf.clip_by_value", args_transform=_clamp_args)

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
        source = self._convert_method_to_func(
            source, "repeat", "tf.tile", wrap_args="[]")

        # .expand() → tf.broadcast_to
        source = self._convert_method_to_func(
            source, "expand", "tf.broadcast_to", wrap_args="[]")

        # .numel() → tf.size
        source = self._convert_method_to_func(source, "numel", "tf.size")

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

        # Dynamic shape unpacking: a, b, c, d = x.shape → a, b, c, d = tf.unstack(tf.shape(x))
        # PyTorch .shape returns a Size (tuple-like) with concrete ints;
        # TF .shape returns TensorShape with None for dynamic dims, breaking arithmetic.
        # tf.unstack(tf.shape(x)) gives scalar tensors that support arithmetic.
        source = re.sub(
            r"(\w+(?:\s*,\s*\w+)+)\s*=\s*(\w+)\.shape\b(?!\[)",
            r"\1 = tf.unstack(tf.shape(\2))",
            source,
        )

        # Sequential indexing: self.xxx[N] → self.xxx.layers[N]
        # PyTorch nn.Sequential supports [] indexing; TF Sequential uses .layers[]
        source = re.sub(
            r"(self\.\w+)\[(\d+)\]",
            r"\1.layers[\2]",
            source,
        )

        return source

    def _convert_noarg_method(self, source: str, method: str, tf_func: str) -> str:
        """Convert x.method() / (expr).method() → tf_func(x) / tf_func(expr).

        Uses backward scanning from each `.method()` match to find the
        full preceding expression, handling nested parens/brackets and
        function call chains like `tf.abs(x).method()`.
        """
        suffix = f".{method}()"
        result = []
        i = 0
        while i < len(source):
            pos = source.find(suffix, i)
            if pos == -1:
                result.append(source[i:])
                break
            # Extract the expression preceding `.method()`
            expr_end = pos
            expr, expr_start = self._scan_preceding_expr(source, expr_end)
            if expr:
                result.append(source[i:expr_start])
                result.append(f"{tf_func}({expr})")
                i = pos + len(suffix)
            else:
                result.append(source[i:pos + len(suffix)])
                i = pos + len(suffix)
        return "".join(result)

    @staticmethod
    def _scan_preceding_expr(source: str, end: int) -> tuple[str, int]:
        """Scan backwards from `end` to find the full expression.

        Returns (expr_string, start_index) or ("", end) on failure.
        Handles:
            - Simple variables:     `x`
            - Dotted names:         `self.layer`
            - Function calls:       `fn(...)`, `tf.abs(...)`
            - Paren expressions:    `(a - b)`
            - Chained calls:        `self.fn(x).attr`
        """
        if end <= 0:
            return "", end
        j = end - 1
        # Skip trailing whitespace
        while j >= 0 and source[j] in " \t":
            j -= 1
        if j < 0:
            return "", end

        # If preceded by ), we need to match backwards to the opening (
        if source[j] == ")":
            depth = 1
            k = j - 1
            while k >= 0 and depth > 0:
                if source[k] == ")":
                    depth += 1
                elif source[k] == "(":
                    depth -= 1
                k -= 1
            if depth != 0:
                return "", end
            # k is now one before the opening '('
            # Continue scanning backwards for function name / dotted access
            k2 = k
            while k2 >= 0 and source[k2] in " \t":
                k2 -= 1
            if k2 >= 0 and (source[k2].isalnum() or source[k2] in "_.]"):
                # There's a function name before the paren
                inner_expr, inner_start = ModelConverter._scan_preceding_expr(source, k2 + 1)
                if inner_expr:
                    return source[inner_start:j + 1], inner_start
            # Bare parenthesized expression
            return source[k + 1:j + 1], k + 1
        elif source[j] == "]":
            # Bracket indexing: scan back to matching [
            depth = 1
            k = j - 1
            while k >= 0 and depth > 0:
                if source[k] == "]":
                    depth += 1
                elif source[k] == "[":
                    depth -= 1
                k -= 1
            if depth != 0:
                return "", end
            inner_expr, inner_start = ModelConverter._scan_preceding_expr(source, k + 1)
            if inner_expr:
                return source[inner_start:j + 1], inner_start
            return source[k + 1:j + 1], k + 1
        elif source[j].isalnum() or source[j] == "_":
            # Identifier (possibly dotted: self.layer, tf.abs)
            k = j
            while k >= 0 and (source[k].isalnum() or source[k] in "_."):
                k -= 1
            start = k + 1
            # If the scanned token starts with '.', it's a method/attribute
            # access on a preceding expression (e.g. `fn(args).method`).
            # Recursively scan backwards to include the receiver expression.
            if source[start] == "." and start > 0:
                prev_expr, prev_start = ModelConverter._scan_preceding_expr(
                    source, start
                )
                if prev_expr:
                    return source[prev_start : j + 1], prev_start
            # Trim trailing dots
            expr = source[start:j + 1].rstrip(".")
            return expr, start
        else:
            return "", end

    # ────────────────────────────────────────
    # torch.* operations conversion
    # ────────────────────────────────────────

    def _convert_torch_ops(self, source: str) -> str:
        """Convert remaining torch.xxx operations."""
        # Sort by key length descending to avoid substring collisions
        # (e.g. torch.log replacing the prefix of torch.log_softmax)
        for pt_op, tf_op in sorted(FUNCTIONAL_MAP.items(), key=lambda x: len(x[0]), reverse=True):
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

        # Runtime helper functions for dynamic parameter conversion
        if self._needs_pad_helper:
            custom_code += '''

def _pt_padding_to_tf(padding, ndim=4, channels_first=False):
    """Convert PyTorch flat padding to TensorFlow nested padding at runtime.

    PyTorch padding is a flat tuple: (left, right, top, bottom[, front, back])
    from innermost dim to outermost dim.
    TF padding is nested: [[before_0, after_0], [before_1, after_1], ...]
    for each dimension (NHWC or NCHW).
    """
    import tensorflow as tf
    if isinstance(padding, (int, float)):
        padding = (int(padding), int(padding))
    padding = list(padding)
    n_pad_dims = len(padding) // 2
    # Build pairs: [(left, right), (top, bottom), ...]
    pairs = [[padding[2 * i], padding[2 * i + 1]] for i in range(n_pad_dims)]
    # Reverse order: PyTorch pads from innermost to outermost
    pairs = pairs[::-1]
    # Build full padding for each dim (ndim dimensions)
    full = [[0, 0] for _ in range(ndim)]
    if channels_first:
        # NCHW: spatial dims are [2, 3, ...] from the end
        for i, pair in enumerate(pairs):
            dim_idx = ndim - 1 - i  # innermost spatial dim first
            full[dim_idx] = pair
    else:
        # NHWC: spatial dims are [1, 2, ...] (skip batch), channel is last
        for i, pair in enumerate(pairs):
            dim_idx = ndim - 2 - i  # skip last (channel) dim
            full[dim_idx] = pair
    return tf.constant(full, dtype=tf.int32)

'''

        if self._needs_interpolate_helper:
            custom_code += '''

def _pt_scale_factor_to_size(tensor, scale_factor, channels_first=False):
    """Convert PyTorch scale_factor to TF size=[H, W] at runtime.

    Computes the target spatial size by multiplying current spatial dimensions
    by the scale_factor.
    """
    import tensorflow as tf
    shape = tf.shape(tensor)
    if channels_first:
        h, w = shape[2], shape[3]
    else:
        h, w = shape[1], shape[2]
    if isinstance(scale_factor, (tuple, list)):
        sh, sw = scale_factor[0], scale_factor[1]
    else:
        sh, sw = scale_factor, scale_factor
    return [h * sh, w * sw]

'''

        if self._needs_bilinear_upsample_helper:
            custom_code += '''

class BilinearUpsample2D(tf.keras.layers.Layer):
    """Bilinear upsampling with align_corners=True support.

    Equivalent to PyTorch nn.Upsample(scale_factor=N, mode='bilinear', align_corners=True).
    TF's built-in UpSampling2D does not support align_corners, which causes
    significant numerical differences for bilinear interpolation.
    """

    def __init__(self, scale_factor=2, data_format='channels_last', **kwargs):
        super().__init__(**kwargs)
        self.scale_factor = scale_factor
        self.data_format = data_format

    def call(self, x):
        import tensorflow as tf
        if self.data_format == 'channels_first':
            # NCHW -> NHWC for resize
            x = tf.transpose(x, [0, 2, 3, 1])
        shape = tf.shape(x)
        new_h = shape[1] * self.scale_factor
        new_w = shape[2] * self.scale_factor
        x = tf.compat.v1.image.resize_bilinear(x, [new_h, new_w], align_corners=True)
        if self.data_format == 'channels_first':
            # NHWC -> NCHW
            x = tf.transpose(x, [0, 3, 1, 2])
        return x

    def get_config(self):
        config = super().get_config()
        config["scale_factor"] = self.scale_factor
        config["data_format"] = self.data_format
        return config

'''

        if self._needs_flatten_helper:
            custom_code += '''

def _pt_flatten(tensor, start_dim=0, channels_first=False):
    """Convert PyTorch flatten with variable start_dim to TF reshape.

    When start_dim is variable, we build the target shape dynamically.
    For start_dim=1 on 4D NHWC tensors, transposes to NCHW first so that
    element order matches PyTorch's Linear layer expectations.
    """
    import tensorflow as tf
    if start_dim == 1 and len(tensor.shape) == 4 and not channels_first:
        tensor = tf.transpose(tensor, [0, 3, 1, 2])
    shape = tf.shape(tensor)
    if start_dim == 0:
        return tf.reshape(tensor, [-1])
    leading = shape[:start_dim]
    return tf.reshape(tensor, tf.concat([leading, [-1]], axis=0))

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
