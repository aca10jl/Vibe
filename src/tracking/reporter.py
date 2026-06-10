"""每轮 markdown 实验日志：假设 → 改动 → 结果 → 结论。"""
from __future__ import annotations

from pathlib import Path

from src.contracts import EvalReport, GateResult, Proposal

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS = ROOT / "runs"


def _fmt_overall(r: EvalReport) -> str:
    o = r.overall
    return (f"recall={o['recall']:.4f} precision={o['precision']:.4f} "
            f"nuisance={o['nuisance_rate']:.4f} "
            f"FP={len(r.failures['fp_ids'])} FN={len(r.failures['fn_ids'])}")


def write_round_report(iteration: int, proposal: Proposal,
                       baseline: EvalReport, candidate: EvalReport | None,
                       gate: GateResult | None, decision: str) -> Path:
    lines = [
        f"# 第 {iteration} 轮实验日志",
        "",
        f"## 假设（{proposal.target_bucket} / {proposal.level}）",
        proposal.hypothesis,
        "",
        "## 改动",
    ]
    if proposal.changes:
        for ch in proposal.changes:
            lines.append(f"- `{ch.path}`: {ch.from_value} → {ch.to_value}")
    else:
        lines.append("-（L2 提案，无 L1 改动，已进入人工审批队列）")
    lines += ["", "## 结果", f"- 基线（{baseline.exp_id}）: {_fmt_overall(baseline)}"]
    if candidate:
        lines.append(f"- 候选（{candidate.exp_id}）: {_fmt_overall(candidate)}")
    if gate:
        lines.append(f"- 门禁: {'通过' if gate.passed else '未通过 — ' + '; '.join(gate.violations)}")
    lines += ["", "## 结论", decision, ""]

    out_dir = RUNS / (candidate.exp_id if candidate else baseline.exp_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.md"
    path.write_text("\n".join(lines))
    return path
