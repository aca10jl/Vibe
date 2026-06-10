"""回归门禁：候选实验 vs 基线实验的硬条件判定（规则来自 configs/tuner.yaml）。"""
from __future__ import annotations

from src.contracts import EvalReport, GateResult


def evaluate_gate(candidate: EvalReport, baseline: EvalReport, rules: dict) -> GateResult:
    v: list[str] = []

    drop = baseline.overall["recall"] - candidate.overall["recall"]
    if drop > rules["overall_recall_drop_max"] + 1e-9:
        v.append(f"overall.recall 下降 {drop:.4f} > {rules['overall_recall_drop_max']}")

    for t, base_m in baseline.per_defect_type.items():
        cand_m = candidate.per_defect_type.get(t)
        if cand_m is None:
            continue
        d = base_m.recall - cand_m.recall
        if d > rules["per_type_recall_drop_max"] + 1e-9:
            v.append(f"per_type.{t}.recall 下降 {d:.4f} > {rules['per_type_recall_drop_max']}")

    rise = candidate.overall["nuisance_rate"] - baseline.overall["nuisance_rate"]
    if rise > rules["nuisance_rate_rise_max"] + 1e-9:
        v.append(f"nuisance_rate 上升 {rise:.4f} > {rules['nuisance_rate_rise_max']}")

    base_p95 = baseline.epe_error["p95_nm"]
    if base_p95 > 0 and candidate.epe_error["p95_nm"] > base_p95 * rules["epe_p95_ratio_max"] + 1e-9:
        v.append(f"epe p95 {candidate.epe_error['p95_nm']} > 基线 {base_p95} x {rules['epe_p95_ratio_max']}")

    return GateResult(passed=not v, violations=v,
                      candidate_exp=candidate.exp_id, baseline_exp=baseline.exp_id)
