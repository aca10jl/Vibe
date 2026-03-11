"""
报告生成器：将分析结果输出为结构化的 Markdown / JSON 报告。

输出内容：
- 错误总览统计
- 时间线（按时间排列的错误事件）
- 每个错误的详细信息：描述、上下文、根因分析建议、优化建议
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from .scanner import ErrorMatch


def generate_markdown_report(
    matches: list[ErrorMatch],
    output_path: Optional[str] = None,
    title: str = "日志分析报告",
    llm_analysis: Optional[dict] = None,
) -> str:
    """生成 Markdown 格式的分析报告"""
    lines = []

    # 标题
    lines.append(f"# {title}")
    lines.append(f"")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**错误总数**: {len(matches)}")
    lines.append("")

    if not matches:
        lines.append("未检测到匹配的错误。")
        report = "\n".join(lines)
        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
        return report

    # ── 统计总览 ──
    lines.append("## 统计总览")
    lines.append("")

    # 按严重程度统计
    severity_counts = Counter(m.rule.severity for m in matches)
    lines.append("### 按严重程度")
    lines.append("")
    lines.append("| 严重程度 | 数量 |")
    lines.append("|----------|------|")
    for sev in ["FATAL", "ERROR", "WARN", "INFO"]:
        if sev in severity_counts:
            lines.append(f"| {sev} | {severity_counts[sev]} |")
    lines.append("")

    # 按分类统计
    category_counts = Counter(m.rule.category for m in matches)
    lines.append("### 按分类")
    lines.append("")
    lines.append("| 分类 | 数量 |")
    lines.append("|------|------|")
    for cat, cnt in category_counts.most_common():
        lines.append(f"| {cat} | {cnt} |")
    lines.append("")

    # 按文件统计
    file_counts = Counter(m.file_path for m in matches)
    lines.append("### 按文件")
    lines.append("")
    lines.append("| 文件 | 错误数 |")
    lines.append("|------|--------|")
    for fp, cnt in file_counts.most_common():
        lines.append(f"| `{Path(fp).name}` | {cnt} |")
    lines.append("")

    # ── 错误时间线 ──
    lines.append("## 错误时间线")
    lines.append("")

    timestamped = [m for m in matches if m.timestamp]
    no_timestamp = [m for m in matches if not m.timestamp]

    if timestamped:
        lines.append("| 时间 | 严重程度 | 分类 | 文件:行号 | 描述 |")
        lines.append("|------|----------|------|-----------|------|")
        for m in timestamped:
            ts = m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            desc = m.rule.description or m.matched_text[:50]
            fname = Path(m.file_path).name
            lines.append(f"| {ts} | {m.rule.severity} | {m.rule.category} | `{fname}:{m.line_number}` | {desc} |")
        lines.append("")

    if no_timestamp:
        lines.append("### 无时间戳的错误")
        lines.append("")
        lines.append("| 文件:行号 | 严重程度 | 分类 | 描述 |")
        lines.append("|-----------|----------|------|------|")
        for m in no_timestamp:
            desc = m.rule.description or m.matched_text[:50]
            fname = Path(m.file_path).name
            lines.append(f"| `{fname}:{m.line_number}` | {m.rule.severity} | {m.rule.category} | {desc} |")
        lines.append("")

    # ── 错误详情 ──
    lines.append("## 错误详情")
    lines.append("")

    for idx, m in enumerate(matches, start=1):
        fname = Path(m.file_path).name
        desc = m.rule.description or "未知错误"
        ts_str = m.timestamp.strftime("%Y-%m-%d %H:%M:%S") if m.timestamp else "N/A"

        lines.append(f"### {idx}. [{m.rule.severity}] {desc}")
        lines.append("")
        lines.append(f"- **文件**: `{fname}:{m.line_number}`")
        lines.append(f"- **时间**: {ts_str}")
        lines.append(f"- **匹配规则**: `{m.rule.pattern_str}`")
        lines.append(f"- **匹配内容**: `{m.matched_text}`")
        lines.append(f"- **分类**: {m.rule.category}")
        lines.append("")

        # 上下文
        lines.append("<details>")
        lines.append(f"<summary>上下文日志（前后 {len(m.context_before)}+{len(m.context_after)} 行）</summary>")
        lines.append("")
        lines.append("```")
        for cl in m.context_before:
            lines.append(f"  {cl}")
        lines.append(f">> {m.line_content}")
        for cl in m.context_after:
            lines.append(f"  {cl}")
        lines.append("```")
        lines.append("</details>")
        lines.append("")

        # LLM 分析结果（如果有）
        if llm_analysis and str(idx) in llm_analysis:
            analysis = llm_analysis[str(idx)]
            if analysis.get("root_cause"):
                lines.append(f"**根因分析**: {analysis['root_cause']}")
                lines.append("")
            if analysis.get("suggestion"):
                lines.append(f"**优化建议**: {analysis['suggestion']}")
                lines.append("")

        lines.append("---")
        lines.append("")

    # ── 总结建议 ──
    lines.append("## 总结与建议")
    lines.append("")

    # 按优先级列出
    fatal_matches = [m for m in matches if m.rule.severity == "FATAL"]
    error_matches = [m for m in matches if m.rule.severity == "ERROR"]

    if fatal_matches:
        lines.append("### 需要立即处理 (FATAL)")
        lines.append("")
        for m in fatal_matches:
            desc = m.rule.description or m.matched_text[:80]
            lines.append(f"- `{Path(m.file_path).name}:{m.line_number}` - {desc}")
        lines.append("")

    if error_matches:
        lines.append("### 需要关注 (ERROR)")
        lines.append("")
        # 按分类分组
        from collections import defaultdict
        by_cat = defaultdict(list)
        for m in error_matches:
            by_cat[m.rule.category].append(m)
        for cat, ms in by_cat.items():
            lines.append(f"- **{cat}**: {len(ms)} 个错误")
            for m in ms[:5]:  # 每类最多显示5个
                desc = m.rule.description or m.matched_text[:60]
                lines.append(f"  - `{Path(m.file_path).name}:{m.line_number}` - {desc}")
            if len(ms) > 5:
                lines.append(f"  - ... 及其他 {len(ms) - 5} 个")
        lines.append("")

    if llm_analysis and "summary" in llm_analysis:
        lines.append("### AI 分析总结")
        lines.append("")
        lines.append(llm_analysis["summary"])
        lines.append("")

    report = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(report, encoding="utf-8")

    return report


def generate_json_report(
    matches: list[ErrorMatch],
    output_path: Optional[str] = None,
) -> dict:
    """生成 JSON 格式的结构化报告"""
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_errors": len(matches),
        "severity_summary": dict(Counter(m.rule.severity for m in matches)),
        "category_summary": dict(Counter(m.rule.category for m in matches)),
        "errors": [m.to_dict() for m in matches],
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return data
