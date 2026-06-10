from src.contracts import CaseSpec, Detection, GroundTruthDefect
from src.eval.matcher import match_case


def _case(defects):
    return CaseSpec(case_id="c", layer="M1", pattern_density=0.5, contrast=0.5,
                    noise_level=0.1, optimal_sigma=1.4, defects=defects)


def _det(det_id, x, y):
    return Detection(det_id=det_id, x=x, y=y, type_guess="bridge", epe_nm=5.0, score=0.8)


def test_match_tp_fp_fn():
    gt = [GroundTruthDefect(defect_id="g0", type="bridge", x=100, y=100),
          GroundTruthDefect(defect_id="g1", type="open", x=300, y=300)]
    dets = [_det("d0", 105, 102),     # 命中 g0
            _det("d1", 500, 500)]     # FP
    tp, fp, fn = match_case(_case(gt), dets)
    assert len(tp) == 1 and tp[0][0].defect_id == "g0"
    assert len(fp) == 1 and fp[0].det_id == "d1"
    assert len(fn) == 1 and fn[0].defect_id == "g1"


def test_one_detection_matches_one_gt():
    gt = [GroundTruthDefect(defect_id="g0", type="bridge", x=100, y=100)]
    dets = [_det("d0", 101, 101), _det("d1", 99, 99)]
    tp, fp, fn = match_case(_case(gt), dets)
    assert len(tp) == 1 and len(fp) == 1 and not fn
