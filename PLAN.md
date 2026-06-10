# Die2Database 缺陷检测算法精度自动调优 Agent · 开发方案

> **代号**：D2DB-Tuner
> **定位**:本文档是 VibeCoding 的施工蓝图。可直接放入仓库根目录(建议命名 `PLAN.md`),配合 `CLAUDE.md` 使用,按里程碑逐段喂给编码 Agent。
> **前提**:数据、标注、Die2Database 算法源码已就绪。算法基于 EPE 思想,SEM 图与 GDS 图对比识别缺陷。

---

## 0. 设计哲学(三条铁律)

1. **评测先于优化**:没有可信、可一键复跑的评测,一切自动调优都是噪声。评测体系是地基,M0 必须先完成。
2. **归因先于改动**:Agent 每一次改动必须挂在一个明确的失败根因假设上,禁止盲目网格搜索。
3. **护栏先于自主**:权限分级 + 回归门禁 + golden set 隔离,先人工在环验证归因可信度,再逐步放开自主权。

---

## 1. 系统总体架构

```
┌─────────────────────────────────────────────────────────┐
│                  Orchestrator(LangGraph)                │
│   状态机:EVAL → BUCKET → DIAGNOSE → PROPOSE → APPLY     │
│            → REGRESSION → (合入 | 回滚) → REPORT → 循环   │
└──────┬──────────────────────────────────────────────────┘
       │ 工具调用(Tool Layer,全部为确定性 CLI/函数)
       ▼
┌──────────────┬──────────────┬──────────────┬─────────────┐
│ eval_harness │ failure_     │ evidence_    │ experiment_ │
│ 一键评测      │ bucketing    │ pack 证据包  │ tracker     │
│              │ 失败自动分桶  │ 生成器       │ 实验台账     │
├──────────────┼──────────────┼──────────────┼─────────────┤
│ config_      │ code_        │ regression_  │ reporter    │
│ mutator      │ patcher      │ gate         │ 实验日志     │
│ L1参数改动   │ L2代码diff   │ 回归门禁      │ 生成器      │
└──────────────┴──────────────┴──────────────┴─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│        被优化对象:Die2Database 算法仓库(git 管理)        │
│   SEM-GDS对齐 → 轮廓提取 → GDS渲染 → EPE计算 → 缺陷判定   │
└─────────────────────────────────────────────────────────┘
```

**LLM 只出现在两个节点**:DIAGNOSE(多模态看证据包归因)和 PROPOSE(生成改动方案)。其余节点全部是确定性工程代码——这是系统可信、可复现的关键。

---

## 2. 仓库目录结构

```
d2db-tuner/
├── PLAN.md                       # 本文档
├── CLAUDE.md                     # VibeCoding 上下文:约定、命令、禁区
├── configs/
│   ├── algo/                     # 算法参数 YAML(对齐/轮廓/EPE阈值/滤波)
│   │   └── baseline.yaml
│   ├── tuner.yaml                # Agent 自身配置(迭代上限、容差、权限)
│   └── search_space.yaml         # L1 可调参数白名单 + 取值范围
├── datasets/
│   ├── manifest.json             # 数据清单:分层信息(缺陷类型/layer/密度)
│   ├── splits/
│   │   ├── dev.json              # 开发集(Agent 可见)
│   │   └── golden.json           # 黄金集(Agent 永不可见,仅里程碑回归)
├── src/
│   ├── eval/
│   │   ├── harness.py            # run_eval(config) → report.json
│   │   ├── metrics.py            # per-type R/P、Nuisance、EPE误差分布
│   │   └── matcher.py            # 检出框与标注匹配逻辑(IoU/中心距)
│   ├── triage/
│   │   ├── bucketing.py          # FP/FN → 五大根因桶
│   │   └── evidence.py           # 证据包生成(叠加图/heatmap/中间量)
│   ├── agent/
│   │   ├── graph.py              # LangGraph 状态机定义
│   │   ├── nodes.py              # 各节点实现
│   │   ├── prompts/              # diagnose/propose 提示词(版本化管理)
│   │   └── tools.py              # 工具注册与 schema
│   ├── apply/
│   │   ├── config_mutator.py     # L1:白名单内改 YAML
│   │   └── code_patcher.py       # L2:生成 diff + 归因报告,等待人工批准
│   ├── guard/
│   │   ├── regression_gate.py    # 回归门禁判定
│   │   └── budget.py             # 迭代次数/token/时长预算控制
│   └── tracking/
│       ├── tracker.py            # 实验台账(SQLite + git branch 绑定)
│       └── reporter.py           # 每轮 markdown 实验日志
├── runs/                         # 实验产物(按 exp_id 归档)
└── tests/                        # 单元测试 + 端到端冒烟测试
```

---

## 3. 核心数据契约(先定 Schema,后写代码)

### 3.1 评测报告 `eval_report.json`

