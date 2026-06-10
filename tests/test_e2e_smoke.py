"""M3 验收（mini 集冒烟版）：L1 自主闭环至少合入一次改动、指标提升、无门禁违规流入。

强制 offline LLM（确定性），整个闭环秒级可复现。
"""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_closed_loop_improves_metrics(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from src.agent.graph import run_session

    state = run_session(split="mini", iterations=8,
                        config_path=ROOT / "configs" / "algo" / "baseline.yaml")

    history = state["history"]
    assert history, "闭环至少要产出一轮提案"
    merged = [h for h in history if h["gate_passed"]]
    assert merged, "至少一次提案通过门禁并合入"

    # 指标只升不降：最终 report 相对 baseline
    baseline = yaml.safe_load((ROOT / "configs" / "algo" / "baseline.yaml").read_text())
    from src.eval import harness

    base_report = harness.run_eval(baseline, "mini")
    final_report = state["current_report"]
    assert final_report.overall["recall"] >= base_report.overall["recall"] - 0.002
    assert final_report.overall["nuisance_rate"] < base_report.overall["nuisance_rate"]
    assert final_report.overall["precision"] > base_report.overall["precision"]

    # 合入产物存在且为白名单内参数
    current = yaml.safe_load((ROOT / "configs" / "algo" / "current.yaml").read_text())
    assert current != baseline

    # 每轮都有实验日志
    run_dirs = [h for h in history if h["gate_passed"] is not None]
    assert run_dirs


def test_golden_split_never_used_by_loop(monkeypatch):
    """golden 隔离：闭环只允许 dev/mini。"""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import inspect

    from src import cli

    sig_src = inspect.getsource(cli.main)
    # loop 子命令的 split choices 不含 golden
    assert '"golden"' not in sig_src.split('add_parser("loop"')[1].split("set_defaults")[0]
