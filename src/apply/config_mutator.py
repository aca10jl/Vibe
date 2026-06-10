"""L1 参数改动：仅允许 search_space.yaml 白名单内的路径与取值范围。

白名单校验是硬约束：路径不在白名单、越界、超过单提案改动数上限，
一律抛 MutationError，提案被拒绝并记录。
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from src.contracts import Proposal
from src.guard.paths import assert_writable

ROOT = Path(__file__).resolve().parent.parent.parent
SEARCH_SPACE = ROOT / "configs" / "search_space.yaml"
CURRENT_CONFIG = ROOT / "configs" / "algo" / "current.yaml"


class MutationError(ValueError):
    pass


def load_search_space() -> dict:
    return yaml.safe_load(SEARCH_SPACE.read_text())["parameters"]


def _get(cfg: dict, dotted: str):
    node = cfg
    for k in dotted.split("."):
        node = node[k]
    return node


def _set(cfg: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    node = cfg
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value


def validate_proposal(proposal: Proposal, max_changes: int) -> None:
    if proposal.level != "L1":
        raise MutationError("config_mutator 只处理 L1 提案")
    if not proposal.changes:
        raise MutationError("提案不含任何改动")
    if len(proposal.changes) > max_changes:
        raise MutationError(f"单提案改动数 {len(proposal.changes)} 超过上限 {max_changes}")
    space = load_search_space()
    for ch in proposal.changes:
        spec = space.get(ch.path)
        if spec is None:
            raise MutationError(f"参数不在白名单: {ch.path}")
        v = ch.to_value
        t = spec["type"]
        if t == "bool":
            if not isinstance(v, bool):
                raise MutationError(f"{ch.path} 需要 bool，得到 {v!r}")
        elif t == "int":
            if not isinstance(v, int) or isinstance(v, bool):
                raise MutationError(f"{ch.path} 需要 int，得到 {v!r}")
        elif t == "float":
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise MutationError(f"{ch.path} 需要 float，得到 {v!r}")
        if "range" in spec:
            lo, hi = spec["range"]
            if not (lo <= v <= hi):
                raise MutationError(f"{ch.path}={v} 超出范围 [{lo}, {hi}]")


def apply_proposal(config: dict, proposal: Proposal, max_changes: int) -> dict:
    """校验并应用提案，返回新 config（不修改原对象）。"""
    validate_proposal(proposal, max_changes)
    new = copy.deepcopy(config)
    for ch in proposal.changes:
        _get(new, ch.path)  # 路径必须已存在
        _set(new, ch.path, ch.to_value)
    return new


def merge_to_current(config: dict) -> Path:
    """门禁通过后，把胜出 config 写为 configs/algo/current.yaml。"""
    path = assert_writable(CURRENT_CONFIG)
    path.write_text(yaml.safe_dump(config, sort_keys=True, allow_unicode=True))
    return path
