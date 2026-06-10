"""证据包生成器（PLAN 3.3）：每个失败 case 一个目录。

sem_raw.png / overlay.png / epe_heatmap.png 由 case 元数据确定性渲染
（真实数据接入后替换为真实 SEM 图与对齐叠加图），intermediates.json /
context.json 为分桶与 LLM 诊断所需的全部结构化信息。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from src.contracts import BucketsFile, CaseSpec, EvalReport
from src import data

RUNS = Path(__file__).resolve().parent.parent.parent / "runs"
SIZE = 256


def _rng01(*parts) -> float:
    s = "|".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big") / 2**64


def _render_sem(case: CaseSpec) -> Image.Image:
    img = Image.new("L", (SIZE, SIZE), int(40 + case.contrast * 60))
    d = ImageDraw.Draw(img)
    n_lines = 4 + int(case.pattern_density * 8)
    pitch = SIZE // n_lines
    for i in range(n_lines):
        x = i * pitch + int(_rng01(case.case_id, "jit", i) * 3)
        d.rectangle([x, 10, x + pitch // 2, SIZE - 10], fill=int(120 + case.contrast * 100))
    if case.charging:
        d.ellipse([SIZE - 90, 20, SIZE - 20, 90], fill=230)
    return img.convert("RGB")


def _render_overlay(case: CaseSpec, fail_xy: tuple[float, float] | None) -> Image.Image:
    img = _render_sem(case)
    d = ImageDraw.Draw(img)
    n_lines = 4 + int(case.pattern_density * 8)
    pitch = SIZE // n_lines
    for i in range(n_lines):  # GDS 轮廓（绿）
        x = i * pitch
        d.rectangle([x, 10, x + pitch // 2, SIZE - 10], outline=(0, 220, 0))
    if fail_xy:
        x, y = fail_xy[0] % SIZE, fail_xy[1] % SIZE
        d.rectangle([x - 12, y - 12, x + 12, y + 12], outline=(255, 40, 40), width=2)
    return img


def _render_heatmap(case: CaseSpec, inter: dict) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), (10, 10, 60))
    d = ImageDraw.Draw(img)
    bias = (inter.get("epe_bias_corner_nm") or 0) + (inter.get("epe_bias_lineend_nm") or 0)
    heat = min(255, int(60 + bias * 30 + case.pattern_density * 60))
    for i in range(0, SIZE, 16):
        for j in range(0, SIZE, 16):
            v = int(heat * _rng01(case.case_id, "hm", i, j))
            d.rectangle([i, j, i + 15, j + 15], fill=(v, max(0, v - 80), 60))
    return img


def generate_evidence(report: EvalReport, buckets: BucketsFile,
                      max_per_bucket: int | None = None) -> BucketsFile:
    """为失败 case 生成证据包目录，并把路径回填到 buckets.json。"""
    details = json.loads((RUNS / report.exp_id / "case_details.json").read_text())
    cases = {c.case_id: c for c in data.load_cases(report.dataset_split)}
    ev_root = RUNS / report.exp_id / "evidence"

    taken: dict[str, int] = {}
    for a in buckets.buckets:
        if max_per_bucket is not None:
            if taken.get(a.bucket, 0) >= max_per_bucket:
                continue
            taken[a.bucket] = taken.get(a.bucket, 0) + 1

        kind, case_id, site = a.case_id.split("::")
        case = cases[case_id]
        d = details[case_id]
        out = ev_root / a.case_id.replace("::", "_")
        out.mkdir(parents=True, exist_ok=True)

        fail_xy = None
        if kind == "fp":
            det = next((x for x in d["fp"] if x["det_id"].endswith(f"::{site}")), None)
            if det:
                fail_xy = (det["x"], det["y"])
        else:
            gt = next((g for g in d["fn"] if g["defect_id"] == site), None)
            if gt:
                fail_xy = (gt["x"], gt["y"])

        _render_sem(case).save(out / "sem_raw.png")
        _render_overlay(case, fail_xy).save(out / "overlay.png")
        _render_heatmap(case, d["intermediates"]).save(out / "epe_heatmap.png")
        (out / "intermediates.json").write_text(json.dumps(d["intermediates"], ensure_ascii=False, indent=1))
        (out / "context.json").write_text(json.dumps({
            "failure_id": a.case_id,
            "failure_kind": kind,
            "layer": case.layer,
            "pattern_density": case.pattern_density,
            "charging": case.charging,
            "cross_die_repeat": case.cross_die_repeat,
            "rule_bucket": a.bucket,
            "rule_confidence": a.confidence,
            "signals": a.signals,
            "ground_truth_defects": [g.model_dump() for g in case.defects],
        }, ensure_ascii=False, indent=1))
        a.evidence_pack = str(out.relative_to(RUNS.parent))

    (RUNS / report.exp_id / "buckets.json").write_text(buckets.model_dump_json(indent=1))
    return buckets
