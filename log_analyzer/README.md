# Log Analyzer - 自动化日志问题定位与根因分析工具

自动化扫描大规模系统日志，通过正则匹配 + 内置规则识别关键错误，提取上下文，生成错误时间线和分析报告。

## 核心特性

- **大文件流式处理**：逐行读取，内存占用恒定，轻松处理几百MB日志
- **双层规则引擎**：自定义 Excel/JSON 规则 + 14 条内置通用规则（OOM、segfault、deadlock、连接异常等）
- **智能上下文提取**：按行数 + 时间窗口双维度提取错误前后上下文
- **自动时间戳解析**：支持 6 种常见日志时间格式
- **结构化报告**：Markdown / JSON 两种输出格式，包含统计总览、时间线、错误详情
- **Skill 接口**：可被 OpenCode / Claude Code 等 AI 编码智能体直接调用

## 快速开始

### 安装

```bash
cd log_analyzer
pip install -e .
```

### 基础用法

```bash
# 使用内置规则扫描日志
log-analyzer scan -l /path/to/app.log --builtin-only

# 使用自定义规则文件
log-analyzer scan -l /path/to/logs/*.log -r 问题规则标注.xlsx -o report.md

# 扫描整个目录
log-analyzer scan -l /var/log/myapp/ -r rules.xlsx

# 输出 JSON 格式
log-analyzer scan -l app.log -r rules.json --format json -o report.json
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-l, --log` | 日志文件路径（支持 glob，可多次指定） | 必填 |
| `-r, --rules` | 规则文件（.xlsx 或 .json） | 可选 |
| `--builtin-only` | 仅使用内置规则 | false |
| `--context-lines` | 错误前后提取行数 | 30 |
| `--context-seconds` | 错误前后时间窗口（秒） | 5.0 |
| `-o, --output` | 输出文件路径 | stdout |
| `--format` | 输出格式 (markdown/json) | markdown |
| `--encoding` | 日志编码 | utf-8 |
| `--max-matches` | 每文件最大匹配数（0=无限） | 0 |
| `--ignore` | 忽略的正则模式（可多次指定） | 无 |

## 规则文件格式

### Excel 格式（.xlsx）

| error match | error description | severity | category |
|-------------|-------------------|----------|----------|
| `(?i)ERROR.*database.*connection` | 数据库连接错误 | ERROR | database |
| `(?i)out\s*of\s*memory` | 内存溢出 | FATAL | resource |

- **必填列**：`error match`（正则表达式）
- **可选列**：`error description`、`severity`、`category`

### JSON 格式

```json
[
    {
        "pattern": "(?i)ERROR.*database.*connection",
        "description": "数据库连接错误",
        "severity": "ERROR",
        "category": "database"
    }
]
```

参考 `sample_data/sample_rules.json` 获取完整示例。

## 内置规则

工具内置 14 条通用错误模式，即使不提供规则文件也能识别常见问题：

```bash
log-analyzer builtin-rules
```

| 规则 | 描述 | 严重程度 |
|------|------|----------|
| FATAL/PANIC/CRITICAL | 致命级别错误 | FATAL |
| OOM/oom-killer | 内存溢出 | FATAL |
| segfault/SIGSEGV | 段错误 | FATAL |
| deadlock | 死锁检测 | ERROR |
| connection refused/reset/timeout | 连接异常 | ERROR |
| disk full/no space left | 磁盘空间不足 | ERROR |
| permission denied | 权限被拒绝 | ERROR |
| NullPointerException | 空指针异常 | ERROR |
| too many open files | 文件描述符耗尽 | ERROR |
| core dump | 产生 core dump | FATAL |
| Exception/Error/Traceback | 通用异常标记 | ERROR |
| ... | 更多 | ... |

## 作为 AI Skill 使用

### Python API（适用于 OpenCode / Claude Code）

```python
from log_analyzer.skill import analyze_logs

result = analyze_logs(
    log_paths=["/path/to/logs/*.log"],
    rules_path="rules.xlsx",        # 可选
    context_lines=30,
    context_seconds=5.0,
)

# 获取报告
print(result["report_markdown"])

# 获取结构化数据
print(f"总错误数: {result['total_errors']}")
print(f"严重程度分布: {result['severity_summary']}")
print(f"分类分布: {result['category_summary']}")

# 遍历每个错误
for m in result["matches"]:
    print(f"[{m['severity']}] {m['file']}:{m['line']} - {m['description']}")
```

### Claude Code Skill 集成

将 `opencode_skill.md` 的内容添加到项目的 `CLAUDE.md` 或 skill 配置中，AI Agent 即可自动调用此工具分析日志。

## 分析流程

```
日志文件 (*.log)          规则文件 (.xlsx/.json)
       │                         │
       ▼                         ▼
┌─────────────┐          ┌──────────────┐
│ 流式逐行读取 │          │ 解析规则文件   │
└──────┬──────┘          │ + 内置规则     │
       │                 └──────┬───────┘
       ▼                        │
┌─────────────────────────────────┐
│    正则匹配引擎                   │
│  (自定义规则 + 内置规则)           │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│    上下文提取                     │
│  (前后 N 行 + 时间窗口)           │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│    去重 + 时间排序                │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│    报告生成                      │
│  (统计 + 时间线 + 详情 + 建议)    │
└─────────────────────────────────┘
               │
               ▼
      Markdown / JSON 报告
```

## 测试

```bash
# 运行测试
pip install -e ".[dev]"
python -m pytest tests/ -v

# 生成示例日志并测试
python sample_data/generate_sample_logs.py
log-analyzer scan -l sample_app.log -r sample_data/sample_rules.json -o test_report.md
```

## 目录结构

```
log_analyzer/
├── pyproject.toml              # 项目配置与依赖
├── README.md                   # 本文档
├── opencode_skill.md           # OpenCode/Claude Code Skill 定义
├── log_analyzer/
│   ├── __init__.py
│   ├── __main__.py             # python -m log_analyzer 入口
│   ├── cli.py                  # CLI 命令行接口
│   ├── rule_parser.py          # 规则解析器（Excel/JSON + 内置规则）
│   ├── scanner.py              # 流式日志扫描引擎
│   ├── report.py               # 报告生成器（Markdown/JSON）
│   └── skill.py                # AI Skill 接口
├── sample_data/
│   ├── sample_rules.json       # 示例规则文件
│   ├── generate_sample_logs.py # 示例日志生成器
│   └── sample_report.md        # 示例分析报告
└── tests/
    └── test_scanner.py         # 单元测试
```
