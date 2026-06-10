"""只读禁区硬性拦截。

所有具备写能力的工具（config_mutator / code_patcher 等）在写入任何文件前
必须调用 assert_writable()。这是工具层强制，不依赖提示词约束。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

FORBIDDEN = (
    "src/eval",
    "src/guard",
    "datasets/splits/golden.json",
    "configs/search_space.yaml",
    "configs/tuner.yaml",
)


class ForbiddenPathError(PermissionError):
    pass


def assert_writable(path: str | Path) -> Path:
    p = Path(path).resolve()
    try:
        rel = p.relative_to(ROOT)
    except ValueError:
        raise ForbiddenPathError(f"禁止写仓库外路径: {p}")
    rel_s = rel.as_posix()
    for f in FORBIDDEN:
        if rel_s == f or rel_s.startswith(f.rstrip("/") + "/"):
            raise ForbiddenPathError(f"只读禁区: {rel_s}（参见 PLAN.md 第 4 节）")
    return p
