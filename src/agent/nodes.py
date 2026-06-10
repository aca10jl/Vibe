"""LangGraph 各节点实现。

LLM 只出现在 DIAGNOSE / PROPOSE；其余节点全部为确定性工程代码。
节点函数签名：state -> 增量 state 更新（dict）。
"""
from __future__ import annotations

import time
from typing import Any, TypedDict

from src.agent.llm import make_llm
from src.apply.code_patcher import submit_l2_proposal
from src.apply.config_mutator import MutationError, apply_proposal, load_search_space, merge_to_current
from src.contracts import EvalReport
from src.eval import harness
from src.guard.regression_gate import evaluate_gate
from src.tracking import reporter, tracker
from src.triage.bucketing import run_bucketing
from src.triage.evidence import generate_evidence


class TunerState(TypedDict, total=False):
    split: str
    tuner_cfg: dict
    config: dict                 # 当前已合入的最优算法参数
    iteration: int
    start_time: float
    current_report: Any          # EvalReport：当前 config 在 dev 上的报告
    buckets: Any                 # BucketsFile
    diagnosis: Any
    proposal: Any
    candidate_config: dict
    candidate_report: Any
    gate: Any
    history: list                # 每轮 {proposal, gate_passed, decision}
    cooldown_fails: dict         # bucket -> 连续失败次数
    decision: str
    stop_reason: str
    apply_error: str


# ----------------------------------------------------------------- nodes
def node_eval(state: TunerState) -> dict:
    upd: dict = {"iteration": state.get("iteration", 0) + 1,
                 "decision": "", "apply_error": "", "gate": None,
                 "candidate_report": None, "proposal": None}
    if state.get("current_report") is None:
        report = harness.run_eval(state["config"], state["split"])
        tracker.record(report.exp_id, "baseline", state["split"],
                       report.config_hash, report.git_commit, report.overall)
        upd["current_report"] = report
        upd["start_time"] = state.get("start_time") or time.monotonic()
    return upd


def node_bucket(state: TunerState) -> dict:
    report: EvalReport = state["current_report"]
    buckets = run_bucketing(report, state["config"])
    max_pb = state["tuner_cfg"]["llm"]["max_evidence_cases_per_bucket"]
    buckets = generate_evidence(report, buckets, max_per_bucket=max_pb)
    return {"buckets": buckets}


def node_diagnose(state: TunerState) -> dict:
    llm = make_llm(state["tuner_cfg"])
    threshold = state["tuner_cfg"]["convergence"]["hypothesis_cooldown_after_failures"]
    cooldown = {b for b, n in state.get("cooldown_fails", {}).items() if n >= threshold}
    diag = llm.diagnose(state["current_report"], state["buckets"], cooldown,
                        max_per_bucket=state["tuner_cfg"]["llm"]["max_evidence_cases_per_bucket"])
    return {"diagnosis": diag}


def node_propose(state: TunerState) -> dict:
    llm = make_llm(state["tuner_cfg"])
    proposal = llm.propose(
        state["diagnosis"], state["current_report"], state["buckets"],
        state["config"], load_search_space(), state.get("history", []),
        max_changes=state["tuner_cfg"]["budget"]["max_l1_changes_per_proposal"])
    return {"proposal": proposal}


def node_apply(state: TunerState) -> dict:
    max_changes = state["tuner_cfg"]["budget"]["max_l1_changes_per_proposal"]
    try:
        new_cfg = apply_proposal(state["config"], state["proposal"], max_changes)
    except MutationError as e:
        return {"apply_error": str(e)}
    if new_cfg == state["config"]:
        return {"apply_error": "提案为 no-op（所有参数已是目标值）"}
    return {"candidate_config": new_cfg, "apply_error": ""}


def node_regression(state: TunerState) -> dict:
    candidate = harness.run_eval(state["candidate_config"], state["split"])
    gate = evaluate_gate(candidate, state["current_report"],
                         state["tuner_cfg"]["regression_gate"]["rules"])
    return {"candidate_report": candidate, "gate": gate}


