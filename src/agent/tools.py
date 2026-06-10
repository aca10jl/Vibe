"""工具注册表：Agent 可调用的确定性工具及其说明。

LangGraph 节点直接 import 这些函数；本注册表同时作为权限文档——
任何新增工具必须在这里登记，写类工具必须内部经过 src/guard/paths 校验。
"""
from __future__ import annotations

from src.apply.code_patcher import submit_l2_proposal
from src.apply.config_mutator import apply_proposal, merge_to_current
from src.eval.harness import run_eval
from src.triage.bucketing import run_bucketing
from src.triage.evidence import generate_evidence

TOOLS = {
    "eval_harness.run_eval": {
        "fn": run_eval, "writes": "runs/<exp_id>/", "level": "read-mostly",
        "desc": "一键评测，输出 eval_report.json（PLAN 3.1）",
    },
    "bucketing.run_bucketing": {
        "fn": run_bucketing, "writes": "runs/<exp_id>/buckets.json", "level": "read-mostly",
        "desc": "失败自动分桶（PLAN 3.2）",
    },
    "evidence.generate_evidence": {
        "fn": generate_evidence, "writes": "runs/<exp_id>/evidence/", "level": "read-mostly",
        "desc": "证据包生成（PLAN 3.3）",
    },
    "config_mutator.apply_proposal": {
        "fn": apply_proposal, "writes": "内存 config（合入时落盘）", "level": "L1",
        "desc": "白名单内参数改动，硬校验",
    },
    "config_mutator.merge_to_current": {
        "fn": merge_to_current, "writes": "configs/algo/current.yaml", "level": "L1",
        "desc": "门禁通过后合入当前最优参数",
    },
    "code_patcher.submit_l2_proposal": {
        "fn": submit_l2_proposal, "writes": "runs/approval_queue/", "level": "L2",
        "desc": "生成 diff + 归因报告，等待人工批准，绝不直接执行",
    },
}