```json
{
  "exp_id": "exp_20260610_001",
  "config_hash": "a3f9...",
  "git_commit": "d41d...",
  "dataset_split": "dev",
  "overall": { "recall": 0.912, "precision": 0.874, "nuisance_rate": 0.063 },
  "per_defect_type": {
    "bridge":    { "recall": 0.95, "precision": 0.91, "count": 412 },
    "open":      { "recall": 0.88, "precision": 0.86, "count": 305 },
    "intrusion": { "recall": 0.90, "precision": 0.83, "count": 198 }
  },
  "per_layer": { "M1": {...}, "V1": {...} },
  "epe_error": { "mean_nm": 1.8, "p95_nm": 4.2, "histogram": [...] },
  "failures": { "fp_ids": [...], "fn_ids": [...] }
}
```

### 3.2 失败分桶结果 `buckets.json`

五大根因桶(规则引擎初判 + LLM 复核):

| 桶 ID | 根因 | 规则信号(示例) |
|---|---|---|
| `B1_ALIGN` | SEM-GDS 对齐失败 | 配准残差 > 阈值、相关峰锐度低 |
| `B2_CONTOUR` | 轮廓提取问题 | 轮廓断裂数、边缘梯度 SNR 低、charging 检测 |
| `B3_RENDER_GAP` | GDS 渲染与真实形貌差异 | FP 集中于 corner/线端、EPE 系统性偏置 |
| `B4_THRESHOLD` | EPE 阈值设置不当 | FP/FN 的 EPE 值贴近阈值边界、pattern 密度相关 |
| `B5_PROC_VAR` | 工艺变异误判 | 同位置跨 die 重复、CD 漂移特征 |

```json
{
  "exp_id": "exp_20260610_001",
  "buckets": [
    { "case_id": "fp_0042", "bucket": "B3_RENDER_GAP",
      "confidence": 0.85, "signals": {"epe_bias_nm": 2.1, "near_corner": true},
      "evidence_pack": "runs/exp_.../evidence/fp_0042/" }
  ],
  "summary": { "B1": 12, "B2": 8, "B3": 41, "B4": 19, "B5": 6, "UNKNOWN": 3 }
}
```

### 3.3 证据包(每个失败 case 一个目录)

```
evidence/fp_0042/
├── sem_raw.png            # 原始 SEM
├── overlay.png            # SEM + GDS 轮廓叠加(对齐后)
├── epe_heatmap.png        # EPE 热力图
├── intermediates.json     # 配准残差/轮廓质量分/EPE统计等中间量
└── context.json           # layer、pattern密度、邻近die情况、标注信息
```

### 3.4 改动提案 `proposal.json`

```json
{
  "proposal_id": "p_017",
  "hypothesis": "B3桶FP集中在M1层线端,GDS渲染未做corner rounding,导致线端EPE系统性偏大2nm",
  "target_bucket": "B3_RENDER_GAP",
  "level": "L1",
  "changes": [
    { "type": "config", "path": "render.corner_rounding_nm", "from": 0, "to": 8 },
    { "type": "config", "path": "epe.line_end_tolerance_nm", "from": 3, "to": 5 }
  ],
  "expected_effect": "B3桶FP减少≥50%,各类型recall不下降",
  "risk": "线端真实缺陷可能漏检,重点观察open类recall"
}
```

---

## 4. 权限分级(系统安全核心)

| 级别 | 范围 | 自主权 | 审批 |
|---|---|---|---|
| **L1** | `search_space.yaml` 白名单内的 YAML 参数 | Agent 全自主迭代 | 回归门禁通过即合入 |
| **L2** | 算法代码改动(对齐/轮廓/渲染/判定逻辑) | 仅生成 diff + 归因报告 | 人工审核后才执行 |
| **禁区** | 评测代码、门禁代码、golden set、本白名单本身 | 任何情况下不可改 | — |

> **关键**:Agent 修改自己的考卷和考官是最大风险。`src/eval/`、`src/guard/`、`datasets/splits/golden.json` 对 Agent 是只读路径,在工具层硬性拦截,不依赖提示词约束。

---

## 5. 回归门禁(每次改动的硬条件)

```yaml
# configs/tuner.yaml 节选
regression_gate:
  dataset: dev
  rules:
    - overall.recall            >= baseline - 0.002    # 总recall几乎不许降
    - per_type.*.recall         >= baseline - 0.005    # 任一类型recall容差0.5%
    - overall.nuisance_rate     <= baseline + 0.005
    - epe_error.p95_nm          <= baseline * 1.10
  on_fail: rollback_branch      # git 回滚,记录失败实验
budget:
  max_iterations_per_session: 20
  max_wall_hours: 8             # overnight 模式预算
  max_l1_changes_per_proposal: 3  # 单次提案最多动3个参数,保持归因可解释
golden_policy:
  run_only_at: [milestone]      # golden 仅里程碑跑
  feed_back_to_agent: false     # 结果绝不回传 Agent,防隐性过拟合
```

