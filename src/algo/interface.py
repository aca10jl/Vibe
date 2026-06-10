"""被优化算法的适配层接口。

真实 Die2Database 算法接入方式：实现 AlgoBackend 协议（通常是包一层 CLI 或
python 接口调用），在 configs/algo/*.yaml 中设 algo.backend: real，并在
load_backend 中注册。CaseResult.intermediates 需尽量填齐分桶所需信号量。
"""
from __future__ import annotations

from typing import Protocol

from src.contracts import CaseResult, CaseSpec


class AlgoBackend(Protocol):
    def run_case(self, case: CaseSpec, config: dict) -> CaseResult: ...


def load_backend(config: dict) -> AlgoBackend:
    name = config.get("algo", {}).get("backend", "simulated")
    if name == "simulated":
        from .simulated import SimulatedD2DB

        return SimulatedD2DB()
    if name == "real":
        raise NotImplementedError(
            "请实现真实 Die2Database 算法的适配器（参见本文件 docstring 与 CLAUDE.md），"
            "并在此注册。"
        )
    raise ValueError(f"未知 algo.backend: {name}")
