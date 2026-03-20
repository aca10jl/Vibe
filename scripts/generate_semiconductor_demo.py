#!/usr/bin/env python3
"""Generate a semiconductor yield root-cause analysis demo with synthetic data and SVG wafer maps."""

from __future__ import annotations

import csv
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo_output"
IMG = OUT / "images"
DATA = OUT / "data"

GRID_SIZE = 33
CENTER = (GRID_SIZE - 1) / 2
RADIUS = GRID_SIZE * 0.45
DIE_PITCH = 18
MARGIN = 45
SEED = 20260320

PATTERN_COLORS = {
    "pass": "#7dd3fc",
    "edge_ring": "#ef4444",
    "top_right_cluster": "#f97316",
    "scratch_diagonal": "#a855f7",
    "center_hotspot": "#eab308",
    "random": "#94a3b8",
}

SCENARIOS = [
    {
        "lot": "LOT-A",
        "phase": "改善前",
        "wafer_id": "W01",
        "product": "28nm MCU",
        "tool": "ETCH-07",
        "chamber": "A",
        "process_step": "Plasma Etch",
        "pattern": "edge_ring",
        "root_cause": "边缘环形失效，怀疑静电卡盘温控漂移与边缘等离子体不均匀",
        "action": "校准 ESC 温区并复核边缘 gas flow",
    },
    {
        "lot": "LOT-A",
        "phase": "改善前",
        "wafer_id": "W02",
        "product": "28nm MCU",
        "tool": "ETCH-07",
        "chamber": "A",
        "process_step": "Plasma Etch",
        "pattern": "edge_ring",
        "root_cause": "边缘环形失效，怀疑静电卡盘温控漂移与边缘等离子体不均匀",
        "action": "校准 ESC 温区并复核边缘 gas flow",
    },
    {
        "lot": "LOT-A",
        "phase": "改善前",
        "wafer_id": "W03",
        "product": "28nm MCU",
        "tool": "ETCH-07",
        "chamber": "B",
        "process_step": "Plasma Etch",
        "pattern": "top_right_cluster",
        "root_cause": "右上局部簇状失效，怀疑 chamber B 粒子污染",
        "action": "执行 chamber PM 与 particle clean",
    },
    {
        "lot": "LOT-A",
        "phase": "改善前",
        "wafer_id": "W04",
        "product": "28nm MCU",
        "tool": "ETCH-07",
        "chamber": "B",
        "process_step": "Plasma Etch",
        "pattern": "top_right_cluster",
        "root_cause": "右上局部簇状失效，怀疑 chamber B 粒子污染",
        "action": "执行 chamber PM 与 particle clean",
    },
    {
        "lot": "LOT-A",
        "phase": "改善前",
        "wafer_id": "W05",
        "product": "28nm MCU",
        "tool": "CMP-03",
        "chamber": "-",
        "process_step": "CMP",
        "pattern": "scratch_diagonal",
        "root_cause": "对角线刮伤，怀疑机械手搬运路径与 pad condition 异常",
        "action": "检查机械手轨迹并更换 pad",
    },
    {
        "lot": "LOT-A",
        "phase": "改善前",
        "wafer_id": "W06",
        "product": "28nm MCU",
        "tool": "LITHO-02",
        "chamber": "-",
        "process_step": "Lithography",
        "pattern": "center_hotspot",
        "root_cause": "中心热点失效，怀疑 focus map 偏差",
        "action": "重跑 focus/exposure matrix",
    },
    {
        "lot": "LOT-B",
        "phase": "改善后",
        "wafer_id": "W07",
        "product": "28nm MCU",
        "tool": "ETCH-07",
        "chamber": "A",
        "process_step": "Plasma Etch",
        "pattern": "improved_edge_ring",
        "root_cause": "已完成 ESC 调校，边缘失效显著收敛",
        "action": "维持每周 ESC drift monitor",
    },
    {
        "lot": "LOT-B",
        "phase": "改善后",
        "wafer_id": "W08",
        "product": "28nm MCU",
        "tool": "ETCH-07",
        "chamber": "B",
        "process_step": "Plasma Etch",
        "pattern": "improved_cluster",
        "root_cause": "已完成 PM，局部粒子 cluster 显著减少",
        "action": "维持 particle SPC 门限",
    },
    {
        "lot": "LOT-B",
        "phase": "改善后",
        "wafer_id": "W09",
        "product": "28nm MCU",
        "tool": "CMP-03",
        "chamber": "-",
        "process_step": "CMP",
        "pattern": "improved_scratch",
        "root_cause": "机械手路径修复后仅剩零星随机失效",
        "action": "持续监控机械手 repeatability",
    },
    {
        "lot": "LOT-B",
        "phase": "改善后",
        "wafer_id": "W10",
        "product": "28nm MCU",
        "tool": "LITHO-02",
        "chamber": "-",
        "process_step": "Lithography",
        "pattern": "improved_center",
        "root_cause": "曝光聚焦重校后中心热点消失",
        "action": "保留 focus map 自动校验",
    },
]


