import pytest

from src.apply.code_patcher import submit_l2_proposal
from src.contracts import Proposal
from src.guard import ForbiddenPathError


def _l2(diff):
    return Proposal(proposal_id="p_l2_test", hypothesis="渲染模块缺 corner rounding 建模",
                    target_bucket="B3_RENDER_GAP", level="L2", changes=[], diff=diff)


def test_l2_goes_to_approval_queue():
    diff = ("--- a/src/algo/simulated.py\n+++ b/src/algo/simulated.py\n"
            "@@ -1 +1 @@\n-x\n+y\n")
    out = submit_l2_proposal(_l2(diff), "rationale")
    assert (out / "patch.diff").exists() and (out / "rationale.md").exists()


def test_l2_diff_touching_forbidden_path_rejected():
    diff = ("--- a/src/eval/harness.py\n+++ b/src/eval/harness.py\n"
            "@@ -1 +1 @@\n-x\n+y\n")
    with pytest.raises(ForbiddenPathError):
        submit_l2_proposal(_l2(diff), "rationale")
