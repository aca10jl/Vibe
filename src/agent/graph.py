"""LangGraph 状态机：EVAL → BUCKET → DIAGNOSE → PROPOSE → (APPLY → REGRESSION
→ 合入|回滚 | L2 审批队列) → REPORT → 预算未尽则回到 EVAL。"""
from __future__ import annotations

import time
from pathlib import Path

import yaml
from langgraph.graph import END, StateGraph

from src.agent import nodes
from src.agent.nodes import TunerState

ROOT = Path(__file__).resolve().parent.parent.parent


def build_graph():
    g = StateGraph(TunerState)
    g.add_node("EVAL", nodes.node_eval)
    g.add_node("BUCKET", nodes.node_bucket)
    g.add_node("DIAGNOSE", nodes.node_diagnose)
    g.add_node("PROPOSE", nodes.node_propose)
    g.add_node("APPLY", nodes.node_apply)
    g.add_node("REGRESSION", nodes.node_regression)
    g.add_node("MERGE_OR_ROLLBACK", nodes.node_merge_or_rollback)
    g.add_node("L2_QUEUE", nodes.node_l2_queue)
    g.add_node("REPORT", nodes.node_report)

    g.set_entry_point("EVAL")
    g.add_edge("EVAL", "BUCKET")
    g.add_conditional_edges("BUCKET", nodes.route_after_bucket,
                            {"diagnose": "DIAGNOSE",
                             "no_failures": END,
                             "no_actionable": END})
    g.add_edge("DIAGNOSE", "PROPOSE")
    g.add_conditional_edges("PROPOSE", nodes.route_level,
                            {"L1": "APPLY", "L2": "L2_QUEUE"})
    g.add_conditional_edges("APPLY", nodes.route_after_apply,
                            {"regression": "REGRESSION", "rejected": "REPORT"})
    g.add_edge("REGRESSION", "MERGE_OR_ROLLBACK")
    g.add_edge("MERGE_OR_ROLLBACK", "REPORT")
    g.add_edge("L2_QUEUE", "REPORT")
    g.add_conditional_edges("REPORT", nodes.route_continue,
                            {"continue": "EVAL", "end": END})
    return g.compile()


def run_session(split: str = "dev", iterations: int | None = None,
                config_path: str | Path | None = None) -> TunerState:
    """跑一个调优 session，返回最终 state。"""
    tuner_cfg = yaml.safe_load((ROOT / "configs" / "tuner.yaml").read_text())
    if iterations is not None:
        tuner_cfg["budget"]["max_iterations_per_session"] = iterations
    cfg_path = Path(config_path) if config_path else _pick_config()
    config = yaml.safe_load(cfg_path.read_text())

    app = build_graph()
    init: TunerState = {
        "split": split, "tuner_cfg": tuner_cfg, "config": config,
        "iteration": 0, "start_time": time.monotonic(),
        "history": [], "cooldown_fails": {},
    }
    return app.invoke(init, config={"recursion_limit": 1000})


def _pick_config() -> Path:
    current = ROOT / "configs" / "algo" / "current.yaml"
    return current if current.exists() else ROOT / "configs" / "algo" / "baseline.yaml"