def die_positions():
    points = []
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            dx = x - CENTER
            dy = y - CENTER
            if math.hypot(dx, dy) <= RADIUS:
                points.append((x, y, dx, dy))
    return points


POSITIONS = die_positions()


def fail_reason(pattern: str, dx: float, dy: float, rng: random.Random) -> str:
    r = math.hypot(dx, dy) / RADIUS
    if pattern == "edge_ring":
        if r > 0.82 and rng.random() < 0.72:
            return "edge_ring"
        if 0.74 < r <= 0.82 and rng.random() < 0.24:
            return "edge_ring"
    elif pattern == "top_right_cluster":
        if dx > 3 and dy < -3:
            cluster_strength = max(0.0, 1.0 - ((dx - 8) ** 2 + (dy + 8) ** 2) / 90)
            if rng.random() < 0.18 + 0.65 * cluster_strength:
                return "top_right_cluster"
        if dx > 6 and dy < -6 and rng.random() < 0.12:
            return "top_right_cluster"
    elif pattern == "scratch_diagonal":
        distance = abs(dy - (0.9 * dx + 1.5)) / math.sqrt(1 + 0.9 ** 2)
        if distance < 0.95 and rng.random() < 0.82:
            return "scratch_diagonal"
        if distance < 1.65 and rng.random() < 0.28:
            return "scratch_diagonal"
    elif pattern == "center_hotspot":
        if math.hypot(dx, dy) < 5.5 and rng.random() < 0.58:
            return "center_hotspot"
        if math.hypot(dx, dy) < 7.0 and rng.random() < 0.12:
            return "center_hotspot"
    elif pattern == "improved_edge_ring":
        if r > 0.86 and rng.random() < 0.12:
            return "edge_ring"
    elif pattern == "improved_cluster":
        if dx > 4 and dy < -4:
            cluster_strength = max(0.0, 1.0 - ((dx - 8) ** 2 + (dy + 8) ** 2) / 100)
            if rng.random() < 0.05 + 0.15 * cluster_strength:
                return "top_right_cluster"
    elif pattern == "improved_scratch":
        distance = abs(dy - (0.9 * dx + 1.5)) / math.sqrt(1 + 0.9 ** 2)
        if distance < 0.9 and rng.random() < 0.08:
            return "scratch_diagonal"
    elif pattern == "improved_center":
        if math.hypot(dx, dy) < 4.0 and rng.random() < 0.06:
            return "center_hotspot"

    random_fail = 0.008 if pattern.startswith("improved_") else 0.015
    if rng.random() < random_fail:
        return "random"
    return "pass"



def generate_rows():
    rng = random.Random(SEED)
    rows = []
    wafer_summaries = []
    for scenario in SCENARIOS:
        wafer_counter = Counter()
        for x, y, dx, dy in POSITIONS:
            reason = fail_reason(scenario["pattern"], dx, dy, rng)
            passed = int(reason == "pass")
            wafer_counter[reason] += 1
            rows.append(
                {
                    **scenario,
                    "die_x": x,
                    "die_y": y,
                    "die_dx": round(dx, 2),
                    "die_dy": round(dy, 2),
                    "status": "PASS" if passed else "FAIL",
                    "fail_reason": reason,
                }
            )
        total_die = sum(wafer_counter.values())
        good_die = wafer_counter["pass"]
        yield_pct = good_die / total_die * 100
        wafer_summaries.append(
            {
                **scenario,
                "total_die": total_die,
                "good_die": good_die,
                "yield_pct": round(yield_pct, 2),
                "edge_ring_fail": wafer_counter["edge_ring"],
                "cluster_fail": wafer_counter["top_right_cluster"],
                "scratch_fail": wafer_counter["scratch_diagonal"],
                "center_fail": wafer_counter["center_hotspot"],
                "random_fail": wafer_counter["random"],
            }
        )
    return rows, wafer_summaries



