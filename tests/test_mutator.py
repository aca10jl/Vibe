"""L1 白名单硬约束。"""
import pytest

from src.apply.config_mutator import MutationError, apply_proposal
from src.contracts import Proposal


def _p(changes, level="L1"):
    return Proposal(proposal_id="p_t", hypothesis="h", target_bucket="B3_RENDER_GAP",
                    level=level, changes=changes)


def test_valid_change_applied(baseline_config):
    p = _p([{"path": "render.corner_rounding_nm", "from": 0.0, "to": 8.0}])
    new = apply_proposal(baseline_config, p, max_changes=3)
    assert new["render"]["corner_rounding_nm"] == 8.0
    assert baseline_config["render"]["corner_rounding_nm"] == 0.0  # 原 config 不可变


def test_non_whitelisted_path_rejected(baseline_config):
    p = _p([{"path": "algo.backend", "from": "simulated", "to": "real"}])
    with pytest.raises(MutationError, match="白名单"):
        apply_proposal(baseline_config, p, max_changes=3)


def test_out_of_range_rejected(baseline_config):
    p = _p([{"path": "gauge.epe_threshold_nm", "from": 3.0, "to": 99.0}])
    with pytest.raises(MutationError, match="范围"):
        apply_proposal(baseline_config, p, max_changes=3)


def test_too_many_changes_rejected(baseline_config):
    chs = [{"path": "render.corner_rounding_nm", "from": 0.0, "to": 8.0},
           {"path": "render.line_end_shortening_nm", "from": 0.0, "to": 6.0},
           {"path": "gauge.line_end_tolerance_nm", "from": 3.0, "to": 5.0},
           {"path": "gauge.density_adaptive", "from": False, "to": True}]
    with pytest.raises(MutationError, match="上限"):
        apply_proposal(baseline_config, _p(chs), max_changes=3)


def test_wrong_type_rejected(baseline_config):
    p = _p([{"path": "gauge.density_adaptive", "from": False, "to": 1.0}])
    with pytest.raises(MutationError):
        apply_proposal(baseline_config, p, max_changes=3)


def test_l2_rejected_by_mutator(baseline_config):
    p = _p([{"path": "render.corner_rounding_nm", "from": 0.0, "to": 8.0}], level="L2")
    with pytest.raises(MutationError, match="L1"):
        apply_proposal(baseline_config, p, max_changes=3)
