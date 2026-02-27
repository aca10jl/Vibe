import argparse
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import onnxruntime as ort
import torch

from moe_routing_onnx import MoEConfig, MoERouter


def parse_batches(text: str) -> List[int]:
    values = [int(x.strip()) for x in text.split(",") if x.strip()]
    if not values:
        raise ValueError("batches must not be empty")
    if any(v <= 0 for v in values):
        raise ValueError("batch sizes must be positive integers")
    return values


def build_reference_models_for_artifacts() -> Dict[int, MoERouter]:
    """
    Rebuilds PyTorch models with the same RNG consumption order used in demo():
    seed -> sample_x/sample_y -> top1 model -> dummy_input(top1 export) -> top2 model.
    """
    torch.manual_seed(42)
    sample_x = torch.randn(5, 16)
    _ = torch.randn(5, 4)  # sample_y in demo()

    model_top1 = MoERouter(MoEConfig(input_dim=16, hidden_dim=64, output_dim=4, top_k=1)).eval()
    with torch.no_grad():
        _ = model_top1(sample_x)

    _ = torch.randn(2, 16)  # dummy_input in export_to_onnx() for top_k=1
    model_top2 = MoERouter(MoEConfig(input_dim=16, hidden_dim=64, output_dim=4, top_k=2)).eval()

    return {1: model_top1, 2: model_top2}


def max_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(a - b)))


def validate_model(
    top_k: int,
    model: MoERouter,
    onnx_path: Path,
    batches: Iterable[int],
    provider: str,
    atol: float,
) -> None:
    session = ort.InferenceSession(str(onnx_path), providers=[provider])
    input_name = session.get_inputs()[0].name

    max_pred_diff = 0.0
    max_weight_diff = 0.0
    max_gate_diff = 0.0
    all_idx_equal = True

    print(f"\n[Validate top_k={top_k}] {onnx_path}")
    for batch_size in batches:
        generator = torch.Generator().manual_seed(5000 + top_k * 100 + batch_size)
        x = torch.randn(batch_size, 16, generator=generator, dtype=torch.float32)

        with torch.no_grad():
            pt_prediction, pt_selected, pt_weights, pt_gate = model(x)
        ort_prediction, ort_selected, ort_weights, ort_gate = session.run(
            None, {input_name: x.numpy()}
        )

        pred_diff = max_abs_diff(pt_prediction.numpy(), ort_prediction)
        weight_diff = max_abs_diff(pt_weights.numpy(), ort_weights)
        gate_diff = max_abs_diff(pt_gate.numpy(), ort_gate)
        selected_equal = bool(np.array_equal(pt_selected.numpy(), ort_selected))

        max_pred_diff = max(max_pred_diff, pred_diff)
        max_weight_diff = max(max_weight_diff, weight_diff)
        max_gate_diff = max(max_gate_diff, gate_diff)
        all_idx_equal = all_idx_equal and selected_equal

        print(
            f"batch={batch_size:2d} | pred_diff={pred_diff:.8f} | "
            f"weights_diff={weight_diff:.8f} | gate_diff={gate_diff:.8f} | "
            f"selected_equal={selected_equal}"
        )

    print(
        f"summary top_k={top_k}: pred={max_pred_diff:.8f}, "
        f"weights={max_weight_diff:.8f}, gate={max_gate_diff:.8f}, "
        f"selected_equal_all={all_idx_equal}"
    )

    if not all_idx_equal:
        raise RuntimeError(f"selected_experts mismatch for top_k={top_k}")
    if max_pred_diff > atol or max_weight_diff > atol or max_gate_diff > atol:
        raise RuntimeError(
            f"numeric diff exceeds atol={atol} for top_k={top_k}: "
            f"pred={max_pred_diff}, weights={max_weight_diff}, gate={max_gate_diff}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate ONNX Runtime outputs against PyTorch reference for MoE router models."
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory containing moe_router_top1.onnx and moe_router_top2.onnx",
    )
    parser.add_argument(
        "--batches",
        type=str,
        default="1,3,8,17",
        help="Comma-separated batch sizes to validate, e.g. 1,3,8,17",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="CPUExecutionProvider",
        help="ONNX Runtime execution provider",
    )
    parser.add_argument(
        "--atol",
        type=float,
        default=1e-5,
        help="Absolute error threshold for floating-point outputs",
    )
    args = parser.parse_args()

    batches = parse_batches(args.batches)
    artifacts_dir = args.artifacts_dir
    onnx_paths = {
        1: artifacts_dir / "moe_router_top1.onnx",
        2: artifacts_dir / "moe_router_top2.onnx",
    }
    missing = [str(path) for path in onnx_paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing ONNX artifacts: {missing}")

    models = build_reference_models_for_artifacts()
    for top_k in (1, 2):
        validate_model(top_k, models[top_k], onnx_paths[top_k], batches, args.provider, args.atol)

    print("\nONNX Runtime validation PASSED")


if __name__ == "__main__":
    main()
