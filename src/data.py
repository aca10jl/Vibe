"""数据集生成与加载。

make_dataset() 用主种子确定性生成合成 case 清单，分层采样切出 dev / golden，
并在 dev 内标记 20 张 mini 冒烟子集。真实数据接入时：手工编写同 schema 的
manifest.json（每个 case 一条 CaseSpec），splits 文件只存 case_id 列表。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.contracts import CaseSpec, GroundTruthDefect

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "datasets"
MANIFEST = DATASET_DIR / "manifest.json"
SPLITS_DIR = DATASET_DIR / "splits"

MASTER_SEED = 20260610
N_DEV, N_GOLDEN, N_MINI = 120, 60, 20
LAYERS = ("M1", "M2", "V1")


def _u(case_idx: int, tag: str) -> float:
    s = f"{MASTER_SEED}|{case_idx}|{tag}"
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big") / 2**64


def _make_case(i: int) -> CaseSpec:
    n_def = int(_u(i, "nd") * 3.5)  # 0~3 个真实缺陷
    defects = []
    for j in range(n_def):
        defects.append(GroundTruthDefect(
            defect_id=f"gt_{j}",
            type=("bridge", "open", "intrusion")[int(_u(i, f"dt{j}") * 3)],
            x=round(_u(i, f"dx{j}") * 600, 1),
            y=round(_u(i, f"dy{j}") * 600, 1),
            near_corner=_u(i, f"dc{j}") < 0.25,
            near_line_end=_u(i, f"dl{j}") < 0.2,
        ))
    return CaseSpec(
        case_id=f"case_{i:04d}",
        layer=LAYERS[int(_u(i, "ly") * 3)],
        pattern_density=round(0.2 + _u(i, "pd") * 0.7, 3),
        contrast=round(0.2 + _u(i, "ct") * 0.75, 3),
        noise_level=round(_u(i, "nz") * 0.8, 3),
        optimal_sigma=round(1.0 + _u(i, "os") * 0.9, 3),  # 1.0~1.9
        charging=_u(i, "ch") < 0.18,
        cross_die_repeat=_u(i, "xd") < 0.22,
        defects=defects,
        seed=i,
    )


def make_dataset() -> None:
    total = N_DEV + N_GOLDEN
    cases = [_make_case(i) for i in range(total)]
    # 按 layer 分层交替分配，保证 dev/golden 分布一致
    by_layer: dict[str, list[CaseSpec]] = {}
    for c in cases:
        by_layer.setdefault(c.layer, []).append(c)
    dev_ids, golden_ids = [], []
    for layer_cases in by_layer.values():
        for k, c in enumerate(layer_cases):
            (dev_ids if k % 3 != 2 else golden_ids).append(c.case_id)
    dev_ids, golden_ids = sorted(dev_ids)[:N_DEV], sorted(golden_ids)[:N_GOLDEN]
    mini_ids = dev_ids[::max(1, len(dev_ids) // N_MINI)][:N_MINI]

    DATASET_DIR.mkdir(exist_ok=True)
    SPLITS_DIR.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(
        {"master_seed": MASTER_SEED,
         "cases": [c.model_dump() for c in cases]},
        ensure_ascii=False, indent=1))
    (SPLITS_DIR / "dev.json").write_text(json.dumps({"split": "dev", "case_ids": dev_ids}, indent=1))
    (SPLITS_DIR / "mini.json").write_text(json.dumps({"split": "mini", "case_ids": mini_ids}, indent=1))
    (SPLITS_DIR / "golden.json").write_text(json.dumps({"split": "golden", "case_ids": golden_ids}, indent=1))


def load_cases(split: str) -> list[CaseSpec]:
    manifest = json.loads(MANIFEST.read_text())
    split_ids = set(json.loads((SPLITS_DIR / f"{split}.json").read_text())["case_ids"])
    return [CaseSpec(**c) for c in manifest["cases"] if c["case_id"] in split_ids]
