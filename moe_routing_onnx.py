import pathlib
from dataclasses import dataclass
from typing import Dict, Tuple

import torch
import torch.nn as nn


class MLPExpert(nn.Module):
    """基础 MLP 专家模型，适合结构化特征场景。"""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ResidualExpert(nn.Module):
    """带残差连接的专家模型，适合中等复杂度场景。"""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int) -> None:
        super().__init__()
        self.proj = nn.Linear(input_dim, output_dim)
        self.block = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.proj(x) + self.block(x)


class DeepExpert(nn.Module):
    """更深层的专家模型，适合高非线性场景。"""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class MoEConfig:
    input_dim: int = 16
    hidden_dim: int = 64
    output_dim: int = 4
    top_k: int = 1
    gate_temperature: float = 1.0


class MoERouter(nn.Module):
    """
    MoE 路由器：
    - top_k=1: 单专家硬路由
    - top_k=2: 双专家软融合路由
    """

    def __init__(self, config: MoEConfig) -> None:
        super().__init__()
        if config.top_k not in (1, 2):
            raise ValueError("top_k 只能是 1 或 2")
        if config.gate_temperature <= 0:
            raise ValueError("gate_temperature 必须 > 0")

        self.config = config
        self.experts = nn.ModuleList(
            [
                MLPExpert(config.input_dim, config.hidden_dim, config.output_dim),
                ResidualExpert(config.input_dim, config.hidden_dim, config.output_dim),
                DeepExpert(config.input_dim, config.hidden_dim, config.output_dim),
            ]
        )
        self.num_experts = len(self.experts)

        self.gate = nn.Sequential(
            nn.Linear(config.input_dim, config.hidden_dim),
            nn.Tanh(),
            nn.Linear(config.hidden_dim, self.num_experts),
        )

    def _all_expert_outputs(self, x: torch.Tensor) -> torch.Tensor:
        """堆叠所有专家输出，形状 [B, E, D]。"""
        outputs = [expert(x) for expert in self.experts]
        return torch.stack(outputs, dim=1)

    def route(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        返回:
        - top_indices: [B, K]
        - top_weights: [B, K]
        - gate_probs: [B, E]
        """
        gate_logits = self.gate(x) / self.config.gate_temperature
        gate_probs = torch.softmax(gate_logits, dim=-1)
        top_weights, top_indices = torch.topk(gate_probs, k=self.config.top_k, dim=-1)

        # top-k 内重新归一化，保证融合权重稳定
        top_weights = top_weights / top_weights.sum(dim=-1, keepdim=True)
        return top_indices, top_weights, gate_probs

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        expert_outputs = self._all_expert_outputs(x)
        top_indices, top_weights, gate_probs = self.route(x)

        gather_index = top_indices.unsqueeze(-1).expand(-1, -1, self.config.output_dim)
        selected_outputs = torch.gather(expert_outputs, dim=1, index=gather_index)

        prediction = (selected_outputs * top_weights.unsqueeze(-1)).sum(dim=1)
        return prediction, top_indices, top_weights, gate_probs

    def load_balance_loss(self, gate_probs: torch.Tensor) -> torch.Tensor:
        """简化版负载均衡损失，避免流量过度集中到单个专家。"""
        expert_density = gate_probs.mean(dim=0)
        uniform = torch.full_like(expert_density, 1.0 / self.num_experts)
        return torch.mean((expert_density - uniform) ** 2)


def export_to_onnx(model: nn.Module, onnx_path: str, input_dim: int) -> None:
    model.eval()
    dummy_input = torch.randn(2, input_dim)
    pathlib.Path(onnx_path).parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=17,
        input_names=["input"],
        output_names=["prediction", "selected_experts", "expert_weights", "gate_probs"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "prediction": {0: "batch_size"},
            "selected_experts": {0: "batch_size"},
            "expert_weights": {0: "batch_size"},
            "gate_probs": {0: "batch_size"},
        },
    )


def one_step_train_example(model: MoERouter, x: torch.Tensor, y: torch.Tensor) -> Dict[str, float]:
    """演示训练逻辑：任务损失 + 负载均衡损失。"""
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    optimizer.zero_grad()

    prediction, _, _, gate_probs = model(x)
    task_loss = nn.functional.mse_loss(prediction, y)
    aux_loss = model.load_balance_loss(gate_probs)
    loss = task_loss + 0.1 * aux_loss

    loss.backward()
    optimizer.step()

    return {
        "task_loss": float(task_loss.detach().cpu()),
        "aux_loss": float(aux_loss.detach().cpu()),
        "total_loss": float(loss.detach().cpu()),
    }


def demo() -> None:
    torch.manual_seed(42)
    input_dim, output_dim = 16, 4
    sample_x = torch.randn(5, input_dim)
    sample_y = torch.randn(5, output_dim)

    for top_k in (1, 2):
        print(f"\n=== Demo: top_k={top_k} ===")
        config = MoEConfig(input_dim=input_dim, output_dim=output_dim, hidden_dim=64, top_k=top_k)
        model = MoERouter(config)

        prediction, expert_idx, expert_w, gate_probs = model(sample_x)
        print("prediction shape:", tuple(prediction.shape))
        print("selected experts:\n", expert_idx)
        print("expert weights:\n", expert_w)
        print("gate probs sum (first sample):", float(gate_probs[0].sum()))

        losses = one_step_train_example(model, sample_x, sample_y)
        print("train losses:", losses)

        onnx_file = f"artifacts/moe_router_top{top_k}.onnx"
        export_to_onnx(model, onnx_file, input_dim)
        print("exported ONNX:", onnx_file)


if __name__ == "__main__":
    demo()
