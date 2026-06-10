"""M0 验收：同一 config 重复评测，指标完全一致（确定性）。"""
from src.eval import harness


def test_eval_deterministic(baseline_config):
    r1 = harness.run_eval(baseline_config, "mini")
    r2 = harness.run_eval(baseline_config, "mini")
    assert r1.overall == r2.overall
    assert r1.per_defect_type == r2.per_defect_type
    assert r1.failures == r2.failures
    assert r1.config_hash == r2.config_hash
    assert r1.exp_id != r2.exp_id  # exp 各自归档


def test_eval_report_contract(baseline_config):
    r = harness.run_eval(baseline_config, "mini")
    assert set(r.overall) == {"recall", "precision", "nuisance_rate"}
    assert 0 <= r.overall["recall"] <= 1
    assert set(r.failures) == {"fp_ids", "fn_ids"}
    # baseline 参数面下必然有失败 case，闭环才有事可做
    assert r.failures["fp_ids"]


def test_config_sensitivity(baseline_config):
    """白名单参数必须真实影响指标（仿真后端对参数有响应）。"""
    import copy

    tuned = copy.deepcopy(baseline_config)
    tuned["render"]["corner_rounding_nm"] = 8.0
    tuned["judge"]["proc_var_filter"] = True
    r_base = harness.run_eval(baseline_config, "mini")
    r_tuned = harness.run_eval(tuned, "mini")
    assert len(r_tuned.failures["fp_ids"]) < len(r_base.failures["fp_ids"])