def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text{font-family:Arial,"Noto Sans SC",sans-serif;} .small{font-size:12px;} .label{font-size:16px;font-weight:700;} .title{font-size:24px;font-weight:700;} .subtitle{font-size:14px;fill:#334155;} </style>',
    ]



def write_text(lines: list[str], x: int, y: int, text: str, cls: str = "small", fill: str = "#0f172a"):
    safe = text.replace("&", "&amp;").replace("<", "&lt;")
    lines.append(f'<text x="{x}" y="{y}" class="{cls}" fill="{fill}">{safe}</text>')



def render_wafer_map(wafer_summary: dict, die_rows: list[dict], filename: Path):
    width = MARGIN * 2 + GRID_SIZE * DIE_PITCH + 220
    height = MARGIN * 2 + GRID_SIZE * DIE_PITCH
    lines = svg_header(width, height)
    map_left = MARGIN
    map_top = MARGIN
    wafer_radius_px = RADIUS * DIE_PITCH
    center_px = map_left + CENTER * DIE_PITCH
    center_py = map_top + CENTER * DIE_PITCH
    lines.append('<rect width="100%" height="100%" fill="#f8fafc"/>')
    lines.append(f'<circle cx="{center_px}" cy="{center_py}" r="{wafer_radius_px + 16}" fill="#e2e8f0" stroke="#94a3b8" stroke-width="2"/>')
    notch_x = center_px
    notch_y = center_py + wafer_radius_px + 16
    lines.append(f'<rect x="{notch_x - 24}" y="{notch_y - 6}" width="48" height="14" rx="4" fill="#cbd5e1"/>')
    for row in die_rows:
        x = map_left + row["die_x"] * DIE_PITCH - 7
        y = map_top + row["die_y"] * DIE_PITCH - 7
        fill = PATTERN_COLORS[row["fail_reason"]]
        stroke = "#ffffff" if row["status"] == "PASS" else "#111827"
        lines.append(f'<rect x="{x}" y="{y}" width="14" height="14" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="0.8"/>')

    write_text(lines, 24, 28, f'{wafer_summary["phase"]} - {wafer_summary["wafer_id"]} ({wafer_summary["process_step"]})', "title")
    write_text(lines, 24, 50, f'Tool {wafer_summary["tool"]} / Chamber {wafer_summary["chamber"]} / Yield {wafer_summary["yield_pct"]:.2f}% ', "subtitle")
    write_text(lines, width - 195, 70, '图例 Legend', 'label')
    legend_items = [
        ("pass", "Pass"),
        ("edge_ring", "边缘环形异常"),
        ("top_right_cluster", "右上 cluster"),
        ("scratch_diagonal", "对角刮伤"),
        ("center_hotspot", "中心热点"),
        ("random", "随机零星失效"),
    ]
    y0 = 100
    for key, label in legend_items:
        lines.append(f'<rect x="{width - 190}" y="{y0 - 12}" width="16" height="16" rx="3" fill="{PATTERN_COLORS[key]}" stroke="#0f172a" stroke-width="0.6"/>')
        write_text(lines, width - 165, y0, label)
        y0 += 28

    write_text(lines, width - 195, y0 + 10, '根因判断', 'label')
    for idx, chunk in enumerate(split_text(wafer_summary["root_cause"], 16)):
        write_text(lines, width - 190, y0 + 36 + idx * 18, chunk)
    write_text(lines, width - 195, y0 + 96, '建议动作', 'label')
    for idx, chunk in enumerate(split_text(wafer_summary["action"], 16)):
        write_text(lines, width - 190, y0 + 122 + idx * 18, chunk)

    lines.append('</svg>')
    filename.write_text("\n".join(lines), encoding="utf-8")



def split_text(text: str, width: int):
    return [text[i : i + width] for i in range(0, len(text), width)]



