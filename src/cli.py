"""D2DB-Tuner 命令行入口。用法见 CLAUDE.md。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def cmd_make_dataset(_args) -> None:
    from src import data

    data.make_dataset()
    print(f"数据集已生成: {data.MANIFEST}")
    for s in ("dev", "mini", "golden"):
        ids = json.loads((data.SPLITS_DIR / f"{s}.json").read_text())["case_ids"]
        print(f"  {s}: {len(ids)} cases")


def _load_config(path: str | None) -> dict:
    if path:
        p = Path(path)
    else:
        cur = ROOT / "configs" / "algo" / "current.yaml"
        p = cur if cur.exists() else ROOT / "configs" / "algo" / "baseline.yaml"
    print(f"使用配置: {p}")
    return yaml.safe_load(p.read_text())


def cmd_eval(args) -> None:
    from src.eval import harness
    from src.tracking import tracker

    config = _load_config(args.config)
    report = harness.run_eval(config, args.split)
    kind = "baseline" if args.baseline else "candidate"
    tracker.record(report.exp_id, kind, args.split, report.config_hash,
                   report.git_commit, report.overall)
    print(report.model_dump_json(indent=1))
    print(f"\n报告已存档: runs/{report.exp_id}/")


def cmd_triage(args) -> None:
    from src.eval import harness
    from src.triage.bucketing import run_bucketing
    from src.triage.evidence import generate_evidence

    report = harness.load_report(args.exp)
    config = yaml.safe_load((ROOT / "runs" / args.exp / "config.yaml").read_text())
    buckets = run_bucketing(report, config)
    buckets = generate_evidence(report, buckets, max_per_bucket=args.max_per_bucket)
    print(json.dumps(buckets.summary, ensure_ascii=False, indent=1))
    print(f"分桶与证据包已写入: runs/{args.exp}/")


def cmd_loop(args) -> None:
    from src.agent.graph import run_session

    state = run_session(split=args.split, iterations=args.iterations,
                        config_path=args.config)
    print(f"\nsession 结束，共 {state.get('iteration', 0)} 轮。")
    for h in state.get("history", []):
        flag = {True: "✔ 合入", False: "✘ 回滚/拒绝", None: "… L2 待审批"}[h["gate_passed"]]
        print(f"  [{h['proposal_id']}] {h['bucket']}: {flag} — {h['decision']}")
    report = state.get("current_report")
    if report:
        print(f"\n最终 dev 指标: {json.dumps(report.overall, ensure_ascii=False)}")


def cmd_golden(args) -> None:
    """golden 仅里程碑跑；结果只打印/入库，绝不回传 Agent（PLAN golden_policy）。"""
    from src.eval import harness
    from src.tracking import tracker

    config = _load_config(args.config)
    report = harness.run_eval(config, "golden")
    tracker.record(report.exp_id, "golden", "golden", report.config_hash,
                   report.git_commit, report.overall)
    print("=== GOLDEN 里程碑回归（结果不回传 Agent）===")
    print(json.dumps(report.overall, ensure_ascii=False, indent=1))


def cmd_history(_args) -> None:
    from src.tracking import tracker

    for h in tracker.history():
        m = h["metrics"] or {}
        print(f"{h['exp_id']}  {h['kind']:9s} {h['status'] or '':12s} "
              f"recall={m.get('recall')} nuisance={m.get('nuisance_rate')}")


def main() -> None:
    p = argparse.ArgumentParser(prog="d2db-tuner")
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("make-dataset", help="生成确定性合成数据集")
    s.set_defaults(fn=cmd_make_dataset)

    s = sub.add_parser("eval", help="一键评测")
    s.add_argument("--split", default="dev", choices=["dev", "mini"])
    s.add_argument("--config", default=None)
    s.add_argument("--baseline", action="store_true", help="作为 baseline 入库")
    s.set_defaults(fn=cmd_eval)

    s = sub.add_parser("triage", help="失败分桶 + 证据包")
    s.add_argument("--exp", required=True)
    s.add_argument("--max-per-bucket", type=int, default=None)
    s.set_defaults(fn=cmd_triage)

    s = sub.add_parser("loop", help="Agent 自主调优闭环")
    s.add_argument("--split", default="dev", choices=["dev", "mini"])
    s.add_argument("--iterations", type=int, default=None)
    s.add_argument("--config", default=None)
    s.set_defaults(fn=cmd_loop)

    s = sub.add_parser("golden", help="golden 集里程碑回归")
    s.add_argument("--config", default=None)
    s.set_defaults(fn=cmd_golden)

    s = sub.add_parser("history", help="实验台账")
    s.set_defaults(fn=cmd_history)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
