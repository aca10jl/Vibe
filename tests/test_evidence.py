from pathlib import Path

from src.eval import harness
from src.triage.bucketing import run_bucketing
from src.triage.evidence import generate_evidence

ROOT = Path(__file__).resolve().parent.parent


def test_evidence_pack_layout(baseline_config):
    report = harness.run_eval(baseline_config, "mini")
    buckets = run_bucketing(report, baseline_config)
    buckets = generate_evidence(report, buckets, max_per_bucket=1)
    with_packs = [a for a in buckets.buckets if a.evidence_pack]
    assert with_packs
    for a in with_packs:
        d = ROOT / a.evidence_pack
        for f in ("sem_raw.png", "overlay.png", "epe_heatmap.png",
                  "intermediates.json", "context.json"):
            assert (d / f).exists(), f"{a.case_id} 缺 {f}"
