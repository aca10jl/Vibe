# 方案演示 PPT（精简版 · 含 Demo 实拍）

面向团队的图解提案，用于说服将 **AI 伴读助手** 集成进现有「一键一生」框架。

- **`一键一生-AI助手-方案.pptx`** — 可直接放映/编辑（16:9，**10 页**，深色主题，内嵌 3 张 Demo 实拍）。PowerPoint / WPS / Keynote / Google Slides 打开。
- **`make_pptx.py`** — PPT 生成脚本（`pip install python-pptx && python3 make_pptx.py`）。
- **`shoot.mjs`** — 用 Playwright 截取 Demo 页面的脚本，输出到 `shots/`。
- **`shots/`** — Demo 截图（配置 / 结果+分析 / 三来源）。

## 目录（10 页）

| 页 | 主题 |
|---|---|
| 01 | 封面 |
| 02 | 背景与痛点 → 机会 |
| 03 | 方案总览（三栏 + Agent 引擎 一图） |
| 04 | 核心能力：伴读/分析/建议 + 会动手 + 学习习惯 |
| 05 | **Demo 实拍**：配置阶段（逐步向导 + AI 伴读） |
| 06 | **Demo 实拍**：全链路结果 + AI 根因分析 |
| 07 | **Demo 实拍**：三种 AI 来源 · 私有化 |
| 08 | 集成方式（3 步 + 数据契约）+ 私有化合规 |
| 09 | 集成前 vs 集成后（价值对比） |
| 10 | 路线图 + 行动号召（CTA） |

## 重新生成截图（可选）

```bash
# 1) 本地起静态服务
cd web && python3 -m http.server 8805 &
# 2) 截图（需 Playwright + Chromium）
cd docs/slides
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers SHOT_URL=http://localhost:8805 \
  node shoot.mjs
# 3) 重新生成 PPT
python3 make_pptx.py
```

> 截图所用 ECharts 已本地化（`web/vendor/echarts.min.js`，CDN 不可达时自动启用），Demo 离线也能出图。
