# Log Analyzer Skill

## Skill Definition for OpenCode / Claude Code

This skill enables AI coding agents to perform automated log analysis, error pattern matching, root cause analysis, and generate optimization reports.

### Trigger

When the user asks to:
- Analyze log files for errors
- Find root causes in system logs
- Generate error timelines from logs
- Diagnose system issues from log output

### Instructions

You have access to a Python log analysis tool at `log_analyzer/`. To analyze logs:

1. **If a rules Excel/JSON file is provided**, use it for pattern matching:
```python
from log_analyzer.skill import analyze_logs

result = analyze_logs(
    log_paths=["path/to/logs/*.log"],  # supports glob
    rules_path="path/to/rules.xlsx",   # or .json
    context_lines=30,                   # lines of context around each error
    context_seconds=5.0,                # time window for context
)
```

2. **Without a rules file** (uses 14 built-in patterns covering OOM, segfault, deadlock, connection errors, etc.):
```python
result = analyze_logs(log_paths=["/var/log/app/*.log"])
```

3. **Access the results**:
```python
print(result["report_markdown"])        # Full markdown report
print(f"Total errors: {result['total_errors']}")
print(f"By severity: {result['severity_summary']}")
print(f"By category: {result['category_summary']}")

# Individual error details
for match in result["matches"]:
    print(f"[{match['severity']}] {match['file']}:{match['line']} - {match['description']}")
    print(f"  Context: {match['context_before'][-3:]}")  # last 3 lines before error
```

4. **CLI usage** (alternative):
```bash
cd log_analyzer && pip install -e .
log-analyzer scan -l /path/to/logs/ -r rules.xlsx -o report.md
log-analyzer scan -l "*.log" --builtin-only --format json -o report.json
log-analyzer builtin-rules  # list all built-in patterns
```

### After Analysis

Once you have the report, help the user by:
1. Summarizing the most critical errors (FATAL first, then ERROR)
2. Identifying error patterns and correlations in the timeline
3. Providing root cause hypotheses based on error context
4. Suggesting specific remediation actions
