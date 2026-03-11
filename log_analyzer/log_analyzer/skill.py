"""
OpenCode / Claude Code Skill 接口。

本模块提供了一个可被 AI 编码智能体直接调用的 Python 函数接口，
无需通过 CLI，适合作为 skill 集成到 OpenCode、Claude Code 等工具中。

使用方式（在 AI Agent 中）：
    from log_analyzer.skill import analyze_logs
    result = analyze_logs(
        log_paths=["/path/to/app.log", "/path/to/sys.log"],
        rules_path="/path/to/rules.xlsx",  # 可选
    )
    print(result["report_markdown"])
"""

from pathlib import Path
from typing import Optional

from .rule_parser import load_rules_from_excel, load_rules_from_json, BUILTIN_PATTERNS
from .scanner import LogScanner
from .report import generate_markdown_report, generate_json_report


def analyze_logs(
    log_paths: list[str],
    rules_path: Optional[str] = None,
    context_lines: int = 30,
    context_seconds: float = 5.0,
    encoding: str = "utf-8",
    max_matches_per_file: int = 500,
    ignore_patterns: Optional[list[str]] = None,
    output_format: str = "markdown",
    output_path: Optional[str] = None,
    title: str = "日志分析报告",
) -> dict:
    """
    分析日志文件，返回结构化结果。

    这是供 AI 编码智能体（OpenCode、Claude Code等）调用的主入口函数。

    参数:
        log_paths: 日志文件路径列表（支持 glob 通配符）
        rules_path: 规则文件路径（.xlsx 或 .json），为 None 则仅用内置规则
        context_lines: 每个错误前后提取的上下文行数
        context_seconds: 每个错误前后提取的时间窗口（秒）
        encoding: 日志文件编码
        max_matches_per_file: 每个文件最大匹配数
        ignore_patterns: 要忽略的正则模式列表
        output_format: "markdown" 或 "json"
        output_path: 报告保存路径（可选）
        title: 报告标题

    返回:
        dict: {
            "total_errors": int,
            "matches": list[dict],       # 结构化的错误列表
            "report_markdown": str,       # Markdown 报告（当 format=markdown）
            "report_json": dict,          # JSON 报告（当 format=json）
            "severity_summary": dict,     # 按严重程度统计
            "category_summary": dict,     # 按分类统计
        }
    """
    import glob as glob_mod
    import os
    from collections import Counter

    # 展开路径
    resolved = []
    for lp in log_paths:
        expanded = glob_mod.glob(lp, recursive=True)
        if expanded:
            resolved.extend(expanded)
        elif os.path.isdir(lp):
            for ext in ["*.log", "*.txt", "*.out", "*.err"]:
                resolved.extend(glob_mod.glob(os.path.join(lp, "**", ext), recursive=True))
    resolved = sorted(set(resolved))

    if not resolved:
        return {
            "total_errors": 0,
            "matches": [],
            "report_markdown": "未找到日志文件。",
            "severity_summary": {},
            "category_summary": {},
        }

    # 加载规则
    rules = []
    if rules_path:
        if rules_path.endswith(".json"):
            rules = load_rules_from_json(rules_path)
        else:
            rules = load_rules_from_excel(rules_path)

    # 扫描
    scanner = LogScanner(
        rules=rules,
        context_lines=context_lines,
        context_seconds=context_seconds,
        use_builtin_rules=True,
        ignore_patterns=ignore_patterns,
    )

    all_matches = scanner.scan_multiple(resolved, encoding=encoding)

    # 生成报告
    result = {
        "total_errors": len(all_matches),
        "files_scanned": resolved,
        "matches": [m.to_dict() for m in all_matches],
        "severity_summary": dict(Counter(m.rule.severity for m in all_matches)),
        "category_summary": dict(Counter(m.rule.category for m in all_matches)),
    }

    md_report = generate_markdown_report(all_matches, output_path if output_format == "markdown" else None, title=title)
    result["report_markdown"] = md_report

    if output_format == "json":
        json_report = generate_json_report(all_matches, output_path)
        result["report_json"] = json_report

    return result


# ── Skill 元信息（供 OpenCode 注册使用） ──
SKILL_METADATA = {
    "name": "log-analyzer",
    "description": "自动化日志分析工具：扫描大规模系统日志，匹配错误模式，提取上下文，生成时间线和根因分析报告",
    "version": "1.0.0",
    "author": "Vibe",
    "entry_point": "log_analyzer.skill:analyze_logs",
    "parameters": {
        "log_paths": {
            "type": "list[str]",
            "required": True,
            "description": "日志文件路径列表（支持 glob 通配符）",
        },
        "rules_path": {
            "type": "str",
            "required": False,
            "description": "规则文件路径（.xlsx 或 .json）",
        },
        "context_lines": {
            "type": "int",
            "required": False,
            "default": 30,
            "description": "上下文行数",
        },
        "output_format": {
            "type": "str",
            "required": False,
            "default": "markdown",
            "description": "输出格式: markdown | json",
        },
    },
    "examples": [
        'analyze_logs(log_paths=["/var/log/app/*.log"])',
        'analyze_logs(log_paths=["app.log"], rules_path="rules.xlsx")',
    ],
}