def render_bar_chart(before_counter: Counter, after_counter: Counter, filename: Path):
    width, height = 1000, 520
    lines = svg_header(width, height)
    lines.append('<rect width="100%" height="100%" fill="#f8fafc"/>')
    write_text(lines, 28, 34, '改善前后缺陷构成对比', 'title')
    write_text(lines, 28, 58, '用于说明智能体如何把零散失效图样归并成可执行的根因优先级。', 'subtitle')

    categories = [
        ("edge_ring", "边缘环形"),
        ("top_right_cluster", "右上 cluster"),
        ("scratch_diagonal", "对角刮伤"),
        ("center_hotspot", "中心热点"),
        ("random", "随机失效"),
    ]
    max_val = max(max(before_counter.values()), max(after_counter.values()))
    chart_left, chart_bottom = 100, 440
    group_gap, bar_w = 150, 36
    chart_height = 300
    lines.append(f'<line x1="{chart_left}" y1="120" x2="{chart_left}" y2="{chart_bottom}" stroke="#475569" stroke-width="2"/>')
    lines.append(f'<line x1="{chart_left}" y1="{chart_bottom}" x2="900" y2="{chart_bottom}" stroke="#475569" stroke-width="2"/>')
    for i in range(0, max_val + 1, max(10, math.ceil(max_val / 6 / 10) * 10)):
        y = chart_bottom - chart_height * (i / max_val)
        lines.append(f'<line x1="{chart_left}" y1="{y}" x2="900" y2="{y}" stroke="#cbd5e1" stroke-width="1"/>')
        write_text(lines, 56, int(y + 4), str(i))

    start_x = 160
    for idx, (key, label) in enumerate(categories):
        x = start_x + idx * group_gap
        before_h = chart_height * (before_counter[key] / max_val)
        after_h = chart_height * (after_counter[key] / max_val)
        lines.append(f'<rect x="{x}" y="{chart_bottom - before_h}" width="{bar_w}" height="{before_h}" fill="#ef4444" rx="4"/>')
        lines.append(f'<rect x="{x + bar_w + 10}" y="{chart_bottom - after_h}" width="{bar_w}" height="{after_h}" fill="#22c55e" rx="4"/>')
        write_text(lines, x - 4, 470, label)
        write_text(lines, x, int(chart_bottom - before_h - 8), str(before_counter[key]))
        write_text(lines, x + bar_w + 10, int(chart_bottom - after_h - 8), str(after_counter[key]))

    lines.append('<rect x="760" y="82" width="18" height="18" fill="#ef4444" rx="3"/>')
    write_text(lines, 786, 96, '改善前')
    lines.append('<rect x="840" y="82" width="18" height="18" fill="#22c55e" rx="3"/>')
    write_text(lines, 866, 96, '改善后')
    lines.append('</svg>')
    filename.write_text("\n".join(lines), encoding="utf-8")



def render_trend_chart(wafer_summaries: list[dict], filename: Path):
    width, height = 1000, 520
    lines = svg_header(width, height)
    lines.append('<rect width="100%" height="100%" fill="#f8fafc"/>')
    write_text(lines, 28, 34, 'Wafer Yield 趋势图', 'title')
    write_text(lines, 28, 58, '改善动作执行后，wafer-level yield 从多点失控转向稳定收敛。', 'subtitle')

    chart_left, chart_bottom, chart_top = 100, 430, 110
    chart_right = 920
    lines.append(f'<line x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_bottom}" stroke="#475569" stroke-width="2"/>')
    lines.append(f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" stroke="#475569" stroke-width="2"/>')
    y_min, y_max = 70, 100
    for value in range(70, 101, 5):
        y = chart_bottom - (value - y_min) / (y_max - y_min) * (chart_bottom - chart_top)
        lines.append(f'<line x1="{chart_left}" y1="{y}" x2="{chart_right}" y2="{y}" stroke="#cbd5e1" stroke-width="1"/>')
        write_text(lines, 54, int(y + 4), f'{value}%')

    step = (chart_right - chart_left - 40) / (len(wafer_summaries) - 1)
    points = []
    for idx, summary in enumerate(wafer_summaries):
        x = chart_left + 20 + idx * step
        y = chart_bottom - (summary["yield_pct"] - y_min) / (y_max - y_min) * (chart_bottom - chart_top)
        points.append((x, y, summary))
        write_text(lines, int(x - 12), 455, summary["wafer_id"])
    polyline = " ".join(f'{x},{y}' for x, y, _ in points)
    lines.append(f'<polyline fill="none" stroke="#2563eb" stroke-width="4" points="{polyline}"/>')
    for x, y, summary in points:
        color = "#ef4444" if summary["phase"] == "改善前" else "#22c55e"
        lines.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}" stroke="#0f172a" stroke-width="1"/>')
        write_text(lines, int(x - 16), int(y - 12), f'{summary["yield_pct"]:.1f}%')
    lines.append('<rect x="760" y="82" width="18" height="18" fill="#ef4444" rx="3"/>')
    write_text(lines, 786, 96, '改善前 wafer')
    lines.append('<rect x="840" y="82" width="18" height="18" fill="#22c55e" rx="3"/>')
    write_text(lines, 866, 96, '改善后 wafer')
    lines.append('</svg>')
    filename.write_text("\n".join(lines), encoding="utf-8")



