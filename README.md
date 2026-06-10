# D2DB-Tuner — Die2Database 缺陷检测算法精度自动调优 Agent

基于 EPE 思想的 Die2Database 缺陷检测算法（SEM 图 vs GDS 渲染图对比）的自动调优系统。
施工蓝图见 [PLAN.md](PLAN.md)，工程约定见 [CLAUDE.md](CLAUDE.md)。

## 架构一览

```
Orchestrator (LangGraph 状态机, src/agent/graph.py)
  EVAL → BUCKET → DIAGNOSE → PROPOSE → (APPLY → REGRESSION → 合入|回滚
                                         | L2 → 人工审批队列) → REPORT → 循环
```

- **LLM 只出现在 DIAGNOSE / PROPOSE 两个节点**（`src/agent/llm.py`，走 OpenAI 兼容接口对接
  本地部署的多模态/语言大模型；未配置时自动退化为确定性规则版，整个闭环可离线复现）
- 其余节点全部为确定性工程代码：评测（`src/eval`）、五大根因桶分桶 + 证据包（`src/triage`）、
  L1 白名单 mutator / L2 diff 队列（`src/apply`）、回归门禁 + 预算（`src/guard`）、
  实验台账 + 每轮 markdown 日志（`src/tracking`）

## 三条铁律的落地

| 铁律 | 实现 |
|---|---|
| 评测先于优化 | `src/eval/harness.py` 一键评测，同一 config 重复评测指标完全一致（有单测固化） |
| 归因先于改动 | 每个提案必须挂在一个根因桶假设上；同一假设连续 2 次失败即冷却该桶 |
| 护栏先于自主 | L1/L2 权限分级；只读禁区在工具层硬拦截（`src/guard/paths.py`）；回归门禁不过即回滚；golden 集结果绝不回传 Agent |

## 快速开始

```bash
pip install -r requirements.txt
python -m src.cli make-dataset                       # 生成确定性合成数据集
python -m src.cli eval --split mini                  # 20 张图秒级冒烟
python -m src.cli loop --split dev --iterations 12   # 自主调优闭环
python -m src.cli golden                             # 里程碑 golden 回归
pytest tests/                                        # 32 项测试
```

### 对接本地大模型（OpenAI 兼容接口）

大模型全部参数集中在 `configs/tuner.yaml` 的 `llm` 段，与门禁/预算等配置放在一起：

```yaml
llm:
  mode: auto            # api / offline / auto（设了 OPENAI_BASE_URL 或 OPENAI_API_KEY 即走 api）
  api:
    base_url: http://127.0.0.1:8000/v1     # vLLM；Ollama 用 http://127.0.0.1:11434/v1
    api_key: EMPTY                          # 本地部署通常随意填
    chat_model: Qwen2.5-32B-Instruct        # PROPOSE：语言模型
    vision_model: Qwen2.5-VL-32B-Instruct   # DIAGNOSE：多模态模型（看证据包图片）
    temperature: 0.2
    max_tokens: 4096
    timeout_s: 180
    use_json_mode: true   # 服务端不支持 response_format 时自动降级重试
    send_images: false    # 没有多模态模型时置 false，DIAGNOSE 退化为纯文本证据
```

环境变量 `OPENAI_BASE_URL` / `OPENAI_API_KEY` 优先于配置文件。未配置任何模型服务时，
DIAGNOSE/PROPOSE 使用确定性 offline 规则版，闭环依然完整可跑。

## 当前效果（仿真后端，dev 120 图 / golden 59 图）

| 指标 | baseline | 调优后 | golden 验证 |
|---|---|---|---|
| recall | 0.684 | **0.954** | 0.709 → 0.977 |
| precision | 0.209 | **0.496** | 0.229 → 0.528 |
| nuisance rate | 0.791 | **0.505** | 0.771 → 0.472 |

一个 12 轮预算的 session 在 9 轮内收敛：五大根因桶各合入一次有效修复，
无效/有害提案被门禁回滚或冷却，残余不可参数化解决的问题自动生成 L2 提案进入
`runs/approval_queue/` 等待人工审批。

## 接入真实算法

实现 `src/algo/interface.py::AlgoBackend` 协议（输入 CaseSpec + config dict，输出检出列表与
分桶所需中间量），在 `configs/algo/baseline.yaml` 设 `algo.backend: real`；
数据侧按 `datasets/manifest.json` 的 CaseSpec schema 准备清单即可，其余链路无需改动。
