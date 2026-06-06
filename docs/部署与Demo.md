# 部署与 Demo 指南

## 0. 运行模式

| 启动方式 | 命令 | 可用 AI 来源 | 需要 |
|---|---|---|---|
| **纯静态**（最快） | `./start.sh static` | 本地推理；本地大模型（浏览器直连，需 CORS） | 浏览器 / python3 |
| **全功能** | `./start.sh` | 本地推理 + 本地大模型 + Claude 在线 | Node ≥ 20 |

右侧 AI 助手有**三种推理来源**（右上角下拉切换）：

| 来源 | 说明 | 是否需密钥/服务 |
|---|---|---|
| **本地推理** | 纯前端规则引擎，零依赖 | 否（默认，开箱即用） |
| **本地大模型** | 你自部署的 OpenAI 兼容端点（Ollama/LM Studio/vLLM/llama.cpp） | 需本地模型服务 |
| **Claude 在线** | 后端代理到 `claude-opus-4-8` | 需 `ANTHROPIC_API_KEY` |

> Demo 默认**不配置任何东西**即可跑（本地推理）。三种来源**统一支持工具调用**（填表/提交/定位面板）。

---

## 1. 最快上手（纯静态，30 秒）

```bash
./start.sh static          # 启动后访问 http://localhost:8000
# 或者直接用浏览器打开 web/index.html（双击即可）
```

## 2. 全功能（含 Claude 在线）

```bash
# 1) 安装依赖并启动（首次会自动 npm install）
./start.sh                 # 访问 http://localhost:8787

# 2) 启用真实 Claude（可选）
cd server
cp .env.example .env
#   编辑 .env 填入 ANTHROPIC_API_KEY=sk-ant-...
./start.sh                 # 重启后，前端开关切到 “Claude” 即生效
```

健康检查：`curl localhost:8787/api/health` → `{"ok":true,"providers":{...}}`

## 2.5 接入本地部署大模型（私有化 / 离线）

适用于数据不出内网的场景。任意 **OpenAI 兼容** 端点均可。

**方式 A：前端 ⚙ 设置（无需重启）**
1. 启动本地模型服务（示例见下表）。
2. 页面右上角 AI 来源切到 **本地大模型** → 点 **⚙** → 填 Base URL / 模型名 → **保存** → **连通测试**。

**方式 B：后端 .env（统一管理）** 在 `server/.env` 设 `LOCAL_LLM_BASE_URL` / `LOCAL_LLM_MODEL`。

| 本地模型服务 | Base URL | 备注 |
|---|---|---|
| **Ollama** | `http://localhost:11434/v1` | `ollama run qwen2.5:7b-instruct`；浏览器直连需 `OLLAMA_ORIGINS=*` |
| **LM Studio** | `http://localhost:1234/v1` | 在 GUI 中 Start Server |
| **vLLM** | `http://localhost:8000/v1` | `vllm serve <model>` |
| **llama.cpp** | `http://localhost:8080/v1` | `llama-server -m model.gguf` |

> 路由优先级：**经本地后端代理**（推荐，规避 CORS）→ 失败则**浏览器直连** → 再失败回退本地推理。
> 工具调用兼容性：支持原生 function-calling 的模型直接用；不支持的模型由助手解析 ` ```action {json}``` ` 动作块，同样能操作页面。

---

## 3. Demo 演示脚本（建议 3 分钟）

1. **空场景**：打开页面，左侧未填。点右侧 **💡建议** —— 助手列出缺失项并**一键修正表单**（自动填 Wafer ID、按你的习惯选 Fab、勾选分析维度）。
2. **一键一生**：点 **🚀 提交「一键一生」**（或左下"一键示例"）。中栏瞬间还原该晶圆**全链路**：根因候选、晶圆 Bin 图、良率/WAT 趋势、缺陷 Pareto、工艺流程时间轴。助手**自动伴读**。
3. **分析**：点 **🔍分析** —— 助手输出按关联度排序的根因（如"中心聚集→CMP-02，置信度 86%"），并**自动高亮根因面板**。
4. **追问**：在输入框问"为什么怀疑这台设备？""带我看晶圆图" —— 助手**滚动定位并高亮**对应面板。
5. **习惯学习**：点 **🧠** 查看习惯画像（常用 Fab/节点/维度、经验等级随提交次数升级）。多操作几次后再点"💡建议 → 用我的习惯填"，体会个性化默认值。
6. **切换 AI 来源**：右上下拉切到 **本地大模型**（先 ⚙ 配好端点）或 **Claude 在线**，重复 2–4，对比真实大模型的措辞与工具决策。三种来源都会真正操作页面。

> 布局说明：页面采用**两阶段**——**配置阶段**左侧为 ①场景→②维度→③呈现→④提交 的逐步向导，主区域为引导态；**结果阶段**左侧自动折叠为配置摘要（可"重新配置/重新运行"），主区域专注呈现结果。顶栏有阶段指示。

> 演示亮点话术：
> - "AI 不是贴在旁边的聊天框，而是**真的会读这个页面、会动手填表和提交**。"
> - "它给的根因是**领域自洽**的：缺陷空间形态决定怀疑哪个工艺环节。"
> - "它**记住你的习惯**——用得越多，默认值越贴合你。"

---

## 4. 部署到服务器 / 容器

**静态托管**（Nginx / 对象存储）：直接发布 `web/` 目录即可（纯本地推理）。

**全功能容器**（示例 Dockerfile）：

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY web ./web
COPY server ./server
RUN cd server && npm install --omit=dev
ENV PORT=8787
EXPOSE 8787
CMD ["node", "server/server.js"]
# 运行：docker run -e ANTHROPIC_API_KEY=sk-ant-... -p 8787:8787 <image>
```

前后端分离时，在 `web/index.html` 把 `window.AI_BACKEND` 改为后端地址，并在后端开启 CORS。

---

## 5. 接入真实数据

`web/js/data/mockData.js` 的 `generateLifecycle()` 返回结构即"契约"。把它替换为从 MES/YMS/EDA 拉取的真实晶圆一生数据（保持同样字段：`meta / summary / waferMap / processFlow / watTrend / yieldTrend / defectPareto`），其余可视化、AI 上下文、根因打分均**无需改动**。

---

## 6. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 图表空白 | 需联网加载 ECharts CDN；离线时把 echarts.min.js 下载到本地并改 `<script src>` |
| 切到 Claude 无反应/报回退 | 后端未配 `ANTHROPIC_API_KEY` 或未启动；助手会**自动回退本地推理**并提示 |
| `./start.sh` 权限 | `chmod +x start.sh` |
| 习惯不持久 | 浏览器隐私模式禁用了 localStorage；正常窗口即可 |
