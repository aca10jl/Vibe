"""一键评测：run_eval(config) -> EvalReport（PLAN 3.1 格式），产物归档到 runs/<exp_id>/。

确定性：同一 config + split 重复评测，报告内容（除 exp_id 外）完全一致。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src import data
from src.algo import load_backend
from src.contracts import EvalReport
from src.eval import metrics as M
from src.eval.matcher import match_case

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS = ROOT / "runs"


def config_hash(config: dict) -> str:
    canon = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                              capture_output=True, check=True).stdout.strip()[:12]
    except Exception:
        return "unknown"


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def new_exp_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"exp_{ts}"


def run_eval(config: dict, split: str, exp_id: str | None = None) -> EvalReport:
    exp_id = exp_id or new_exp_id()
    backend = load_backend(config)
    cases = data.load_cases(split)

    records, fp_ids, fn_ids = [], [], []
    case_details = {}
    for case in cases:
        result = backend.run_case(case, config)
        tp, fp, fn = match_case(case, result.detections)
        records.append({"case": case, "tp": tp, "fp": fp, "fn": fn,
                        "intermediates": result.intermediates})
        for det in fp:
            fp_ids.append(f"fp::{case.case_id}::{det.det_id.split('::')[-1]}")
        for gt in fn:
            fn_ids.append(f"fn::{case.case_id}::{gt.defect_id}")
        case_details[case.case_id] = {
            "intermediates": result.intermediates,
            "detections": [d.model_dump() for d in result.detections],
            "fp": [d.model_dump() for d in fp],
            "fn": [g.model_dump() for g in fn],
        }

    agg = M.aggregate(records)
    report = EvalReport(
        exp_id=exp_id,
        config_hash=config_hash(config),
        git_commit=git_commit(),
        dataset_split=split,
        overall=agg["overall"],
        per_defect_type=agg["per_defect_type"],
        per_layer=agg["per_layer"],
        epe_error=agg["epe_error"],
        failures={"fp_ids": sorted(fp_ids), "fn_ids": sorted(fn_ids)},
    )

    out = RUNS / exp_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval_report.json").write_text(report.model_dump_json(indent=1))
    (out / "case_details.json").write_text(json.dumps(case_details, ensure_ascii=False))
    (out / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=True, allow_unicode=True))
    return report


def load_report(exp_id: str) -> EvalReport:
    return EvalReport.model_validate_json((RUNS / exp_id / "eval_report.json").read_text())
