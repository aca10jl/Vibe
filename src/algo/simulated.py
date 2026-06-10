"""确定性仿真版 Die2Database 算法。

用途：在真实算法/数据接入前，让评测、分桶、Agent 闭环全链路可开发、可测试。
仿真嵌入了五大根因桶对应的失败机制，且对白名单参数有真实响应——
调对参数确实会提升指标，因此可用于验证整个调优闭环的有效性。

确定性保证：所有随机量由 (case_id, 固定盐) 派生，与进程、时间无关；
同一 (case, config) 输入永远得到相同输出。
"""
from __future__ import annotations

import hashlib

from src.contracts import CaseResult, CaseSpec, Detection


def _h(*parts: object) -> float:
    """稳定哈希 -> [0,1) 浮点。"""
    s = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(s.encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


class SimulatedD2DB:
    def run_case(self, case: CaseSpec, config: dict) -> CaseResult:
        al, ct = config["alignment"], config["contour"]
        rd, gg, jd = config["render"], config["gauge"], config["judge"]

        detections: list[Detection] = []
        inter: dict = {}

        # ---- 1. SEM-GDS 对齐（B1 机制）----------------------------------
        needed_iters = 5 + int(_h(case.case_id, "iters") * 18)         # 5~22
        needed_corr = 0.40 + _h(case.case_id, "corr") * 0.35           # 0.40~0.75
        align_ok = (al["max_iterations"] >= needed_iters) and (case.contrast >= 0.25) \
            and (al["min_correlation"] <= needed_corr + 0.15)
        if align_ok:
            inter["registration_residual_px"] = round(0.2 + _h(case.case_id, "res") * 0.6, 3)
            inter["correlation_peak_sharpness"] = round(0.6 + _h(case.case_id, "pk") * 0.35, 3)
        else:
            inter["registration_residual_px"] = round(3.0 + _h(case.case_id, "res") * 4.0, 3)
            inter["correlation_peak_sharpness"] = round(0.05 + _h(case.case_id, "pk") * 0.2, 3)

        # ---- 2. 轮廓提取（B2 机制）--------------------------------------
        sigma_err = abs(ct["gradient_sigma"] - case.optimal_sigma)
        contour_q = max(0.0, 1.0 - sigma_err / 1.5 - case.noise_level * 0.3)
        if case.charging and not ct["charging_compensation"]:
            contour_q = max(0.0, contour_q - 0.45)
        contour_ok = contour_q >= 0.35
        inter["contour_quality"] = round(contour_q, 3)
        inter["contour_break_count"] = 0 if contour_ok else 2 + int(_h(case.case_id, "brk") * 5)
        inter["edge_snr"] = round(1.0 + contour_q * 4.0, 3)
        inter["charging_detected"] = case.charging

        # ---- 3. GDS 渲染缺口（B3 机制信号）-------------------------------
        corner_bias = max(0.0, (8.0 - rd["corner_rounding_nm"])) * 0.35
        lineend_bias = max(0.0, (6.0 - rd["line_end_shortening_nm"])) * 0.30
        inter["epe_bias_corner_nm"] = round(corner_bias, 3)
        inter["epe_bias_lineend_nm"] = round(lineend_bias, 3)

        thr = gg["epe_threshold_nm"]
        # 密度自适应：高密度图整体 EPE 抬升，开启后阈值随密度补偿
        density_shift = (case.pattern_density - 0.5) * 1.6
        eff_thr = thr + (density_shift if gg["density_adaptive"] else 0.0)

        # ---- 4. 真实缺陷检出 / 漏检（FN 路径）----------------------------
        for d in case.defects:
            if not align_ok:
                continue  # 对齐失败 -> 全部漏检（B1 型 FN）
            if not contour_ok and d.type == "open":
                continue  # 轮廓断裂 -> open 漏检（B2 型 FN）
            true_epe = {"bridge": 6.5, "open": 5.5, "intrusion": 4.5}[d.type]
            measured = true_epe + (_h(case.case_id, d.defect_id, "n") - 0.5) * 1.2 + density_shift
            score = 0.55 + _h(case.case_id, d.defect_id, "s") * 0.4
            site_thr = eff_thr
            if d.near_line_end:
                site_thr = max(site_thr, gg["line_end_tolerance_nm"])
            if measured >= site_thr and score >= jd["min_defect_score"]:
                detections.append(Detection(
                    det_id=f"det::{case.case_id}::{d.defect_id}",
                    x=d.x, y=d.y, type_guess=d.type,
                    epe_nm=round(measured, 3), score=round(score, 3),
                    near_corner=d.near_corner, near_line_end=d.near_line_end,
                    signals={"margin_nm": round(measured - site_thr, 3)},
                ))
            # 漏检即不产生检出，matcher 标 FN；阈值边缘信息留在 intermediates
            inter.setdefault("fn_margins", {})[d.defect_id] = round(measured - site_thr, 3)

        # ---- 5. 误检源（FP 路径）----------------------------------------
        def _fp(site: str, x: float, y: float, epe: float, score: float,
                near_corner=False, near_line_end=False, mechanism="", extra=None):
            detections.append(Detection(
                det_id=f"fp::{case.case_id}::{site}",
                x=x, y=y,
                type_guess="intrusion",
                epe_nm=round(epe, 3), score=round(score, 3),
                near_corner=near_corner, near_line_end=near_line_end,
                signals={"_mechanism": mechanism, "margin_nm": round(epe - eff_thr, 3),
                         **(extra or {})},
            ))

        if align_ok:
            # B3：corner / line-end 渲染缺口导致的系统性 FP
            n_corner_sites = 1 + int(_h(case.case_id, "ncs") * 3)
            for i in range(n_corner_sites):
                base = 1.2 + _h(case.case_id, "c", i) * 1.6
                epe = base + corner_bias + density_shift
                if epe >= eff_thr:
                    _fp(f"corner_{i}", 100 + i * 37, 80 + i * 23, epe,
                        0.5 + _h(case.case_id, "cs", i) * 0.3,
                        near_corner=True, mechanism="render_gap",
                        extra={"epe_bias_nm": round(corner_bias, 3)})
            n_le_sites = int(_h(case.case_id, "nls") * 3)
            for i in range(n_le_sites):
                epe = 1.0 + _h(case.case_id, "l", i) * 1.5 + lineend_bias + density_shift
                site_thr = max(eff_thr, gg["line_end_tolerance_nm"])
                if epe >= site_thr:
                    _fp(f"lineend_{i}", 300 + i * 41, 200 + i * 19, epe,
                        0.5 + _h(case.case_id, "ls", i) * 0.3,
                        near_line_end=True, mechanism="render_gap",
                        extra={"epe_bias_nm": round(lineend_bias, 3)})

            # B4：贴阈值边界的 nuisance（密度相关，density_adaptive 可消解）
            n_marg = 1 + int(_h(case.case_id, "nm") * 3)
            for i in range(n_marg):
                epe = thr + (_h(case.case_id, "m", i) - 0.35) * 0.8 + density_shift
                if epe >= eff_thr:
                    _fp(f"marginal_{i}", 420 + i * 29, 350 + i * 31, epe,
                        0.5 + _h(case.case_id, "ms", i) * 0.25,
                        mechanism="threshold",
                        extra={"density": case.pattern_density})

            # B5：跨 die 重复的工艺变异误判
            if case.cross_die_repeat and not jd["proc_var_filter"]:
                _fp("procvar_0", 510, 440, eff_thr + 1.0 + _h(case.case_id, "pv") * 0.8,
                    0.6 + _h(case.case_id, "pvs") * 0.2,
                    mechanism="proc_var",
                    extra={"cross_die_repeat_count": 3 + int(_h(case.case_id, "pvc") * 3),
                           "cd_drift_nm": round(0.8 + _h(case.case_id, "cd") * 0.6, 3)})

            # B2：轮廓断裂产生的碎片 FP
            if not contour_ok:
                _fp("contour_0", 220, 300, eff_thr + 0.8 + _h(case.case_id, "cf") * 1.0,
                    0.55 + _h(case.case_id, "cfs") * 0.2,
                    mechanism="contour",
                    extra={"contour_break_count": inter["contour_break_count"]})
        else:
            # B1：对齐失败产生的大面积假 EPE
            _fp("align_0", 50, 60, eff_thr + 2.5 + _h(case.case_id, "af") * 2.0,
                0.7 + _h(case.case_id, "afs") * 0.2, mechanism="align")

        # score 门限过滤
        detections = [d for d in detections if d.score >= jd["min_defect_score"]]
        return CaseResult(case_id=case.case_id, detections=detections, intermediates=inter)
