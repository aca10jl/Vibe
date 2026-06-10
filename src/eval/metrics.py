"""per-type / per-layer Recall-Precision、Nuisance rate、EPE 误差分布。"""
from __future__ import annotations

from src.contracts import DEFECT_TYPES, Metrics


def _rp(tp: int, fp: int, fn: int) -> tuple[float, float]:
    recall = tp / (tp + fn) if tp + fn else 1.0
    precision = tp / (tp + fp) if tp + fp else 1.0
    return round(recall, 4), round(precision, 4)


def aggregate(case_records: list[dict]) -> dict:
    """case_records: 每个 case 一条 {case, tp, fp, fn, intermediates}。"""
    tot_tp = sum(len(r["tp"]) for r in case_records)
    tot_fp = sum(len(r["fp"]) for r in case_records)
    tot_fn = sum(len(r["fn"]) for r in case_records)
    tot_det = tot_tp + tot_fp
    recall, precision = _rp(tot_tp, tot_fp, tot_fn)
    overall = {
        "recall": recall,
        "precision": precision,
        "nuisance_rate": round(tot_fp / tot_det, 4) if tot_det else 0.0,
    }

    per_type: dict[str, Metrics] = {}
    for t in DEFECT_TYPES:
        tp = sum(1 for r in case_records for gt, _ in r["tp"] if gt.type == t)
        fn = sum(1 for r in case_records for gt in r["fn"] if gt.type == t)
        fp = sum(1 for r in case_records for d in r["fp"] if d.type_guess == t)
        rec, prec = _rp(tp, fp, fn)
        per_type[t] = Metrics(recall=rec, precision=prec, count=tp + fn)

    per_layer: dict[str, Metrics] = {}
    layers = sorted({r["case"].layer for r in case_records})
    for ly in layers:
        rs = [r for r in case_records if r["case"].layer == ly]
        tp = sum(len(r["tp"]) for r in rs)
        fp = sum(len(r["fp"]) for r in rs)
        fn = sum(len(r["fn"]) for r in rs)
        rec, prec = _rp(tp, fp, fn)
        per_layer[ly] = Metrics(recall=rec, precision=prec, count=tp + fn)

    # EPE 误差：TP 检出的 |measured - 类型典型值| 分布（代理真实 gauge 误差）
    typical = {"bridge": 6.5, "open": 5.5, "intrusion": 4.5}
    errs = sorted(abs(det.epe_nm - typical[gt.type])
                  for r in case_records for gt, det in r["tp"])
    if errs:
        mean = sum(errs) / len(errs)
        p95 = errs[min(len(errs) - 1, int(len(errs) * 0.95))]
    else:
        mean = p95 = 0.0
    hist = [0] * 6
    for e in errs:
        hist[min(5, int(e))] += 1
    epe_error = {"mean_nm": round(mean, 3), "p95_nm": round(p95, 3), "histogram": hist}

    return {"overall": overall, "per_defect_type": per_type,
            "per_layer": per_layer, "epe_error": epe_error}
