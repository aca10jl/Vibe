# 一键一生 · Wafer 良率根因分析 + AI 伴读助手

> 半导体晶圆全生命周期（一键一生）分析平台 Demo —— 一个按键，把 Wafer 的全链路历史在 HTML 页面中还原；
> 页面右侧内置 **AI 伴读助手**，能**阅读页面内容、指引正确提交任务、分析良率根因**，并以**智能体技术持续学习用户习惯**。

![mode](https://img.shields.io/badge/AI-本地推理%20%7C%20Claude%20在线-3b82f6) ![stack](https://img.shields.io/badge/stack-Vanilla%20JS%20%2B%20ECharts%20%2B%20Node-1f9d55)

## ✨ 能力一览

- **一键一生**：**左侧逐步配置（①场景→②维度→③呈现→④提交）→ 主区域结果呈现**，两阶段布局自动切换；一键还原晶圆全链路（晶圆 Bin 图 / 良率趋势 / WAT 参数 / 缺陷 Pareto / 工艺时间轴 / 根因候选）。
- **AI 伴读 / 分析 / 建议**：右侧助手三大通道，读懂当前页面、做根因分析、指引正确提交。
- **智能体（会动手）**：AI 通过工具调用**真正操作页面**——自动填表、设维度、提交、定位高亮面板。
- **持续学习习惯**：行为画像沉淀（常用 Fab/节点/维度/意图），反哺个性化默认值与建议。
- **三种 AI 来源 & 零门槛**：**本地推理**（默认，无需密钥）/ **本地大模型**（Ollama·LM Studio·vLLM·llama.cpp 等 OpenAI 兼容端点，私有化离线）/ **Claude 在线**（claude-opus-4-8）。右上角一键切换，三者统一支持工具调用。

## 🚀 快速开始

```bash
# 方式一：纯静态（最快，仅本地推理）
./start.sh static          # → http://localhost:8000
# 也可直接双击打开 web/index.html

# 方式二：全功能（可选接入真实 Claude）
./start.sh                 # → http://localhost:8787（首次自动装依赖）
#   接 Claude：cd server && cp .env.example .env && 填入 ANTHROPIC_API_KEY，再重启
```

> 演示脚本见 [`docs/部署与Demo.md`](docs/部署与Demo.md)。

## 🧩 架构（详见 [`docs/调研与设计.md`](docs/调研与设计.md)）

```
左：场景设定   │   中：一键一生结果呈现(ECharts)   │   右：AI 助手(伴读/分析/建议)
        └──────── Agent 引擎：上下文采集 · 工具调用 · 习惯学习 · 双模LLM ────────┘
                                   │ (仅 Claude 模式) → Node 后端代理 → Claude API
```

## 📁 目录

```
web/                       前端（可独立静态运行）
  index.html  css/  js/
  js/data/mockData.js      合成晶圆"一生"数据（替换此处即可接真实数据）
  js/charts.js             ECharts 可视化
  js/app.js                一键一生主界面
  js/agent/                AI 智能体引擎
    contextCollector.js      读页面 → 结构化上下文 + 填表校验
    tools.js                 可调用的页面动作（function-calling）
    habitProfile.js          习惯学习（localStorage 画像）
    llmClient.js             双模：本地推理 / Claude 后端
    assistant.js             右侧助手 UI
server/                    Node/Express：静态托管 + Claude 代理(/api/chat)
docs/                      调研与设计、部署与 Demo
start.sh                   一键启动
```

## 🔌 接真实数据 / 真实模型

- **数据**：替换 `web/js/data/mockData.js::generateLifecycle()` 的返回（保持字段契约），可视化与 AI 全部复用。
- **模型**：后端 `server/server.js` 已用官方 SDK 接入 `claude-opus-4-8`（adaptive thinking + 原生工具调用）；配置 `ANTHROPIC_API_KEY` 即可。

## 📜 说明

本仓库为 Demo：晶圆数据为**可复现的合成数据**（同一 Wafer ID 生成同一结果），缺陷空间特征与根因环节做了**领域自洽**映射（如中心聚集↔CMP、边缘环↔边缘刻蚀/清洗），便于展示真实分析体验。
