"""失败自动分桶：FP/FN -> 五大根因桶（规则引擎初判，PLAN 3.2）。

只依赖算法暴露的客观信号量（配准残差、轮廓断裂数、EPE 边际、跨 die 重复等），
不读取仿真内部的机制标签——机制标签仅用于单测里验证分桶准确率。
"""
from __future__ import annotations

import json
from pathlib import Path

from src.contracts import BucketAssignment, BucketsFile, EvalReport

RUNS = Path(__file__).resolve().parent.parent.parent / "runs"


def _classify(inter: dict, det: dict | None, fn_margin: float | None,
              epe_threshold: float) -> tuple[str, float, dict]:
    """返回 (bucket, confidence, signals)。规则按特异性从高到低排列。"""
    signals: dict = {}

    # B1：配准残差大 / 相关峰锐度低
    res = inter.get("registration_residual_px")
    pk = inter.get("correlation_peak_sharpness")
    if res is not None and res > 2.0 or pk is not None and pk < 0.3:
        signals.update({"registration_residual_px": res, "peak_sharpness": pk})
        return "B1_ALIGN", 0.9, signals

    # B5：同位置跨 die 重复
    if det and det.get("signals", {}).get("cross_die_repeat_count"):
        signals.update({k: det["signals"][k] for k in ("cross_die_repeat_count", "cd_drift_nm")
                        if k in det["signals"]})
        return "B5_PROC_VAR", 0.85, signals

    # B2：轮廓断裂 / 边缘 SNR 低 / charging 未补偿
    brk = inter.get("contour_break_count") or 0
    snr = inter.get("edge_snr")
    if brk > 0 or (snr is not None and snr < 2.0):
        signals.update({"contour_break_count": brk, "edge_snr": snr,
                        "charging_detected": inter.get("charging_detected")})
        return "B2_CONTOUR", 0.8, signals

    # B3：FP 集中于 corner / 线端，且存在系统性 EPE 偏置
    if det and (det.get("near_corner") or det.get("near_line_end")):
        bias = (inter.get("epe_bias_corner_nm") if det.get("near_corner")
                else inter.get("epe_bias_lineend_nm")) or 0.0
        if bias > 0.8:
            signals.update({"near_corner": det.get("near_corner"),
                            "near_line_end": det.get("near_line_end"),
                            "epe_bias_nm": bias})
            return "B3_RENDER_GAP", 0.85, signals

    # B4：EPE 贴阈值边界（FP 的正边际小 / FN 的负边际小）
    margin = None
    if det is not None:
        margin = det.get("signals", {}).get("margin_nm")
    elif fn_margin is not None:
        margin = fn_margin
    if margin is not None and abs(margin) < 1.2:
        signals.update({"margin_nm": margin, "epe_threshold_nm": epe_threshold})
        return "B4_THRESHOLD", 0.75, signals

    return "UNKNOWN", 0.3, signals


def run_bucketing(report: EvalReport, config: dict) -> BucketsFile:
    details = json.loads((RUNS / report.exp_id / "case_details.json").read_text())
    thr = config["gauge"]["epe_threshold_nm"]
    assignments: list[BucketAssignment] = []

    for fid in report.failures["fp_ids"]:
        _, case_id, site = fid.split("::")
        d = details[case_id]
        det = next((x for x in d["fp"] if x["det_id"].endswith(f"::{site}")), None)
        bucket, conf, sig = _classify(d["intermediates"], det, None, thr)
        assignments.append(BucketAssignment(case_id=fid, bucket=bucket, confidence=conf, signals=sig))

    for fid in report.failures["fn_ids"]:
        _, case_id, defect_id = fid.split("::")
        d = details[case_id]
        fn_margin = (d["intermediates"].get("fn_margins") or {}).get(defect_id)
        bucket, conf, sig = _classify(d["intermediates"], None, fn_margin, thr)
        assignments.append(BucketAssignment(case_id=fid, bucket=bucket, confidence=conf, signals=sig))

    summary: dict[str, int] = {}
    for a in assignments:
        summary[a.bucket] = summary.get(a.bucket, 0) + 1

    bf = BucketsFile(exp_id=report.exp_id, buckets=assignments, summary=summary)
    (RUNS / report.exp_id / "buckets.json").write_text(bf.model_dump_json(indent=1))
    return bf
