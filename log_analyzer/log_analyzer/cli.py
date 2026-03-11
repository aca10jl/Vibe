"""
命令行入口 & OpenCode/Claude Code Skill 接口。

用法示例：
    # 基础用法
    python -m log_analyzer scan -l /path/to/logs/ -r rules.xlsx

    # 指定参数
    python -m log_analyzer scan -l app.log -l sys.log -r rules.xlsx \
        --context-lines 50 --context-seconds 10 --output report.md

    # 使用内置规则（不提供 Excel）
    python -m log_analyzer scan -l /path/to/logs/ --builtin-only

    # 输出 JSON
    python -m log_analyzer scan -l app.log -r rules.xlsx --format json
"""

import os
import sys
import glob as glob_mod
import json
from pathlib import Path

try:
    import click
except ImportError:
    print("请安装 click: pip install click")
    sys.exit(1)

from .rule_parser import load_rules_from_excel, load_rules_from_json, ErrorRule
from .scanner import LogScanner
from .report import generate_markdown_report, generate_json_report


@click.group()
@click.version_option(version="1.0.0")
def main():
    """日志自动化分析工具 - 问题定位、根因分析、优化建议"""
    pass


@main.command()
@click.option("-l", "--log", "log_paths", multiple=True, required=True,
              help="日志文件路径（支持 glob 通配符，可多次指定）")
@click.option("-r", "--rules", "rules_path", default=None,
              help="规则文件路径（.xlsx 或 .json）")
@click.option("--builtin-only", is_flag=True, default=False,
              help="仅使用内置规则（不需要规则文件）")
@click.option("--context-lines", default=30, show_default=True,
              help="每个错误前后提取的上下文行数")
@click.option("--context-seconds", default=5.0, show_default=True,
              help="每个错误前后提取的时间窗口（秒）")
@click.option("--encoding", default="utf-8", show_default=True,
              help="日志文件编码")
@click.option("-o", "--output", "output_path", default=None,
              help="报告输出路径（默认打印到 stdout）")
@click.option("--format", "output_format", type=click.Choice(["markdown", "json"]),
              default="markdown", show_default=True, help="输出格式")
@click.option("--max-matches", default=0, show_default=True,
              help="每个文件最大匹配数（0=无限制）")
@click.option("--ignore", "ignore_patterns", multiple=True,
              help="要忽略的正则模式（可多次指定）")
@click.option("--title", default="日志分析报告", help="报告标题")
def scan(log_paths, rules_path, builtin_only, context_lines, context_seconds,
         encoding, output_path, output_format, max_matches, ignore_patterns, title):
    """扫描日志文件，匹配错误规则，生成分析报告"""

    # 展开 glob 路径
    resolved_paths = []
    for lp in log_paths:
        expanded = glob_mod.glob(lp, recursive=True)
        if expanded:
            resolved_paths.extend(expanded)
        elif os.path.isdir(lp):
            # 如果是目录，扫描常见日志扩展名
            for ext in ["*.log", "*.txt", "*.out", "*.err"]:
                resolved_paths.extend(glob_mod.glob(os.path.join(lp, "**", ext), recursive=True))
        else:
            click.echo(f"警告: 路径不存在或无匹配: {lp}", err=True)

    if not resolved_paths:
        click.echo("错误: 未找到任何日志文件", err=True)
        sys.exit(1)

    # 去重并排序
    resolved_paths = sorted(set(resolved_paths))
    click.echo(f"找到 {len(resolved_paths)} 个日志文件", err=True)
    for fp in resolved_paths:
        size_mb = os.path.getsize(fp) / (1024 * 1024)
        click.echo(f"  - {fp} ({size_mb:.1f} MB)", err=True)

    # 加载规则
    rules = []
    if rules_path:
        click.echo(f"加载规则文件: {rules_path}", err=True)
        if rules_path.endswith(".json"):
            rules = load_rules_from_json(rules_path)
        else:
            rules = load_rules_from_excel(rules_path)
        click.echo(f"已加载 {len(rules)} 条自定义规则", err=True)
    elif not builtin_only:
        click.echo("未指定规则文件，将仅使用内置规则", err=True)

    # 创建扫描器
    scanner = LogScanner(
        rules=rules,
        context_lines=context_lines,
        context_seconds=context_seconds,
        use_builtin_rules=True,
        ignore_patterns=list(ignore_patterns) if ignore_patterns else None,
    )

    # 扫描
    def progress(bytes_read, total_bytes, match_count):
        pct = (bytes_read / total_bytes * 100) if total_bytes > 0 else 0
        click.echo(f"\r  进度: {pct:.1f}% | 已匹配: {match_count}", err=True, nl=False)

    all_matches = []
    for fp in resolved_paths:
        click.echo(f"\n扫描: {fp}", err=True)
        matches = scanner.scan_file(
            fp, encoding=encoding, max_matches=max_matches, progress_callback=progress
        )
        click.echo(f"\n  发现 {len(matches)} 个错误", err=True)
        all_matches.extend(matches)

    # 全局排序
    all_matches.sort(key=lambda m: (
        m.timestamp or __import__("datetime").datetime.max,
        m.file_path,
        m.line_number,
    ))

    click.echo(f"\n共发现 {len(all_matches)} 个错误", err=True)

    # 生成报告
    if output_format == "json":
        report = generate_json_report(all_matches, output_path)
        if not output_path:
            click.echo(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        report = generate_markdown_report(all_matches, output_path, title=title)
        if not output_path:
            click.echo(report)

    if output_path:
        click.echo(f"报告已保存: {output_path}", err=True)


@main.command()
@click.option("-r", "--rules", "rules_path", required=True,
              help="规则文件路径")
def validate(rules_path):
    """验证规则文件的正确性"""
    try:
        if rules_path.endswith(".json"):
            rules = load_rules_from_json(rules_path)
        else:
            rules = load_rules_from_excel(rules_path)

        click.echo(f"规则文件验证通过: 共 {len(rules)} 条规则")
        for r in rules:
            status = "OK"
            click.echo(f"  [{status}] #{r.rule_id} [{r.severity}] {r.pattern_str[:60]}")
    except Exception as e:
        click.echo(f"验证失败: {e}", err=True)
        sys.exit(1)


@main.command()
def builtin_rules():
    """列出所有内置错误规则"""
    from .rule_parser import BUILTIN_PATTERNS
    click.echo(f"内置规则 ({len(BUILTIN_PATTERNS)} 条):\n")
    for r in BUILTIN_PATTERNS:
        click.echo(f"  #{r.rule_id} [{r.severity:5s}] [{r.category:12s}] {r.description}")
        click.echo(f"    Pattern: {r.pattern_str}")
        click.echo()


if __name__ == "__main__":
    main()
