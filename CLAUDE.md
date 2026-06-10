# D2DB-Tuner · VibeCoding 上下文

Die2Database 缺陷检测算法精度自动调优 Agent。施工蓝图见 `PLAN.md`，按其里程碑（M0→M4）开发。

## 常用命令

```bash
pip install -r requirements.txt

# 生成确定性合成数据集（manifest + dev/golden 切分）
python -m src.cli make-dataset

# 一键评测（mini 集秒级冒烟 / dev 全量）
python -m src.cli eval --split mini
python -m src.cli eval --split dev --baseline   # 跑通并存档 baseline

# 失败分桶 + 证据包
python -m src.cli triage --exp <exp_id>

# Agent 闭环（默认 offline 规则版 LLM；设 ANTHROPIC_API_KEY 后自动切换 API 模式）
python -m src.cli loop --iterations 5

# golden 集仅里程碑回归，结果绝不回传 Agent
python -m src.cli golden

# 测试
pytest tests/ -q
```

## 目录与职责

- `configs/algo/baseline.yaml` — 算法参数基线；`configs/algo/current.yaml` — 当前合入的最优参数
- `configs/search_space.yaml` — L1 可调参数白名单（路径 + 类型 + 取值范围），mutator 硬校验
- `configs/tuner.yaml` — Agent 自身配置：回归门禁规则、预算、LLM 模式
- `src/contracts/` — pydantic 数据契约（PLAN.md 第 3 节 Schema 的唯一实现）
- `src/algo/` — 被优化算法的适配层。`simulated.py` 为确定性仿真实现（用于开发/测试全链路）；接入真实 Die2Database 算法时实现 `interface.AlgoBackend` 协议并在 algo 配置中设 `backend: real`（见下）
- `src/eval/`、`src/triage/`、`src/agent/`、`src/apply/`、`src/guard/`、`src/tracking/` — 见 PLAN.md 第 2 节

## 只读禁区（任何改动工具在写入前必须经 src/guard/paths.py 校验）

- `src/eval/` 评测代码
- `src/guard/` 门禁代码
- `datasets/splits/golden.json` 黄金集
- `configs/search_space.yaml` 白名单本身
- `configs/tuner.yaml` 门禁与预算配置

违反即抛 `ForbiddenPathError`，不依赖提示词约束。

## 接入真实算法的契约

实现 `src/algo/interface.py::AlgoBackend`：

```python
class AlgoBackend(Protocol):
    def run_case(self, case: CaseSpec, config: dict) -> CaseResult: ...
```

`CaseResult` 含检出列表（坐标/EPE/score/信号量）与中间量（配准残差、轮廓质量、EPE 偏置等），
分桶规则引擎依赖这些中间量，真实算法需尽量填齐（缺失字段置 None，对应桶规则自动跳过）。

## 代码风格

- Python 3.11，pydantic v2 契约校验，全模块确定性（同一 config 重复评测指标必须完全一致）
- LLM 仅出现在 DIAGNOSE / PROPOSE 两个节点（`src/agent/`），其余全部为确定性工程代码
- 提示词在 `src/agent/prompts/` 下当代码管理，修改需写明动机

## 当前里程碑

M0–M3 已实现并通过测试（评测地基 / 分桶+证据包 / LLM 诊断节点 / L1 自主闭环）。
M4（overnight 无人值守 + L2 人工审批队列)：预算熔断与 L2 diff 生成已就绪，审批队列为文件目录形式（`runs/approval_queue/`）。
