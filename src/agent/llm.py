"""DIAGNOSE / PROPOSE 两个 LLM 节点的客户端。

- ClaudeLLM：调用 Anthropic API（多模态读证据包，结构化输出 JSON）。
- OfflineLLM：确定性规则版，用于无 API key 的开发/测试，行为与提示词中的
  参考方向一致，保证闭环可离线复现。

llm.mode=auto 时：有 ANTHROPIC_API_KEY 用 ClaudeLLM，否则 OfflineLLM。
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from src.contracts import BucketsFile, Diagnosis, EvalReport, Proposal

ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS = Path(__file__).resolve().parent / "prompts"

_DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "target_bucket": {"type": "string",
                          "enum": ["B1_ALIGN", "B2_CONTOUR", "B3_RENDER_GAP",
                                   "B4_THRESHOLD", "B5_PROC_VAR", "UNKNOWN"]},
        "root_cause": {"type": "string"},
        "bucket_corrections": {"type": "object", "additionalProperties": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": ["target_bucket", "root_cause", "bucket_corrections", "confidence"],
    "additionalProperties": False,
}

_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "hypothesis": {"type": "string"},
        "target_bucket": {"type": "string"},
        "level": {"type": "string", "enum": ["L1", "L2"]},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "to": {"type": ["number", "boolean", "integer"]},
                },
                "required": ["path", "to"],
                "additionalProperties": False,
            },
        },
        "expected_effect": {"type": "string"},
        "risk": {"type": "string"},
    },
    "required": ["hypothesis", "target_bucket", "level", "changes",
                 "expected_effect", "risk"],
    "additionalProperties": False,
}


def make_llm(tuner_cfg: dict):
    mode = tuner_cfg["llm"]["mode"]
    if mode == "api" or (mode == "auto" and os.environ.get("ANTHROPIC_API_KEY")):
        return ClaudeLLM(model=tuner_cfg["llm"]["model"])
    return OfflineLLM()


# ===================================================================== API 版
class ClaudeLLM:
    def __init__(self, model: str = "claude-opus-4-8"):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model

    @staticmethod
    def _image_block(path: Path) -> dict:
        return {"type": "image",
                "source": {"type": "base64", "media_type": "image/png",
                           "data": base64.standard_b64encode(path.read_bytes()).decode()}}

    def _evidence_blocks(self, buckets: BucketsFile, max_per_bucket: int) -> list[dict]:
        blocks: list[dict] = []
        taken: dict[str, int] = {}
        for a in buckets.buckets:
            if not a.evidence_pack or taken.get(a.bucket, 0) >= max_per_bucket:
                continue
            taken[a.bucket] = taken.get(a.bucket, 0) + 1
            ev = ROOT / a.evidence_pack
            blocks.append({"type": "text",
                           "text": f"## 失败 case {a.case_id}（初判 {a.bucket}）\n"
                                   f"context: {(ev / 'context.json').read_text()}\n"
                                   f"intermediates: {(ev / 'intermediates.json').read_text()}"})
            for img in ("sem_raw.png", "overlay.png", "epe_heatmap.png"):
                p = ev / img
                if p.exists():
                    blocks.append(self._image_block(p))
        return blocks

    def _call(self, system: str, content: list[dict], schema: dict) -> dict:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    def diagnose(self, report: EvalReport, buckets: BucketsFile,
                 cooldown: set[str], max_per_bucket: int = 3) -> Diagnosis:
        system = (PROMPTS / "diagnose.md").read_text()
        content: list[dict] = [
            {"type": "text",
             "text": f"## 本轮指标\n{json.dumps(report.overall, ensure_ascii=False)}\n"
                     f"## 分桶汇总\n{json.dumps(buckets.summary, ensure_ascii=False)}\n"
                     f"## 冷却中的桶（不要选）\n{sorted(cooldown)}"},
            *self._evidence_blocks(buckets, max_per_bucket),
        ]
        out = self._call(system, content, _DIAGNOSIS_SCHEMA)
        return Diagnosis(exp_id=report.exp_id, **out)

    def propose(self, diagnosis: Diagnosis, report: EvalReport, buckets: BucketsFile,
                config: dict, search_space: dict, history: list[dict],
                max_changes: int) -> Proposal:
        system = (PROMPTS / "propose.md").read_text()
        content = [{"type": "text", "text":
                    f"## 根因分析\n{diagnosis.model_dump_json()}\n"
                    f"## 当前 config\n{json.dumps(config, ensure_ascii=False)}\n"
                    f"## search_space 白名单\n{json.dumps(search_space, ensure_ascii=False)}\n"
                    f"## max_changes\n{max_changes}\n"
                    f"## history（最近的提案与结果）\n"
                    f"{json.dumps(history[-6:], ensure_ascii=False)}"}]
        out = self._call(system, content, _PROPOSAL_SCHEMA)
        from src.apply.config_mutator import _get  # 当前值回填 from 字段

        changes = []
        for ch in out["changes"]:
            cur = _get(config, ch["path"]) if _exists(config, ch["path"]) else None
            changes.append({"path": ch["path"], "from": cur, "to": ch["to"]})
        return Proposal(
            proposal_id=f"p_{len(history) + 1:03d}",
            hypothesis=out["hypothesis"],
            target_bucket=out["target_bucket"],
            level=out["level"],
            changes=changes,
            expected_effect=out["expected_effect"],
            risk=out["risk"],
        )


def _exists(cfg: dict, dotted: str) -> bool:
    node = cfg
    for k in dotted.split("."):
        if not isinstance(node, dict) or k not in node:
            return False
        node = node[k]
    return True


# ================================================================== 离线规则版
class OfflineLLM:
    """确定性规则实现：复核=接受规则初判；提案=按桶查 playbook。"""

    _ROOT_CAUSE = {
        "B1_ALIGN": "配准迭代数不足/相关阈值过严，低对比度图上对齐不收敛，产生整图级 FN/FP。",
        "B2_CONTOUR": "梯度尺度与图像最优尺度失配且 charging 未补偿，轮廓断裂导致 open 漏检与碎片 FP。",
        "B3_RENDER_GAP": "GDS 渲染未建模 corner rounding / 线端收缩，corner 与线端处 EPE 系统性偏大造成 FP。",
        "B4_THRESHOLD": "EPE 阈值未随 pattern 密度自适应，高密度图整体 EPE 抬升使贴边 nuisance 越线。",
        "B5_PROC_VAR": "同位置跨 die 重复的 CD 漂移属工艺变异，未做跨 die 投票过滤被误判为缺陷。",
    }

    def diagnose(self, report: EvalReport, buckets: BucketsFile,
                 cooldown: set[str], max_per_bucket: int = 3) -> Diagnosis:
        ranked = sorted(((n, b) for b, n in buckets.summary.items()
                         if b != "UNKNOWN" and b not in cooldown), reverse=True)
        target = ranked[0][1] if ranked else "UNKNOWN"
        return Diagnosis(
            exp_id=report.exp_id, target_bucket=target,
            root_cause=self._ROOT_CAUSE.get(target, "证据不足，无法归因。"),
            bucket_corrections={}, confidence=0.7,
        )

    def propose(self, diagnosis: Diagnosis, report: EvalReport, buckets: BucketsFile,
                config: dict, search_space: dict, history: list[dict],
                max_changes: int) -> Proposal:
        from src.apply.config_mutator import _get

        fp_n = len(report.failures["fp_ids"])
        fn_n = len(report.failures["fn_ids"])
        playbook: dict[str, list[tuple[str, object]]] = {
            "B3_RENDER_GAP": [("render.corner_rounding_nm", 8.0),
                              ("render.line_end_shortening_nm", 6.0)],
            "B4_THRESHOLD": [("gauge.density_adaptive", True)] if not config["gauge"]["density_adaptive"]
                            else [("gauge.epe_threshold_nm",
                                   round(config["gauge"]["epe_threshold_nm"] + (0.3 if fp_n >= fn_n else -0.3), 2))],
            "B5_PROC_VAR": [("judge.proc_var_filter", True), ("judge.cross_die_votes", 3)],
            "B2_CONTOUR": [("contour.gradient_sigma", 1.45),
                           ("contour.charging_compensation", True)],
            "B1_ALIGN": [("alignment.max_iterations", 55),
                         ("alignment.min_correlation", 0.45)],
        }
        moves = [(p, v) for p, v in playbook.get(diagnosis.target_bucket, [])
                 if _get(config, p) != v][:max_changes]
        pid = f"p_{len(history) + 1:03d}"
        if not moves:
            return Proposal(
                proposal_id=pid,
                hypothesis=f"{diagnosis.target_bucket} 的 L1 参数空间已用尽，疑似算法代码缺陷，需 L2 改动。",
                target_bucket=diagnosis.target_bucket, level="L2", changes=[],
                expected_effect="待人工评审", risk="L2 改动需人工审批",
            )
        return Proposal(
            proposal_id=pid,
            hypothesis=f"{diagnosis.target_bucket}: {diagnosis.root_cause}",
            target_bucket=diagnosis.target_bucket, level="L1",
            changes=[{"path": p, "from": _get(config, p), "to": v} for p, v in moves],
            expected_effect=f"{diagnosis.target_bucket} 桶失败数显著下降，各类型 recall 不降",
            risk="参数放宽可能引入新 FN，靠回归门禁兜底",
        )