---

## 6. Agent 闭环主流程(LangGraph 状态机)

```
START
 → EVAL          eval_harness.run(dev) → report.json
 → BUCKET        bucketing.run(failures) → buckets.json + 证据包
 → DIAGNOSE      LLM(多模态) 读证据包,确认/修正桶归属,输出根因分析
 → PROPOSE       LLM 基于根因 + search_space 生成 proposal.json
 → GATE_LEVEL    L1 → APPLY_CONFIG(自动) | L2 → 挂起等人工批准
 → APPLY         git新分支上执行改动
 → REGRESSION    eval_harness.run(dev) → regression_gate判定
 → MERGE/ROLLBACK
 → REPORT        本轮markdown日志(假设→改动→结果→结论)
 → 预算未尽 ? 回到 EVAL : END
```

**收敛策略**:每轮 PROPOSE 优先攻击占比最大的桶;同一假设连续 2 次失败则标记该方向冷却,换下一个桶,防止 Agent 在局部死磕。

---

## 7. 里程碑计划(VibeCoding 施工顺序)

### M0 · 评测地基(第 1-2 周,纯工程,无 LLM)

- [ ] `datasets/manifest.json`:分层采样切出 dev / golden,golden 加密或权限隔离
- [ ] `src/eval/`:一键评测,输出 3.1 格式报告;跑通 baseline 并存档
- [ ] `src/tracking/`:实验台账,exp_id ↔ git branch ↔ config hash 三方绑定
- **验收**:同一 config 重复评测,指标完全一致(确定性);baseline 报告入库

### M1 · 失败分桶 + 证据包(第 2-3 周)

- [ ] `src/triage/bucketing.py`:规则引擎按五大桶信号初判
- [ ] `src/triage/evidence.py`:批量生成证据包
- **验收**:人工抽检 50 个 case,规则初判桶准确率 ≥ 70%;UNKNOWN 占比 < 15%

### M2 · LLM 诊断,人工在环(第 3-4 周)

- [ ] `src/agent/` 中 DIAGNOSE / PROPOSE 节点 + 提示词
- [ ] 跑 5-10 轮人工在环:LLM 归因 vs 工程师归因对照打分
- **验收**:LLM 归因与人工一致率 ≥ 80%;提案被工程师评为"合理"的比例 ≥ 70%

### M3 · L1 自主闭环(第 5-6 周)

- [ ] APPLY / REGRESSION / 回滚全链路;`config_mutator` 白名单硬约束
- [ ] 白天监督模式连续运行 ≥ 3 个 session 无失控
- **验收**:dev set 上至少一项 per-type recall 提升 ≥ 1pp 且无任何门禁违规

### M4 · Overnight 无人值守 + L2 提案(第 7-8 周)

- [ ] 预算控制、异常熔断(评测崩溃/指标异常波动即停)、晨间汇总报告
- [ ] `code_patcher`:L2 diff + 归因报告生成,接入人工审批队列
- **验收**:连续 5 个 overnight 无人工干预安全完成;golden set 里程碑回归通过

---

## 8. VibeCoding 使用指引

1. **仓库初始化**:将本文档存为 `PLAN.md`;另建 `CLAUDE.md` 写入:常用命令(评测/测试)、代码风格、**只读禁区路径清单**、当前所处里程碑。
2. **按里程碑逐段施工**:每次给编码 Agent 的指令模板——
   > "阅读 PLAN.md 第 N 节,实现 Mx 中的 [具体模块]。先写该模块的单元测试,再写实现,完成后跑 `pytest tests/` 并给出验收项自查结果。不得触碰第 4 节列出的禁区路径。"
3. **每个模块的完成定义(DoD)**:单测通过 + 数据契约校验(用 pydantic/jsonschema 固化第 3 节 Schema)+ 在 PLAN.md 勾掉对应 checkbox。
4. **提示词当代码管**:`src/agent/prompts/` 下的诊断/提案提示词纳入 git,每次修改记录动机与效果,这是后期调优 Agent 本身的主要抓手。
5. **先冒烟后全量**:M0 起就维护一个 20 张图的 mini 数据集,所有开发用它秒级跑通,全量数据只在验收时跑。

---

## 9. 验收总指标(项目级)

| 维度 | 目标 |
|---|---|
| 精度 | dev set 各缺陷类型 recall 平均提升 ≥ 2pp,nuisance rate 不升 |
| 效率 | 单轮"评测→归因→改动→回归"全自动 ≤ 45 min |
| 可信 | golden set 里程碑回归与 dev 趋势一致(无过拟合迹象) |
| 安全 | 0 次禁区触碰;0 次未过门禁的改动流入主分支 |
| 沉淀 | 每轮实验日志完整可复盘,失败实验同样归档 |
