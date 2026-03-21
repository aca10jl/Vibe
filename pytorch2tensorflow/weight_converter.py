"""
PyTorch Weight (.pth) → TensorFlow Weight Converter

Converts PyTorch checkpoint files to TensorFlow-compatible weights.
Handles:
    - state_dict loading and parsing
    - Weight name mapping (PyTorch → Keras naming convention)
    - Weight shape transposition (OIHW → HWIO for convolutions, etc.)
    - BatchNorm running stats conversion
    - Partial / selective weight loading
    - Verification of weight shapes after conversion
"""

import re
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class WeightConverter:
    """Convert PyTorch .pth weights to TensorFlow format."""

    # Weight shape transpose rules
    TRANSPOSE_RULES = {
        "conv2d": (2, 3, 1, 0),       # [O,I,H,W] → [H,W,I,O]
        "conv1d": (2, 1, 0),           # [O,I,L] → [L,I,O]
        "conv3d": (2, 3, 4, 1, 0),     # [O,I,D,H,W] → [D,H,W,I,O]
        "conv_transpose": (2, 3, 1, 0),  # [I,O,H,W] → [H,W,O,I]
        "depthwise": (2, 3, 0, 1),     # [C,1,H,W] → [H,W,C,1]
        "linear": (1, 0),              # [O,I] → [I,O]
    }

    # PyTorch → TF weight name components
    NAME_MAP = {
        "weight": "kernel",
        "bias": "bias",
        "running_mean": "moving_mean",
        "running_var": "moving_variance",
    }

    # BatchNorm uses gamma/beta instead of kernel/bias in TF
    BN_NAME_MAP = {
        "weight": "gamma",
        "bias": "beta",
        "running_mean": "moving_mean",
        "running_var": "moving_variance",
    }

    # Keys to skip (not used in TF)
    SKIP_KEYS = {"num_batches_tracked"}

    def __init__(self, strict: bool = True):
        """
        Args:
            strict: If True, raise errors on unmatched weights.
                If False, skip unmatched weights with warnings.
        """
        self.strict = strict
        self._conversion_log: list[dict] = []

    # ────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────

    def convert(
        self,
        pytorch_path: str,
        tf_model,
        output_path: Optional[str] = None,
        name_mapping: Optional[dict] = None,
    ) -> dict:
        """Convert PyTorch weights and load into TensorFlow model.

        Args:
            pytorch_path: Path to the PyTorch .pth checkpoint file.
            tf_model: A built tf.keras.Model instance to load weights into.
            output_path: Optional path to save converted weights (.h5 or dir).
            name_mapping: Optional custom name mapping overrides.

        Returns:
            Dictionary with conversion statistics and details.
        """
        import torch

        self._conversion_log.clear()

        # Load PyTorch state dict
        state_dict = self._load_pytorch_checkpoint(pytorch_path)

        # Try name-based mapping first
        mapping = self._build_name_mapping(state_dict, tf_model, name_mapping)

        # If name-based mapping found very few matches, fall back to
        # structural/positional matching
        matched_count = sum(1 for v in mapping.values() if v is not None)
        total_mappable = sum(
            1 for k in state_dict
            if not any(skip in k for skip in self.SKIP_KEYS)
        )

        if matched_count < total_mappable * 0.5:
            logger.info(
                "Name-based mapping found only %d/%d matches, "
                "falling back to structural matching",
                matched_count, total_mappable,
            )
            stats = self._assign_weights_structural(state_dict, tf_model)
        else:
            stats = self._assign_weights(state_dict, tf_model, mapping)

        # Save if requested
        if output_path:
            self._save_tf_weights(tf_model, output_path)

        return stats

    def convert_state_dict_to_numpy(
        self,
        pytorch_path: str,
        output_dir: Optional[str] = None,
    ) -> dict[str, np.ndarray]:
        """Convert PyTorch state dict to numpy arrays without a TF model.

        Useful for manual weight inspection or custom loading.

        Args:
            pytorch_path: Path to the PyTorch .pth checkpoint file.
            output_dir: Optional directory to save .npy files.

        Returns:
            Dictionary mapping converted weight names to numpy arrays.
        """
        import torch

        state_dict = self._load_pytorch_checkpoint(pytorch_path)
        converted = {}

        for name, tensor in state_dict.items():
            # Skip non-weight entries
            if any(skip in name for skip in self.SKIP_KEYS):
                continue

            np_array = tensor.cpu().numpy()

            # Determine transpose rule
            new_name = self._convert_weight_name(name)
            transpose_rule = self._get_transpose_rule(name, np_array)

            if transpose_rule:
                np_array = np.transpose(np_array, transpose_rule)

            converted[new_name] = np_array

        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            for name, arr in converted.items():
                safe_name = name.replace("/", "_").replace(":", "_")
                np.save(out_path / f"{safe_name}.npy", arr)
            logger.info("Saved %d weight files to %s", len(converted), output_dir)

        return converted

    def get_conversion_log(self) -> list[dict]:
        """Return detailed log of the last conversion."""
        return self._conversion_log.copy()

    # ────────────────────────────────────────
    # Internal: Loading
    # ────────────────────────────────────────

    def _load_pytorch_checkpoint(self, path: str) -> dict:
        """Load PyTorch checkpoint and extract state dict."""
        import torch

        checkpoint = torch.load(path, map_location="cpu", weights_only=False)

        # Handle different checkpoint formats
        if isinstance(checkpoint, dict):
            for key in ("state_dict", "model_state_dict", "model", "net", "params"):
                if key in checkpoint:
                    logger.info("Found state dict under key '%s'", key)
                    return checkpoint[key]
            # If the dict looks like a state dict itself (has tensor values)
            if any(isinstance(v, torch.Tensor) for v in checkpoint.values()):
                return checkpoint
            # Try the first dict-like value
            for key, val in checkpoint.items():
                if isinstance(val, dict) and any(
                    isinstance(v, torch.Tensor) for v in val.values()
                ):
                    logger.info("Using nested dict under key '%s' as state dict", key)
                    return val
            return checkpoint
        elif hasattr(checkpoint, "state_dict"):
            return checkpoint.state_dict()
        else:
            raise ValueError(
                f"Cannot extract state dict from checkpoint of type "
                f"{type(checkpoint).__name__}"
            )

    # ────────────────────────────────────────
    # Internal: Name mapping
    # ────────────────────────────────────────

    def _build_name_mapping(
        self,
        state_dict: dict,
        tf_model,
        custom_mapping: Optional[dict] = None,
    ) -> dict[str, str]:
        """Build mapping from PyTorch weight names to TF variable names."""
        import tensorflow as tf

        # Get TF model weight names
        tf_weights = {w.name: w for w in tf_model.weights}
        tf_weight_names = set(tf_weights.keys())

        mapping = {}

        if custom_mapping:
            mapping.update(custom_mapping)

        # Auto-map remaining weights
        for pt_name in state_dict.keys():
            if pt_name in mapping:
                continue
            if any(skip in pt_name for skip in self.SKIP_KEYS):
                continue

            tf_name = self._convert_weight_name(pt_name)

            # Try to find matching TF weight
            matched = self._find_tf_weight_match(tf_name, tf_weight_names)
            if matched:
                mapping[pt_name] = matched
            else:
                logger.warning("No TF match for PyTorch weight: %s → %s", pt_name, tf_name)

        return mapping

    def _convert_weight_name(self, pt_name: str) -> str:
        """Convert a PyTorch weight name to TF naming convention."""
        name = pt_name

        # Remove 'module.' prefix (from DataParallel)
        name = re.sub(r"^module\.", "", name)

        # Replace PyTorch-specific suffixes
        for pt_suffix, tf_suffix in self.NAME_MAP.items():
            if name.endswith(f".{pt_suffix}"):
                name = name[: -len(pt_suffix)] + tf_suffix
                break

        # Replace dots with slashes (TF convention)
        name = name.replace(".", "/")

        return name

    def _find_tf_weight_match(self, converted_name: str, tf_names: set[str]) -> Optional[str]:
        """Find the best matching TF weight name."""
        # Exact match
        for tf_name in tf_names:
            if converted_name in tf_name:
                return tf_name

        # Try matching without index numbers
        simplified = re.sub(r"/\d+/", "/", converted_name)
        for tf_name in tf_names:
            tf_simplified = re.sub(r"/\d+/", "/", tf_name)
            if simplified in tf_simplified:
                return tf_name

        # Try matching last components
        parts = converted_name.split("/")
        if len(parts) >= 2:
            suffix = "/".join(parts[-2:])
            for tf_name in tf_names:
                if tf_name.endswith(suffix) or suffix in tf_name:
                    return tf_name

        return None

    # ────────────────────────────────────────
    # Internal: Weight assignment
    # ────────────────────────────────────────

    def _assign_weights(
        self,
        state_dict: dict,
        tf_model,
        mapping: dict[str, str],
    ) -> dict:
        """Convert and assign weights from PyTorch to TF model."""
        import tensorflow as tf
        import torch

        tf_weights = {w.name: w for w in tf_model.weights}
        assigned = 0
        skipped = 0
        errors = []

        for pt_name, tensor in state_dict.items():
            if any(skip in pt_name for skip in self.SKIP_KEYS):
                skipped += 1
                continue

            if pt_name not in mapping:
                skipped += 1
                self._log("skip", pt_name, reason="no mapping found")
                continue

            tf_name = mapping[pt_name]
            if tf_name not in tf_weights:
                skipped += 1
                self._log("skip", pt_name, tf_name=tf_name, reason="TF weight not found")
                continue

            tf_var = tf_weights[tf_name]
            np_array = tensor.cpu().numpy()

            # Apply transpose if needed
            transpose_rule = self._get_transpose_rule(pt_name, np_array)
            original_shape = np_array.shape
            if transpose_rule:
                np_array = np.transpose(np_array, transpose_rule)

            # Verify shape compatibility
            tf_shape = tuple(tf_var.shape)
            np_shape = np_array.shape

            if tf_shape != np_shape:
                msg = (
                    f"Shape mismatch for {pt_name}: "
                    f"converted={np_shape}, expected={tf_shape}"
                )
                if self.strict:
                    errors.append(msg)
                    self._log("error", pt_name, tf_name=tf_name, reason=msg)
                    continue
                else:
                    logger.warning(msg)
                    # Try to reshape if total elements match
                    if np.prod(np_shape) == np.prod(tf_shape):
                        np_array = np_array.reshape(tf_shape)
                        logger.info("Reshaped %s: %s → %s", pt_name, np_shape, tf_shape)
                    else:
                        self._log("error", pt_name, tf_name=tf_name, reason=msg)
                        continue

            # Assign weight
            tf_var.assign(np_array)
            assigned += 1
            self._log(
                "assigned",
                pt_name,
                tf_name=tf_name,
                pt_shape=original_shape,
                tf_shape=tf_shape,
                transposed=transpose_rule is not None,
            )

        stats = {
            "total_pytorch_weights": len(state_dict),
            "assigned": assigned,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors,
            "tf_model_weights": len(tf_weights),
        }

        if errors and self.strict:
            logger.error(
                "Weight conversion completed with %d errors:\n%s",
                len(errors),
                "\n".join(errors),
            )

        logger.info(
            "Weight conversion: %d/%d assigned, %d skipped, %d errors",
            assigned,
            len(state_dict),
            skipped,
            len(errors),
        )

        return stats

    def _assign_weights_structural(
        self,
        state_dict: dict,
        tf_model,
    ) -> dict:
        """Assign weights using structural/positional matching.

        This approach matches PyTorch and TF weights by their structural
        position in the model, rather than by name. Works when the two
        models have the same architecture but different naming conventions.

        The key insight: both PyTorch and TF iterate weights in the same
        structural order (layer by layer, weight then bias/BN params).
        We classify each weight by its role (conv kernel, BN gamma, etc.)
        and match them positionally.
        """
        import tensorflow as tf

        # Pre-identify BN layers by finding running_mean/running_var keys
        bn_prefixes = set()
        for name in state_dict.keys():
            if name.endswith(".running_mean") or name.endswith(".running_var"):
                prefix = name.rsplit(".", 1)[0]
                bn_prefixes.add(prefix)

        # Pre-identify ConvTranspose layers: 4D weight where dim0 < dim1
        # (PyTorch ConvTranspose2d shape is [I, O, H, W] where I < O
        #  while regular Conv2d is [O, I, H, W] where O > I typically)
        # Also check the TF model for Conv2DTranspose layers to confirm.
        conv_transpose_prefixes = set()
        # Collect TF Conv2DTranspose layer names
        tf_has_conv_transpose = any(
            "conv2d_transpose" in w.name.lower() or "conv_transpose" in w.name.lower()
            for w in tf_model.weights
        )
        if tf_has_conv_transpose:
            for name, tensor in state_dict.items():
                if name.endswith(".weight") and tensor.ndim == 4:
                    # ConvTranspose2d: shape [I, O, H, W] where typically I < O
                    # But we also check name heuristic
                    parent = name.rsplit(".", 1)[0]
                    name_lower = name.lower()
                    if ("up" in name_lower or "deconv" in name_lower
                            or "transpose" in name_lower
                            or "upsample" in name_lower):
                        conv_transpose_prefixes.add(parent)
                    elif tensor.shape[0] < tensor.shape[1]:
                        # [I, O, H, W] pattern: input channels < output channels
                        # This is common in ConvTranspose (upsampling doubles channels)
                        conv_transpose_prefixes.add(parent)

        # Classify PT weights into ordered groups
        pt_weights = []
        for name, tensor in state_dict.items():
            if any(skip in name for skip in self.SKIP_KEYS):
                continue
            np_array = tensor.cpu().numpy()
            role = self._classify_weight_role(
                name, np_array, bn_prefixes, conv_transpose_prefixes)
            pt_weights.append((name, np_array, role))

        # Classify TF weights
        tf_weights = []
        for w in tf_model.weights:
            role = self._classify_tf_weight_role(w.name, w.shape)
            tf_weights.append((w.name, w, role))

        # Match by role sequence: iterate both lists and match
        # weights that have compatible roles
        assigned = 0
        skipped = 0
        errors = []
        tf_idx = 0

        for pt_name, np_array, pt_role in pt_weights:
            # Find next TF weight with compatible role
            matched = False
            search_start = tf_idx

            for j in range(search_start, len(tf_weights)):
                tf_name, tf_var, tf_role = tf_weights[j]

                if not self._roles_compatible(pt_role, tf_role):
                    continue

                # Apply transpose
                transpose_rule = self._get_transpose_rule(
                    pt_name, np_array, conv_transpose_prefixes)
                converted = np.transpose(np_array, transpose_rule) if transpose_rule else np_array

                # Check shape compatibility
                tf_shape = tuple(tf_var.shape)
                if converted.shape == tf_shape:
                    tf_var.assign(converted)
                    assigned += 1
                    tf_idx = j + 1
                    matched = True
                    self._log(
                        "assigned", pt_name, tf_name=tf_name,
                        pt_shape=np_array.shape, tf_shape=tf_shape,
                        transposed=transpose_rule is not None,
                        method="structural",
                    )
                    break
                elif np.prod(converted.shape) == np.prod(tf_shape):
                    # Same total elements, try reshape
                    converted = converted.reshape(tf_shape)
                    tf_var.assign(converted)
                    assigned += 1
                    tf_idx = j + 1
                    matched = True
                    self._log(
                        "assigned", pt_name, tf_name=tf_name,
                        pt_shape=np_array.shape, tf_shape=tf_shape,
                        transposed=True, method="structural+reshape",
                    )
                    break

            if not matched:
                skipped += 1
                self._log("skip", pt_name, reason=f"no structural match (role={pt_role})")

        stats = {
            "total_pytorch_weights": len(state_dict),
            "assigned": assigned,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors,
            "tf_model_weights": len(tf_weights),
        }

        logger.info(
            "Structural weight mapping: %d/%d assigned, %d skipped",
            assigned, len(state_dict), skipped,
        )
        return stats

    @staticmethod
    def _classify_weight_role(
        name: str, array: np.ndarray,
        bn_prefixes: set[str] | None = None,
        conv_transpose_prefixes: set[str] | None = None,
    ) -> str:
        """Classify a PyTorch weight by its role.

        Args:
            name: PyTorch weight name (e.g. 'layer1.bn1.weight').
            array: Weight tensor as numpy array.
            bn_prefixes: Set of layer prefixes known to be BN layers
                (identified by the presence of running_mean/running_var siblings).
            conv_transpose_prefixes: Set of layer prefixes known to be
                ConvTranspose layers (identified by shape pattern I<O for 4D weights).
        """
        suffix = name.split(".")[-1]
        name_lower = name.lower()

        # Check if this weight belongs to a known BN layer
        parent = name.rsplit(".", 1)[0] if "." in name else ""
        is_bn_layer = False
        if bn_prefixes and parent in bn_prefixes:
            is_bn_layer = True
        elif "bn" in name_lower or "batch_norm" in name_lower or "norm" in name_lower:
            is_bn_layer = True

        # Check if ConvTranspose layer
        is_conv_transpose = False
        if conv_transpose_prefixes and parent in conv_transpose_prefixes:
            is_conv_transpose = True
        elif "transpose" in name_lower or "convtranspose" in name_lower:
            is_conv_transpose = True

        if suffix == "weight":
            if is_bn_layer and array.ndim == 1:
                return "bn_gamma"
            if array.ndim == 4:
                if is_conv_transpose:
                    return "conv_transpose_kernel"
                return "conv_kernel"
            if array.ndim == 2:
                return "dense_kernel"
            if array.ndim == 3:
                return "conv1d_kernel"
            if array.ndim == 1:
                return "bn_gamma"  # fallback for 1D weight
        elif suffix == "bias":
            if is_bn_layer:
                return "bn_beta"
            return "bias"
        elif suffix == "running_mean":
            return "bn_moving_mean"
        elif suffix == "running_var":
            return "bn_moving_var"

        return f"unknown_{array.ndim}d"

    @staticmethod
    def _classify_tf_weight_role(name: str, shape) -> str:
        """Classify a TF weight by its role."""
        name_lower = name.lower()
        ndim = len(shape)

        if "gamma" in name_lower:
            return "bn_gamma"
        elif "beta" in name_lower:
            return "bn_beta"
        elif "moving_mean" in name_lower:
            return "bn_moving_mean"
        elif "moving_variance" in name_lower:
            return "bn_moving_var"
        elif "kernel" in name_lower:
            if ndim == 4:
                if "transpose" in name_lower:
                    return "conv_transpose_kernel"
                return "conv_kernel"
            elif ndim == 3:
                return "conv1d_kernel"
            elif ndim == 2:
                return "dense_kernel"
        elif "bias" in name_lower:
            return "bias"

        return f"unknown_{ndim}d"

    @staticmethod
    def _roles_compatible(pt_role: str, tf_role: str) -> bool:
        """Check if PT and TF weight roles are compatible."""
        return pt_role == tf_role

    # ────────────────────────────────────────
    # Internal: Transpose rules
    # ────────────────────────────────────────

    def _get_transpose_rule(
        self, name: str, array: np.ndarray,
        conv_transpose_prefixes: set[str] | None = None,
    ) -> Optional[tuple]:
        """Determine the transpose rule for a given weight."""
        ndim = array.ndim

        # Check for specific layer types in the name
        name_lower = name.lower()
        parent = name.rsplit(".", 1)[0] if "." in name else ""

        if ndim == 4:
            # ConvTranspose: check explicit name, known prefixes, or shape pattern
            if ("conv_transpose" in name_lower or "convtranspose" in name_lower
                    or (conv_transpose_prefixes and parent in conv_transpose_prefixes)):
                return self.TRANSPOSE_RULES["conv_transpose"]
            # Only classify as depthwise if explicitly named so.
            # Do NOT use shape[1]==1 heuristic — regular convs with 1
            # input channel (e.g. grayscale) have the same pattern.
            if "depthwise" in name_lower:
                return self.TRANSPOSE_RULES["depthwise"]
            if "conv" in name_lower or "weight" in name.split(".")[-1]:
                # Check if it looks like a conv weight (not BN)
                if array.shape[2] <= array.shape[0] and array.shape[3] <= array.shape[0]:
                    return self.TRANSPOSE_RULES["conv2d"]
        elif ndim == 3:
            if "conv" in name_lower:
                return self.TRANSPOSE_RULES["conv1d"]
        elif ndim == 5:
            if "conv" in name_lower:
                return self.TRANSPOSE_RULES["conv3d"]
        elif ndim == 2:
            # Linear / Dense layers
            if "weight" in name.split(".")[-1]:
                # Check it's not an embedding (embeddings shouldn't be transposed)
                if "embed" not in name_lower:
                    return self.TRANSPOSE_RULES["linear"]

        return None

    # ────────────────────────────────────────
    # Internal: Saving
    # ────────────────────────────────────────

    def _save_tf_weights(self, tf_model, output_path: str) -> None:
        """Save TF model weights."""
        path = Path(output_path)
        if path.suffix in (".h5", ".weights.h5"):
            tf_model.save_weights(str(path))
        else:
            # Save as Keras weights file
            path.mkdir(parents=True, exist_ok=True)
            weights_file = path / "weights.weights.h5"
            tf_model.save_weights(str(weights_file))
        logger.info("Saved TF weights to %s", output_path)

    # ────────────────────────────────────────
    # Internal: Logging
    # ────────────────────────────────────────

    def _log(self, action: str, pt_name: str, **kwargs) -> None:
        """Log a conversion action."""
        entry = {"action": action, "pytorch_name": pt_name, **kwargs}
        self._conversion_log.append(entry)
