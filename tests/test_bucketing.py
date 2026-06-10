"""M1 验收：规则初判桶准确率 ≥ 70%（对照仿真机制标签），UNKNOWN 占比 < 15%。"""
import json
from pathlib import Path

from src.eval import harness
from src.triage.bucketing import run_bucketing

ROOT = Path(__file__).resolve().parent.parent

MECH_TO_BUCKET = {"render_gap": "B3_RENDER_GAP", "threshold": "B4_THRESHOLD",
                  "proc_var": "B5_PROC_VAR", "contour": "B2_CONTOUR", "align": "B1_ALIGN"}


def test_bucketing_accuracy_and_unknown_rate(baseline_config):
    report = harness.run_eval(baseline_config, "dev")
    buckets = run_bucketing(report, baseline_config)
    assert buckets.buckets, "baseline 下必须有失败 case"

    details = json.loads((ROOT / "runs" / report.exp_id / "case_details.json").read_text())
    total = len(buckets.buckets)
    unknown = sum(1 for a in buckets.buckets if a.bucket == "UNKNOWN")
    assert unknown / total < 0.15, f"UNKNOWN 占比 {unknown}/{total}"

    # FP 类失败有机制标签，可对照评估准确率
    checked = correct = 0
    for a in buckets.buckets:
        kind, case_id, site = a.case_id.split("::")
        if kind != "fp":
            continue
        det = next((x for x in details[case_id]["fp"]
                    if x["det_id"].endswith(f"::{site}")), None)
        mech = (det or {}).get("signals", {}).get("_mechanism")
        if not mech:
            continue
        checked += 1
        if a.bucket == MECH_TO_BUCKET[mech]:
            correct += 1
    assert checked > 10
    assert correct / checked >= 0.70, f"分桶准确率 {correct}/{checked}"


def test_buckets_file_schema(baseline_config):
    report = harness.run_eval(baseline_config, "mini")
    bf = run_bucketing(report, baseline_config)
    assert bf.exp_id == report.exp_id
    assert sum(bf.summary.values()) == len(bf.buckets)
