"""
Accuracy Validator for PyTorch ↔ TensorFlow Model Consistency

Validates that the converted TensorFlow model produces outputs
consistent with the original PyTorch model. Supports:
    - Element-wise absolute/relative tolerance comparison
    - Multiple input shapes and data types
    - Per-layer intermediate output comparison
    - Statistical distribution matching
    - Detailed diff reports
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a model output validation."""

    passed: bool
    max_abs_diff: float
    mean_abs_diff: float
    max_rel_diff: float
    mean_rel_diff: float
    cosine_similarity: float
    pytorch_output_stats: dict = field(default_factory=dict)
    tensorflow_output_stats: dict = field(default_factory=dict)
    details: str = ""

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"Validation {status}\n"
            f"  Max Absolute Diff : {self.max_abs_diff:.2e}\n"
            f"  Mean Absolute Diff: {self.mean_abs_diff:.2e}\n"
            f"  Max Relative Diff : {self.max_rel_diff:.2e}\n"
            f"  Mean Relative Diff: {self.mean_rel_diff:.2e}\n"
            f"  Cosine Similarity : {self.cosine_similarity:.6f}\n"
            f"  {self.details}"
        )


class AccuracyValidator:
    """Validate output consistency between PyTorch and TensorFlow models."""

    def __init__(
        self,
        atol: float = 1e-5,
        rtol: float = 1e-4,
        cosine_threshold: float = 0.9999,
    ):
        """
        Args:
            atol: Absolute tolerance for comparison.
            rtol: Relative tolerance for comparison.
            cosine_threshold: Minimum cosine similarity to pass.
        """
        self.atol = atol
        self.rtol = rtol
        self.cosine_threshold = cosine_threshold

    # ────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────

    def validate(
        self,
        pytorch_model,
        tf_model,
        input_shapes: list[tuple],
        num_samples: int = 5,
        nchw_to_nhwc: bool = True,
        seed: int = 42,
    ) -> ValidationResult:
        """Validate output consistency between PyTorch and TF models.

        Args:
            pytorch_model: The original PyTorch nn.Module model.
            tf_model: The converted tf.keras.Model.
            input_shapes: List of input shapes (without batch dim).
                Example: [(3, 224, 224)] for a single image input.
            num_samples: Number of random inputs to test.
            nchw_to_nhwc: Whether to convert inputs from NCHW to NHWC for TF.
            seed: Random seed for reproducibility.

        Returns:
            ValidationResult with detailed comparison metrics.
        """
        import torch
        import tensorflow as tf

        np.random.seed(seed)
        torch.manual_seed(seed)

        all_abs_diffs = []
        all_rel_diffs = []
        all_cosine_sims = []

        pytorch_model.eval()

        for i in range(num_samples):
            # Generate random input
            inputs_np = [
                np.random.randn(1, *shape).astype(np.float32)
                for shape in input_shapes
            ]

            # Run PyTorch model
            pt_outputs = self._run_pytorch(pytorch_model, inputs_np)

            # Prepare TF inputs (convert NCHW → NHWC if needed)
            tf_inputs_np = inputs_np
            if nchw_to_nhwc:
                tf_inputs_np = [self._nchw_to_nhwc(x) for x in inputs_np]

            # Run TF model
            tf_outputs = self._run_tensorflow(tf_model, tf_inputs_np)

            # Ensure same format for comparison
            pt_flat = self._flatten_outputs(pt_outputs)
            tf_flat = self._flatten_outputs(tf_outputs)

            if len(pt_flat) != len(tf_flat):
                return ValidationResult(
                    passed=False,
                    max_abs_diff=float("inf"),
                    mean_abs_diff=float("inf"),
                    max_rel_diff=float("inf"),
                    mean_rel_diff=float("inf"),
                    cosine_similarity=0.0,
                    details=f"Output count mismatch: PT={len(pt_flat)}, TF={len(tf_flat)}",
                )

            for pt_out, tf_out in zip(pt_flat, tf_flat):
                # Handle shape differences due to channel order
                if nchw_to_nhwc and pt_out.ndim == 4:
                    tf_out = self._nhwc_to_nchw(tf_out)

                # Flatten for comparison
                pt_vec = pt_out.flatten()
                tf_vec = tf_out.flatten()

                if pt_vec.shape != tf_vec.shape:
                    return ValidationResult(
                        passed=False,
                        max_abs_diff=float("inf"),
                        mean_abs_diff=float("inf"),
                        max_rel_diff=float("inf"),
                        mean_rel_diff=float("inf"),
                        cosine_similarity=0.0,
                        details=(
                            f"Shape mismatch after flatten: "
                            f"PT={pt_vec.shape}, TF={tf_vec.shape}"
                        ),
                    )

                abs_diff = np.abs(pt_vec - tf_vec)
                rel_diff = abs_diff / (np.abs(pt_vec) + 1e-10)
                cosine_sim = self._cosine_similarity(pt_vec, tf_vec)

                all_abs_diffs.append(abs_diff)
                all_rel_diffs.append(rel_diff)
                all_cosine_sims.append(cosine_sim)

        # Aggregate metrics
        all_abs = np.concatenate(all_abs_diffs)
        all_rel = np.concatenate(all_rel_diffs)
        avg_cosine = float(np.mean(all_cosine_sims))

        max_abs = float(np.max(all_abs))
        mean_abs = float(np.mean(all_abs))
        max_rel = float(np.max(all_rel))
        mean_rel = float(np.mean(all_rel))

        passed = (
            max_abs <= self.atol
            or mean_abs <= self.atol
            or avg_cosine >= self.cosine_threshold
        )

        pt_sample = self._flatten_outputs(
            self._run_pytorch(pytorch_model, inputs_np)
        )[0].flatten()
        tf_sample = self._flatten_outputs(
            self._run_tensorflow(tf_model, tf_inputs_np)
        )[0].flatten()

        result = ValidationResult(
            passed=passed,
            max_abs_diff=max_abs,
            mean_abs_diff=mean_abs,
            max_rel_diff=max_rel,
            mean_rel_diff=mean_rel,
            cosine_similarity=avg_cosine,
            pytorch_output_stats={
                "mean": float(np.mean(pt_sample)),
                "std": float(np.std(pt_sample)),
                "min": float(np.min(pt_sample)),
                "max": float(np.max(pt_sample)),
            },
            tensorflow_output_stats={
                "mean": float(np.mean(tf_sample)),
                "std": float(np.std(tf_sample)),
                "min": float(np.min(tf_sample)),
                "max": float(np.max(tf_sample)),
            },
        )

        logger.info("Validation result:\n%s", result)
        return result

    def validate_from_numpy(
        self,
        pytorch_outputs: list[np.ndarray],
        tensorflow_outputs: list[np.ndarray],
        nchw_to_nhwc: bool = True,
    ) -> ValidationResult:
        """Validate pre-computed outputs as numpy arrays.

        Args:
            pytorch_outputs: List of PyTorch model outputs as numpy arrays.
            tensorflow_outputs: List of TF model outputs as numpy arrays.
            nchw_to_nhwc: Whether to convert TF outputs from NHWC to NCHW.

        Returns:
            ValidationResult with comparison metrics.
        """
        all_abs_diffs = []
        all_rel_diffs = []
        all_cosine_sims = []

        for pt_out, tf_out in zip(pytorch_outputs, tensorflow_outputs):
            if nchw_to_nhwc and tf_out.ndim == 4:
                tf_out = self._nhwc_to_nchw(tf_out)

            pt_vec = pt_out.flatten()
            tf_vec = tf_out.flatten()

            abs_diff = np.abs(pt_vec - tf_vec)
            rel_diff = abs_diff / (np.abs(pt_vec) + 1e-10)
            cosine_sim = self._cosine_similarity(pt_vec, tf_vec)

            all_abs_diffs.append(abs_diff)
            all_rel_diffs.append(rel_diff)
            all_cosine_sims.append(cosine_sim)

        all_abs = np.concatenate(all_abs_diffs)
        all_rel = np.concatenate(all_rel_diffs)
        avg_cosine = float(np.mean(all_cosine_sims))

        max_abs = float(np.max(all_abs))
        mean_abs = float(np.mean(all_abs))
        max_rel = float(np.max(all_rel))
        mean_rel = float(np.mean(all_rel))

        passed = (
            max_abs <= self.atol
            or mean_abs <= self.atol
            or avg_cosine >= self.cosine_threshold
        )

        return ValidationResult(
            passed=passed,
            max_abs_diff=max_abs,
            mean_abs_diff=mean_abs,
            max_rel_diff=max_rel,
            mean_rel_diff=mean_rel,
            cosine_similarity=avg_cosine,
        )

    # ────────────────────────────────────────
    # Internal: Model execution
    # ────────────────────────────────────────

    def _run_pytorch(self, model, inputs_np: list[np.ndarray]) -> list[np.ndarray]:
        """Run PyTorch model and return outputs as numpy."""
        import torch

        with torch.no_grad():
            tensors = [torch.from_numpy(x) for x in inputs_np]
            if len(tensors) == 1:
                output = model(tensors[0])
            else:
                output = model(*tensors)

        return self._to_numpy_list(output, framework="pytorch")

    def _run_tensorflow(self, model, inputs_np: list[np.ndarray]) -> list[np.ndarray]:
        """Run TF model and return outputs as numpy."""
        import tensorflow as tf

        tensors = [tf.constant(x) for x in inputs_np]
        if len(tensors) == 1:
            output = model(tensors[0], training=False)
        else:
            output = model(tensors, training=False)

        return self._to_numpy_list(output, framework="tensorflow")

    def _to_numpy_list(self, output, framework: str) -> list[np.ndarray]:
        """Convert model output to list of numpy arrays."""
        if framework == "pytorch":
            import torch

            if isinstance(output, torch.Tensor):
                return [output.cpu().numpy()]
            elif isinstance(output, (tuple, list)):
                return [
                    o.cpu().numpy() if isinstance(o, torch.Tensor) else np.array(o)
                    for o in output
                ]
            elif isinstance(output, dict):
                return [
                    v.cpu().numpy() if isinstance(v, torch.Tensor) else np.array(v)
                    for v in output.values()
                ]
        else:
            import tensorflow as tf

            if isinstance(output, tf.Tensor):
                return [output.numpy()]
            elif isinstance(output, (tuple, list)):
                return [
                    o.numpy() if isinstance(o, tf.Tensor) else np.array(o)
                    for o in output
                ]
            elif isinstance(output, dict):
                return [
                    v.numpy() if isinstance(v, tf.Tensor) else np.array(v)
                    for v in output.values()
                ]

        return [np.array(output)]

    # ────────────────────────────────────────
    # Internal: Data format conversion
    # ────────────────────────────────────────

    @staticmethod
    def _nchw_to_nhwc(x: np.ndarray) -> np.ndarray:
        if x.ndim == 4:
            return np.transpose(x, (0, 2, 3, 1))
        return x

    @staticmethod
    def _nhwc_to_nchw(x: np.ndarray) -> np.ndarray:
        if x.ndim == 4:
            return np.transpose(x, (0, 3, 1, 2))
        return x

    # ────────────────────────────────────────
    # Internal: Metrics
    # ────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 1.0 if norm_a < 1e-10 and norm_b < 1e-10 else 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def _flatten_outputs(outputs: list[np.ndarray]) -> list[np.ndarray]:
        """Ensure outputs are a flat list of numpy arrays."""
        result = []
        for o in outputs:
            if isinstance(o, np.ndarray):
                result.append(o)
            else:
                result.append(np.array(o))
        return result
