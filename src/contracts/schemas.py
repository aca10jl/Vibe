"""数据契约：PLAN.md 第 3 节 Schema 的唯一实现。

所有模块间传递的结构化数据都必须经过这里的 pydantic 模型校验，
落盘 JSON 与内存对象一一对应。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

DEFECT_TYPES = ("bridge", "open", "intrusion")
BUCKET_IDS = ("B1_ALIGN", "B2_CONTOUR", "B3_RENDER_GAP", "B4_THRESHOLD", "B5_PROC_VAR", "UNKNOWN")

BucketId = Literal["B1_ALIGN", "B2_CONTOUR", "B3_RENDER_GAP", "B4_THRESHOLD", "B5_PROC_VAR", "UNKNOWN"]
DefectType = Literal["bridge", "open", "intrusion"]


# ---------------------------------------------------------------- dataset
class GroundTruthDefect(BaseModel):
    defect_id: str
    type: DefectType
    x: float
    y: float
    near_corner: bool = False
    near_line_end: bool = False


class CaseSpec(BaseModel):
    """一个评测 case = 一张 SEM 图（含对应 GDS clip）及其标注。"""

    case_id: str
    layer: str                          # M1 / M2 / V1 ...
    pattern_density: float              # 0~1
    contrast: float                     # SEM 成像对比度 0~1
    noise_level: float                  # 0~1
    optimal_sigma: float                # 该图最佳轮廓梯度尺度（仿真用，真实数据可缺省）
    charging: bool = False              # 是否存在 charging 伪影
    cross_die_repeat: bool = False      # 同位置跨 die 重复（工艺变异）特征
    defects: list[GroundTruthDefect] = Field(default_factory=list)
    seed: int = 0
    image_path: Optional[str] = None    # 真实数据时指向 SEM 图路径


# ---------------------------------------------------------------- algorithm output
class Detection(BaseModel):
    det_id: str
    x: float
    y: float
    type_guess: DefectType
    epe_nm: float
    score: float
    near_corner: bool = False
    near_line_end: bool = False
    signals: dict = Field(default_factory=dict)


class CaseResult(BaseModel):
    case_id: str
    detections: list[Detection] = Field(default_factory=list)
    intermediates: dict = Field(default_factory=dict)
    # 配准残差 px / 相关峰锐度 / 轮廓断裂数 / 边缘 SNR / charging 检出 / EPE 偏置 nm 等


# ---------------------------------------------------------------- eval report (PLAN 3.1)
class Metrics(BaseModel):
    recall: float
    precision: float
    count: int = 0


class EvalReport(BaseModel):
    exp_id: str
    config_hash: str
    git_commit: str
    dataset_split: str
    overall: dict                                  # recall / precision / nuisance_rate
    per_defect_type: dict[str, Metrics]
    per_layer: dict[str, Metrics]
    epe_error: dict                                # mean_nm / p95_nm / histogram
    failures: dict                                 # fp_ids / fn_ids


# ---------------------------------------------------------------- buckets (PLAN 3.2)
class BucketAssignment(BaseModel):
    case_id: str                                   # 失败 case id：fp::case::site / fn::case::defect
    bucket: BucketId
    confidence: float
    signals: dict = Field(default_factory=dict)
    evidence_pack: Optional[str] = None


class BucketsFile(BaseModel):
    exp_id: str
    buckets: list[BucketAssignment]
    summary: dict[str, int]


# ---------------------------------------------------------------- diagnosis / proposal (PLAN 3.4)
class Diagnosis(BaseModel):
    exp_id: str
    target_bucket: BucketId
    root_cause: str
    bucket_corrections: dict[str, str] = Field(default_factory=dict)  # case_id -> 修正后的桶
    confidence: float = 0.5


class ConfigChange(BaseModel):
    type: Literal["config"] = "config"
    path: str                                      # 点号路径，如 render.corner_rounding_nm
    from_value: object = Field(alias="from")
    to_value: object = Field(alias="to")

    model_config = {"populate_by_name": True}


class Proposal(BaseModel):
    proposal_id: str
    hypothesis: str
    target_bucket: BucketId
    level: Literal["L1", "L2"]
    changes: list[ConfigChange] = Field(default_factory=list)
    expected_effect: str = ""
    risk: str = ""
    diff: Optional[str] = None                     # L2：代码 diff 文本


# ---------------------------------------------------------------- gate
class GateResult(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list)
    candidate_exp: str
    baseline_exp: str
