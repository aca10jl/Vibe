"""迭代次数 / 时长预算控制 + 异常熔断。"""
from __future__ import annotations

import time


class Budget:
    def __init__(self, max_iterations: int, max_wall_hours: float):
        self.max_iterations = max_iterations
        self.max_wall_seconds = max_wall_hours * 3600
        self.start = time.monotonic()
        self.iterations = 0
        self.tripped: str | None = None  # 熔断原因

    def tick(self) -> None:
        self.iterations += 1

    def trip(self, reason: str) -> None:
        self.tripped = reason

    def exhausted(self) -> str | None:
        if self.tripped:
            return f"熔断: {self.tripped}"
        if self.iterations >= self.max_iterations:
            return f"达到迭代上限 {self.max_iterations}"
        if time.monotonic() - self.start >= self.max_wall_seconds:
            return "达到时长预算"
        return None
