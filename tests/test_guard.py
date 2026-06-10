"""禁区硬拦截 + 回归门禁判定。"""
import pytest

from src.contracts import EvalReport, Metrics
from src.guard import ForbiddenPathError, assert_writable, evaluate_gate
from src.guard.paths import ROOT


@pytest.mark.parametrize("p", [
    "src/eval/harness.py",
    "src/guard/regression_gate.py",
    "datasets/splits/golden.json",
    "configs/search_space.yaml",
    "configs/tuner.yaml",
])
def test_forbidden_paths_blocked(p):
    with pytest.raises(ForbiddenPathError):
        assert_writable(ROOT / p)


def test_outside_repo_blocked():
    with pytest.raises(ForbiddenPathError):
        assert_writable("/tmp/evil.yaml")


def test_writable_paths_ok():
    assert_writable(ROOT / "configs/algo/current.yaml")
    assert_writable(ROOT / "runs/exp_x/report.md")


def _report(recall, precision, nuisance, p95=2.0, bridge_recall=0.9):
    return EvalReport(
        exp_id="e", config_hash="h", git_commit="g", dataset_split="dev",
        overall={"recall": recall, "precision": precision, "nuisance_rate": nuisance},
        per_defect_type={"bridge": Metrics(recall=bridge_recall, precision=0.9, count=10)},
        per_layer={}, epe_error={"mean_nm": 1.0, "p95_nm": p95, "histogram": []},
        failures={"fp_ids": [], "fn_ids": []})


RULES = {"overall_recall_drop_max": 0.002, "per_type_recall_drop_max": 0.005,
         "nuisance_rate_rise_max": 0.005, "epe_p95_ratio_max": 1.10}


def test_gate_pass_on_improvement():
    g = evaluate_gate(_report(0.92, 0.9, 0.05), _report(0.90, 0.88, 0.08), RULES)
    assert g.passed


def test_gate_fail_on_recall_drop():
    g = evaluate_gate(_report(0.88, 0.95, 0.02), _report(0.90, 0.88, 0.08), RULES)
    assert not g.passed and any("overall.recall" in v for v in g.violations)


def test_gate_fail_on_per_type_recall_drop():
    g = evaluate_gate(_report(0.90, 0.9, 0.05, bridge_recall=0.80),
                      _report(0.90, 0.88, 0.05, bridge_recall=0.90), RULES)
    assert not g.passed and any("per_type.bridge" in v for v in g.violations)


def test_gate_fail_on_nuisance_rise():
    g = evaluate_gate(_report(0.91, 0.9, 0.10), _report(0.90, 0.9, 0.05), RULES)
    assert not g.passed
