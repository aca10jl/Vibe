"""检出框与标注的匹配逻辑（中心距）。"""
from __future__ import annotations

import math

from src.contracts import CaseSpec, Detection

MATCH_DIST_PX = 20.0


def match_case(case: CaseSpec, detections: list[Detection]):
    """返回 (tp_pairs, fp_dets, fn_defects)。贪心最近邻，距离阈值 MATCH_DIST_PX。"""
    unmatched_dets = list(detections)
    tp, fn = [], []
    for gt in case.defects:
        best, best_d = None, MATCH_DIST_PX
        for det in unmatched_dets:
            d = math.hypot(det.x - gt.x, det.y - gt.y)
            if d <= best_d:
                best, best_d = det, d
        if best is not None:
            tp.append((gt, best))
            unmatched_dets.remove(best)
        else:
            fn.append(gt)
    return tp, unmatched_dets, fn