def build_report(wafer_summaries: list[dict], before_counter: Counter, after_counter: Counter):
    before_yields = [w["yield_pct"] for w in wafer_summaries if w["phase"] == "改善前"]
    after_yields = [w["yield_pct"] for w in wafer_summaries if w["phase"] == "改善后"]
    best_gain = round(statistics.mean(after_yields) - statistics.mean(before_yields), 2)
    before_sigma = round(statistics.pstdev(before_yields), 2)
    after_sigma = round(statistics.pstdev(after_yields), 2)

    report = ROOT / "README.md"
    lines = [
        "# 半导体良率根因分析智能体 Demo",
        "",
        "这个 demo 面向**长期深耕半导体制造、但对 AI / 大模型 / 智能体不熟悉的管理者**，用合成数据演示智能体如何从 wafer map 图样中识别根因、给出改善动作，并量化良率提升。",
        "",
        "## 1. Demo 想传达的核心价值",
        "",
        "- **自动化**：自动汇总 MES、设备、缺陷、wafer map 等多源数据，减少工程师人工翻图与做 PPT 的时间。",
        "- **智能化**：将 ring、cluster、scratch、center hotspot 等典型图样自动归类，并关联可能的设备/工艺原因。",
        "- **可执行**：不仅告诉你“哪里坏了”，还输出“先做什么动作、预期能提升多少良率”。",
        "- **可管理**：把零散的工程问题转换成管理层容易理解的三件事：问题规模、优先级、改善收益。",
        "",
        "## 2. 合成数据说明",
        "",
        "- 产品：28nm MCU。",
        "- 对象：10 片 wafer，其中 6 片为改善前、4 片为改善后。",
        "- Die 数量：每片 697 颗有效 die（按圆形 wafer 区域近似生成）。",
        "- 典型失效图样：边缘环形异常、右上 cluster、对角刮伤、中心热点、随机零星失效。",
        "- 主要目的：用于汇报演示，不代表真实 fab 数据。",
        "",
        "## 3. 关键结论（适合汇报时先讲）",
        "",
        f"- 改善前平均良率约 **{statistics.mean(before_yields):.2f}%**，改善后提升到 **{statistics.mean(after_yields):.2f}%**，平均提升 **{best_gain:.2f} 个百分点**。",
        f"- 良率波动（sigma）从 **{before_sigma}** 收敛到 **{after_sigma}**，说明不只是均值提升，稳定性也更好。",
        f"- 主要损失来源从边缘 ring 与局部 cluster，转为少量随机失效；这说明关键系统性问题已被压制。",
        "- 这类任务很适合做成智能体：输入 wafer map + 设备/工艺上下文，输出根因优先级、建议动作、预估收益。",
        "",
        "## 4. 代表性 Wafer Map",
        "",
        "### 4.1 改善前：边缘 ring 异常（疑似 ESC 温控 / 边缘 plasma 不均）",
        "",
        "![W01 wafer map](demo_output/images/wafer_W01.svg)",
        "",
        "### 4.2 改善前：右上局部 cluster（疑似 chamber particle）",
        "",
        "![W03 wafer map](demo_output/images/wafer_W03.svg)",
        "",
        "### 4.3 改善前：对角刮伤（疑似机械手 / pad condition）",
        "",
        "![W05 wafer map](demo_output/images/wafer_W05.svg)",
        "",
        "### 4.4 改善前：中心 hotspot（疑似 litho focus map 偏移）",
        "",
        "![W06 wafer map](demo_output/images/wafer_W06.svg)",
        "",
        "### 4.5 改善后：边缘 ring 明显收敛",
        "",
        "![W07 wafer map](demo_output/images/wafer_W07.svg)",
        "",
        "### 4.6 改善后：cluster 仅剩零星分布",
        "",
        "![W08 wafer map](demo_output/images/wafer_W08.svg)",
        "",
        "## 5. 对比图",
        "",
        "### 5.1 缺陷构成对比",
        "",
        "![Pareto-like comparison](demo_output/images/defect_comparison.svg)",
        "",
        "### 5.2 Yield 趋势",
        "",
        "![Yield trend](demo_output/images/yield_trend.svg)",
        "",
        "## 6. 对比分析（可以直接讲给领导听）",
        "",
        "### 6.1 改善前发生了什么",
        "",
        "- **W01 / W02** 出现明显边缘 ring，说明问题不像随机波动，更像是设备状态或工艺窗口系统性偏移。",
        "- **W03 / W04** 右上 cluster 反复出现，而且集中在同一 chamber，说明可以优先排查粒子污染而不是到处撒网。",
        "- **W05** 的对角线失效很像机械伤或 pad-related 轨迹问题，属于典型模式识别能快速定位的问题。",
        "- **W06** 中心热点说明 litho focus/exposure 的空间分布失衡，不是简单单点参数漂移。",
        "",
        "### 6.2 智能体能怎么做",
        "",
        "1. 自动读取 wafer map，并识别图样属于 ring / cluster / scratch / hotspot 中哪一类。",
        "2. 自动拉取对应 lot 的工艺履历、tool/chamber、SPC、FDC 告警和 PM 记录。",
        "3. 根据历史案例库给出**根因优先级列表**，例如：ESC 温控漂移 > particle 污染 > 机械手路径异常。",
        "4. 生成工程建议：先校准什么、先 clean 哪台机、先看哪一个 SPC 指标。",
        "5. 估算收益：若优先处理前两大根因，平均良率可从 80%+ 提升到 95%+。",
        "",
        "### 6.3 管理层能看到的价值",
        "",
        "- 以前：工程师靠经验看图、拉数据、开会讨论，往往要几小时到几天。",
        "- 以后：智能体几分钟内形成首版结论，工程师重点变成确认与执行。",
        "- 对领导的意义不是“替代工程师”，而是让优秀工程经验可复制、可沉淀、可规模化。",
        "",
        "## 7. 建议你汇报时的讲法",
        "",
        "可以按下面这 4 句话展开：",
        "",
        "1. **第一句话：** 智能体不是一个聊天机器人，而是一个会自动看 wafer map、查设备履历、给出改善建议的数字工程师助理。",
        "2. **第二句话：** 它最适合先做高频、重复、依赖经验的环节，比如良率根因分析。",
        "3. **第三句话：** 这个 demo 展示了它能把几个典型图样快速归因，并把良率从 80%+ 拉升到 95%+。",
        "4. **第四句话：** 真正落地后，它会沉淀成企业自己的工程知识系统，而不是一次性工具。",
        "",
        "## 8. 文件说明",
        "",
        "- `scripts/generate_semiconductor_demo.py`：生成合成数据、wafer map 和对比图。",
        "- `demo_output/data/wafer_die_data.csv`：die-level 合成数据。",
        "- `demo_output/data/wafer_summary.csv`：wafer-level 汇总数据。",
        "- `demo_output/images/*.svg`：可直接插入汇报材料的图。",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")



def main():
    IMG.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    rows, wafer_summaries = generate_rows()

    write_csv(DATA / "wafer_die_data.csv", rows, list(rows[0].keys()))
    write_csv(DATA / "wafer_summary.csv", wafer_summaries, list(wafer_summaries[0].keys()))

    rows_by_wafer = defaultdict(list)
    for row in rows:
        rows_by_wafer[row["wafer_id"]].append(row)

    for summary in wafer_summaries:
        render_wafer_map(summary, rows_by_wafer[summary["wafer_id"]], IMG / f'wafer_{summary["wafer_id"]}.svg')

    before_counter = Counter()
    after_counter = Counter()
    for row in rows:
        if row["fail_reason"] == "pass":
            continue
        if row["phase"] == "改善前":
            before_counter[row["fail_reason"]] += 1
        else:
            after_counter[row["fail_reason"]] += 1

    render_bar_chart(before_counter, after_counter, IMG / "defect_comparison.svg")
    render_trend_chart(wafer_summaries, IMG / "yield_trend.svg")
    build_report(wafer_summaries, before_counter, after_counter)

    print(f'Generated {len(wafer_summaries)} wafer summaries, {len(rows)} die rows.')
    print(f'Output written to: {OUT}')


if __name__ == "__main__":
    main()
