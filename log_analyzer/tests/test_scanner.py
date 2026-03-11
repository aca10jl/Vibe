"""log_analyzer 核心功能测试"""

import os
import tempfile
import pytest
from datetime import datetime

from log_analyzer.rule_parser import ErrorRule, BUILTIN_PATTERNS, load_rules_from_json
from log_analyzer.scanner import LogScanner, parse_timestamp
from log_analyzer.report import generate_markdown_report


SAMPLE_LOG = """\
[2024-06-15 10:00:00.000] INFO Application started successfully
[2024-06-15 10:00:01.000] INFO Listening on port 8080
[2024-06-15 10:00:02.000] INFO Database connection pool initialized: size=20
[2024-06-15 10:00:03.000] DEBUG Health check passed
[2024-06-15 10:00:04.000] INFO Request handled in 45ms
[2024-06-15 10:00:05.000] ERROR connection reset by peer: upstream-service:9090
[2024-06-15 10:00:05.500] ERROR Retrying connection to upstream-service:9090 (attempt 1/3)
[2024-06-15 10:00:06.000] INFO Request handled in 120ms
[2024-06-15 10:00:07.000] WARN timeout waiting for response from cache-service after 5s
[2024-06-15 10:00:08.000] INFO Request handled in 30ms
[2024-06-15 10:00:09.000] FATAL Out of memory: requested 1024MB, available 64MB
[2024-06-15 10:00:09.100] ERROR core dumped: signal 11 in thread worker-5
[2024-06-15 10:00:10.000] INFO Application shutting down
[2024-06-15 10:00:11.000] ERROR NullPointerException at com.app.Service.process(Service.java:88)
[2024-06-15 10:00:12.000] INFO Cleanup completed
"""


@pytest.fixture
def sample_log_file():
    """创建临时日志文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_LOG)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_rules_file():
    """创建临时规则文件"""
    import json
    rules = [
        {"pattern": "(?i)connection.*reset", "description": "连接重置", "severity": "ERROR", "category": "network"},
        {"pattern": "(?i)upstream.*retry", "description": "上游重试", "severity": "WARN", "category": "network"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(rules, f)
        path = f.name
    yield path
    os.unlink(path)


class TestTimestampParsing:
    def test_standard_format(self):
        ts = parse_timestamp("[2024-06-15 10:30:45.123] INFO test")
        assert ts is not None
        assert ts.year == 2024
        assert ts.month == 6
        assert ts.hour == 10

    def test_iso_format(self):
        ts = parse_timestamp("2024-06-15T10:30:45.000Z some message")
        assert ts is not None

    def test_no_timestamp(self):
        ts = parse_timestamp("just a plain message with no time")
        assert ts is None


class TestScanner:
    def test_scan_with_builtin_rules(self, sample_log_file):
        scanner = LogScanner(rules=[], context_lines=5, use_builtin_rules=True)
        matches = scanner.scan_file(sample_log_file)
        assert len(matches) > 0

        # 应该能找到 OOM、connection reset、core dump 等
        severities = {m.rule.severity for m in matches}
        assert "FATAL" in severities or "ERROR" in severities

    def test_scan_with_custom_rules(self, sample_log_file, sample_rules_file):
        rules = load_rules_from_json(sample_rules_file)
        scanner = LogScanner(rules=rules, context_lines=3, use_builtin_rules=False)
        matches = scanner.scan_file(sample_log_file)
        assert len(matches) > 0
        assert any("连接重置" in m.rule.description for m in matches)

    def test_context_extraction(self, sample_log_file):
        scanner = LogScanner(rules=[], context_lines=3, use_builtin_rules=True)
        matches = scanner.scan_file(sample_log_file)
        for m in matches:
            assert isinstance(m.context_before, list)
            assert isinstance(m.context_after, list)

    def test_deduplication(self, sample_log_file):
        """连续的相同错误应该被去重"""
        scanner = LogScanner(rules=[], context_lines=2, use_builtin_rules=True)
        matches = scanner.scan_file(sample_log_file)
        # 检查没有同规则的连续匹配（5行内）
        for i in range(1, len(matches)):
            if matches[i].rule.rule_id == matches[i-1].rule.rule_id:
                assert matches[i].line_number - matches[i-1].line_number > 5

    def test_ignore_patterns(self, sample_log_file):
        scanner = LogScanner(
            rules=[], context_lines=2, use_builtin_rules=True,
            ignore_patterns=["connection reset"]
        )
        matches = scanner.scan_file(sample_log_file)
        for m in matches:
            assert "connection reset" not in m.line_content.lower()


class TestReport:
    def test_markdown_report(self, sample_log_file):
        scanner = LogScanner(rules=[], context_lines=3, use_builtin_rules=True)
        matches = scanner.scan_file(sample_log_file)
        report = generate_markdown_report(matches, title="测试报告")
        assert "# 测试报告" in report
        assert "统计总览" in report
        assert "错误时间线" in report
        assert "错误详情" in report

    def test_empty_report(self):
        report = generate_markdown_report([], title="空报告")
        assert "未检测到" in report


class TestSkillInterface:
    def test_analyze_logs(self, sample_log_file):
        from log_analyzer.skill import analyze_logs
        result = analyze_logs(log_paths=[sample_log_file])
        assert result["total_errors"] > 0
        assert "report_markdown" in result
        assert "severity_summary" in result
        assert len(result["matches"]) > 0