def node_merge_or_rollback(state: TunerState) -> dict:
    gate = state["gate"]
    proposal = state["proposal"]
    cooldown = dict(state.get("cooldown_fails", {}))
    cand: EvalReport = state["candidate_report"]
    base: EvalReport = state["current_report"]
    upd: dict = {"gate": gate}
    improved = (
        len(cand.failures["fp_ids"]) + len(cand.failures["fn_ids"])
        < len(base.failures["fp_ids"]) + len(base.failures["fn_ids"])
        or cand.overall["recall"] > base.overall["recall"] + 1e-9
    )
    if gate.passed and not improved:
        # 无回归但也无改善：不合入，按假设失败计入冷却，防止参数无意义漂移
        cooldown[proposal.target_bucket] = cooldown.get(proposal.target_bucket, 0) + 1
        status, decision = "rejected", "门禁通过但无任何改善，不合入（计入假设冷却）"
        tracker.record(cand.exp_id, "candidate", state["split"], cand.config_hash,
                       cand.git_commit, cand.overall, parent_exp=base.exp_id,
                       proposal=proposal.model_dump(by_alias=True),
                       gate=gate.model_dump(), status=status)
        hist = list(state.get("history", []))
        hist.append({"proposal_id": proposal.proposal_id, "bucket": proposal.target_bucket,
                     "changes": [c.model_dump(by_alias=True) for c in proposal.changes],
                     "gate_passed": False, "decision": decision})
        upd.update({"cooldown_fails": cooldown, "decision": decision, "history": hist})
        return upd
    if gate.passed:
        merge_to_current(state["candidate_config"])
        cooldown[proposal.target_bucket] = 0
        status, decision = "merged", (
            f"门禁通过，合入。FP {len(base.failures['fp_ids'])}→{len(cand.failures['fp_ids'])}，"
            f"FN {len(base.failures['fn_ids'])}→{len(cand.failures['fn_ids'])}。")
        upd.update({"config": state["candidate_config"], "current_report": cand})
    else:
        cooldown[proposal.target_bucket] = cooldown.get(proposal.target_bucket, 0) + 1
        status, decision = "rolled_back", f"门禁未通过，回滚：{'; '.join(gate.violations)}"
    tracker.record(cand.exp_id, "candidate", state["split"], cand.config_hash,
                   cand.git_commit, cand.overall, parent_exp=base.exp_id,
                   proposal=proposal.model_dump(by_alias=True),
                   gate=gate.model_dump(), status=status)
    hist = list(state.get("history", []))
    hist.append({"proposal_id": proposal.proposal_id, "bucket": proposal.target_bucket,
                 "changes": [c.model_dump(by_alias=True) for c in proposal.changes],
                 "gate_passed": gate.passed, "decision": decision})
    upd.update({"cooldown_fails": cooldown, "decision": decision, "history": hist})
    return upd


def node_l2_queue(state: TunerState) -> dict:
    proposal = state["proposal"]
    diag = state["diagnosis"]
    proposal.diff = proposal.diff or _l2_stub_diff(proposal)
    path = submit_l2_proposal(
        proposal,
        rationale_md=f"# L2 提案归因报告\n\n## 目标桶\n{proposal.target_bucket}\n\n"
                     f"## 根因\n{diag.root_cause}\n\n## 假设\n{proposal.hypothesis}\n")
    cooldown = dict(state.get("cooldown_fails", {}))
    threshold = state["tuner_cfg"]["convergence"]["hypothesis_cooldown_after_failures"]
    cooldown[proposal.target_bucket] = threshold  # 等待人工，先冷却该方向
    hist = list(state.get("history", []))
    decision = f"L2 提案已进入人工审批队列：{path}"
    hist.append({"proposal_id": proposal.proposal_id, "bucket": proposal.target_bucket,
                 "changes": [], "gate_passed": None, "decision": decision})
    return {"cooldown_fails": cooldown, "decision": decision, "history": hist}


def _l2_stub_diff(proposal) -> str:
    """L2 提案的占位 diff：标注目标模块，由人工/后续编码 Agent 补全实现。"""
    module = {"B1_ALIGN": "alignment", "B2_CONTOUR": "contour",
              "B3_RENDER_GAP": "render", "B4_THRESHOLD": "gauge",
              "B5_PROC_VAR": "judge"}.get(proposal.target_bucket, "unknown")
    return (f"--- a/docs/l2_requests/{proposal.proposal_id}.md\n"
            f"+++ b/docs/l2_requests/{proposal.proposal_id}.md\n"
            "@@ -0,0 +1,2 @@\n"
            f"+目标模块: {module}\n"
            f"+假设: {proposal.hypothesis}\n")


def node_report(state: TunerState) -> dict:
    if state.get("proposal") is None:
        return {}
    if state.get("apply_error"):
        decision = f"提案被 mutator 拒绝：{state['apply_error']}"
        cooldown = dict(state.get("cooldown_fails", {}))
        cooldown[state["proposal"].target_bucket] = \
            cooldown.get(state["proposal"].target_bucket, 0) + 1
        hist = list(state.get("history", []))
        hist.append({"proposal_id": state["proposal"].proposal_id,
                     "bucket": state["proposal"].target_bucket,
                     "changes": [], "gate_passed": False, "decision": decision})
        reporter.write_round_report(state["iteration"], state["proposal"],
                                    state["current_report"], None, None, decision)
        return {"cooldown_fails": cooldown, "history": hist, "decision": decision}
    reporter.write_round_report(
        state["iteration"], state["proposal"], state["current_report"],
        state.get("candidate_report"), state.get("gate"),
        state.get("decision") or "（无结论）")
    return {}


# ----------------------------------------------------------------- routes
def route_after_bucket(state: TunerState) -> str:
    if not state["buckets"].buckets:
        return "no_failures"
    threshold = state["tuner_cfg"]["convergence"]["hypothesis_cooldown_after_failures"]
    cooled = {b for b, n in state.get("cooldown_fails", {}).items() if n >= threshold}
    actionable = {b for b in state["buckets"].summary if b != "UNKNOWN"} - cooled
    return "diagnose" if actionable else "no_actionable"


def route_level(state: TunerState) -> str:
    return state["proposal"].level


def route_after_apply(state: TunerState) -> str:
    return "rejected" if state.get("apply_error") else "regression"


def route_continue(state: TunerState) -> str:
    budget = state["tuner_cfg"]["budget"]
    if state["iteration"] >= budget["max_iterations_per_session"]:
        return "end"
    if time.monotonic() - state.get("start_time", time.monotonic()) \
            >= budget["max_wall_hours"] * 3600:
        return "end"
    return "continue"
