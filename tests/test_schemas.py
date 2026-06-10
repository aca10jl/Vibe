"""数据契约校验：PLAN 第 3 节 Schema 的固化。"""
import json

from src.contracts import ConfigChange, EvalReport, Metrics, Proposal


def test_config_change_alias_roundtrip():
    ch = ConfigChange(**{"path": "render.corner_rounding_nm", "from": 0, "to": 8})
    assert ch.from_value == 0 and ch.to_value == 8
    dumped = json.loads(ch.model_dump_json(by_alias=True))
    assert dumped["from"] == 0 and dumped["to"] == 8


def test_proposal_schema_matches_plan_3_4():
    p = Proposal(
        proposal_id="p_017",
        hypothesis="B3桶FP集中在M1层线端",
        target_bucket="B3_RENDER_GAP",
        level="L1",
        changes=[{"path": "render.corner_rounding_nm", "from": 0, "to": 8}],
        expected_effect="B3桶FP减少≥50%",
        risk="线端真实缺陷可能漏检",
    )
    d = json.loads(p.model_dump_json(by_alias=True))
    assert d["level"] == "L1" and d["changes"][0]["to"] == 8


def test_eval_report_schema_matches_plan_3_1():
    r = EvalReport(
        exp_id="exp_x", config_hash="a", git_commit="b", dataset_split="dev",
        overall={"recall": 0.9, "precision": 0.87, "nuisance_rate": 0.06},
        per_defect_type={"bridge": Metrics(recall=0.95, precision=0.91, count=412)},
        per_layer={}, epe_error={"mean_nm": 1.8, "p95_nm": 4.2, "histogram": []},
        failures={"fp_ids": [], "fn_ids": []},
    )
    assert r.per_defect_type["bridge"].count == 412
