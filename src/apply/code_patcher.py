"""L2 代码改动：只生成 diff + 归因报告，进入人工审批队列，绝不直接执行。

队列形式：runs/approval_queue/<proposal_id>/ 下存 proposal.json + patch.diff +
rationale.md。人工审核后自行 git apply。写入前经 guard 校验，
且 diff 目标若落在禁区路径会被直接拒绝。
"""
from __future__ import annotations

import re
from pathlib import Path

from src.contracts import Proposal
from src.guard.paths import ForbiddenPathError, assert_writable

ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE = ROOT / "runs" / "approval_queue"


def _diff_targets(diff_text: str) -> list[str]:
    return re.findall(r"^\+\+\+ b/(.+)$", diff_text, flags=re.M)


def submit_l2_proposal(proposal: Proposal, rationale_md: str) -> Path:
    if proposal.level != "L2":
        raise ValueError("code_patcher 只处理 L2 提案")
    if not proposal.diff:
        raise ValueError("L2 提案必须携带 diff")
    for target in _diff_targets(proposal.diff):
        assert_writable(ROOT / target)  # diff 不得触碰禁区

    out = QUEUE / proposal.proposal_id
    assert_writable(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "proposal.json").write_text(proposal.model_dump_json(indent=1))
    (out / "patch.diff").write_text(proposal.diff)
    (out / "rationale.md").write_text(rationale_md)
    return out
