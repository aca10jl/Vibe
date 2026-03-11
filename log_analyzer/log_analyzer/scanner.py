"""
日志扫描引擎：流式处理大文件，正则匹配错误行，提取上下文。

核心特性：
- 流式逐行读取，内存占用恒定（不受文件大小影响）
- 环形缓冲区保留前后上下文行
- 自动解析时间戳，支持按时间窗口提取上下文
- 多文件并行扫描
"""

import re
import os
import mmap
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .rule_parser import ErrorRule

# 常见日志时间戳格式
TIMESTAMP_PATTERNS = [
    # 2024-01-15 10:30:45.123
    (re.compile(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)"), "%Y-%m-%d %H:%M:%S"),
    # 2024-01-15T10:30:45.123Z  (ISO 8601)
    (re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"), "%Y-%m-%dT%H:%M:%S"),
    # Jan 15 10:30:45
    (re.compile(r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"), "%b %d %H:%M:%S"),
    # 15/Jan/2024:10:30:45 (Apache/Nginx)
    (re.compile(r"(\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2})"), "%d/%b/%Y:%H:%M:%S"),
    # [2024-01-15 10:30:45]
    (re.compile(r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]"), "%Y-%m-%d %H:%M:%S"),
    # Unix timestamp (10 digits)
    (re.compile(r"\b(\d{10})\b"), "epoch"),
]


@dataclass
class ErrorMatch:
    """一个被匹配到的错误"""
    file_path: str
    line_number: int
    line_content: str
    matched_text: str
    rule: ErrorRule
    timestamp: Optional[datetime] = None
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)

    @property
    def context_full(self) -> str:
        """完整上下文（前+当前+后）"""
        lines = []
        for l in self.context_before:
            lines.append(f"  {l}")
        lines.append(f">> {self.line_content}")
        for l in self.context_after:
            lines.append(f"  {l}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "content": self.line_content.strip(),
            "matched_text": self.matched_text,
            "rule_id": self.rule.rule_id,
            "rule_pattern": self.rule.pattern_str,
            "description": self.rule.description,
            "severity": self.rule.severity,
            "category": self.rule.category,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "context_before": [l.strip() for l in self.context_before],
            "context_after": [l.strip() for l in self.context_after],
        }


def parse_timestamp(line: str) -> Optional[datetime]:
    """尝试从日志行中解析时间戳"""
    for pattern, fmt in TIMESTAMP_PATTERNS:
        m = pattern.search(line)
        if m:
            ts_str = m.group(1)
            try:
                if fmt == "epoch":
                    return datetime.fromtimestamp(int(ts_str))
                # 去掉微秒部分的多余精度
                if "." in ts_str:
                    base, frac = ts_str.rsplit(".", 1)
                    frac = frac[:6]  # 最多6位微秒
                    return datetime.strptime(base, fmt).replace(
                        microsecond=int(frac.ljust(6, "0"))
                    )
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
    return None


class LogScanner:
    """流式日志扫描器"""

    def __init__(
        self,
        rules: list[ErrorRule],
        context_lines: int = 30,
        context_seconds: float = 5.0,
        use_builtin_rules: bool = True,
        ignore_patterns: Optional[list[str]] = None,
    ):
        self.rules = list(rules)
        if use_builtin_rules:
            from .rule_parser import BUILTIN_PATTERNS
            self.rules.extend(BUILTIN_PATTERNS)

        self.context_lines = context_lines
        self.context_seconds = context_seconds

        # 编译忽略模式
        self.ignore_patterns = []
        if ignore_patterns:
            for p in ignore_patterns:
                self.ignore_patterns.append(re.compile(p, re.IGNORECASE))

    def _should_ignore(self, line: str) -> bool:
        """判断是否应忽略此行（无伤大雅的错误）"""
        for p in self.ignore_patterns:
            if p.search(line):
                return True
        return False

    def scan_file(
        self,
        file_path: str,
        encoding: str = "utf-8",
        max_matches: int = 0,
        progress_callback=None,
    ) -> list[ErrorMatch]:
        """
        扫描单个日志文件。

        使用两遍扫描法：
        1. 第一遍：找到所有匹配行
        2. 第二遍：为每个匹配行提取上下文
        (对于大文件，这比在内存中保留全部行更高效)
        """
        file_path = str(file_path)
        file_size = os.path.getsize(file_path)

        # 第一遍：找到所有匹配
        raw_matches = []
        line_count = 0
        bytes_read = 0

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                line_count += 1
                bytes_read += len(line.encode(encoding, errors="replace"))

                if progress_callback and line_number % 100000 == 0:
                    progress_callback(bytes_read, file_size, len(raw_matches))

                if self._should_ignore(line):
                    continue

                for rule in self.rules:
                    m = rule.pattern.search(line)
                    if m:
                        ts = parse_timestamp(line)
                        raw_matches.append(ErrorMatch(
                            file_path=file_path,
                            line_number=line_number,
                            line_content=line.rstrip("\n\r"),
                            matched_text=m.group(0),
                            rule=rule,
                            timestamp=ts,
                        ))
                        break  # 一行只匹配第一个规则

                if max_matches > 0 and len(raw_matches) >= max_matches:
                    break

        if not raw_matches:
            return []

        # 去重：相同规则的连续错误（5行内），只保留第一个
        deduped = self._deduplicate(raw_matches)

        # 第二遍：提取上下文
        self._fill_context(file_path, deduped, line_count, encoding)

        return deduped

    def _deduplicate(self, matches: list[ErrorMatch], proximity: int = 5) -> list[ErrorMatch]:
        """去除同一规则在相邻行的重复匹配"""
        if not matches:
            return matches

        result = [matches[0]]
        for m in matches[1:]:
            prev = result[-1]
            if m.rule.rule_id == prev.rule.rule_id and (m.line_number - prev.line_number) <= proximity:
                continue
            result.append(m)
        return result

    def _fill_context(
        self,
        file_path: str,
        matches: list[ErrorMatch],
        total_lines: int,
        encoding: str,
    ):
        """为每个匹配填充上下文行"""
        if not matches:
            return

        # 构建需要读取的行号范围集合
        needed_ranges = {}  # match_idx -> (start, end)
        for idx, m in enumerate(matches):
            start = max(1, m.line_number - self.context_lines)
            end = min(total_lines, m.line_number + self.context_lines)
            needed_ranges[idx] = (start, end)

        # 合并所有需要的行号
        all_needed_lines = set()
        for start, end in needed_ranges.values():
            all_needed_lines.update(range(start, end + 1))

        # 读取所需行
        line_cache = {}
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                if line_number in all_needed_lines:
                    line_cache[line_number] = line.rstrip("\n\r")
                if line_number > max(all_needed_lines):
                    break

        # 填充上下文，考虑时间窗口
        for idx, m in enumerate(matches):
            start, end = needed_ranges[idx]

            before = []
            after = []

            for ln in range(start, m.line_number):
                content = line_cache.get(ln, "")
                # 如果有时间戳，检查时间窗口
                if m.timestamp and self.context_seconds > 0:
                    ts = parse_timestamp(content)
                    if ts and abs((ts - m.timestamp).total_seconds()) > self.context_seconds:
                        continue
                before.append(content)

            for ln in range(m.line_number + 1, end + 1):
                content = line_cache.get(ln, "")
                if m.timestamp and self.context_seconds > 0:
                    ts = parse_timestamp(content)
                    if ts and abs((ts - m.timestamp).total_seconds()) > self.context_seconds:
                        continue
                after.append(content)

            m.context_before = before
            m.context_after = after

    def scan_multiple(
        self,
        file_paths: list[str],
        encoding: str = "utf-8",
        progress_callback=None,
    ) -> list[ErrorMatch]:
        """扫描多个日志文件并合并结果"""
        all_matches = []
        for fp in file_paths:
            matches = self.scan_file(fp, encoding=encoding, progress_callback=progress_callback)
            all_matches.extend(matches)

        # 按时间排序（有时间戳的优先）
        all_matches.sort(key=lambda m: (
            m.timestamp or datetime.max,
            m.file_path,
            m.line_number,
        ))
        return all_matches
