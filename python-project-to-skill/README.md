# Python Project to Skill

将现有 Python 工程自动转换为可被 AI Agent 调用的 skill 包。

## 能做什么

- 分析项目结构、依赖、入口脚本、测试、文档和领域信号
- 自动生成目标 skill（`SKILL.md`、`agents/openai.yaml`、`scripts/`、`references/`）
- 生成可复用任务目录（`task_catalog.json`）和任务执行器（`task_runner.py`）
- 支持批量转换多个项目

## 目录说明

- `scripts/project_to_skill.py`：单项目分析与转换
- `scripts/batch_convert.py`：批量转换入口
- `references/workflow-playbook.md`：复杂场景策略
- `references/quality-gates.md`：质量门禁
- `references/manifest-schema.md`：批量清单格式

## 快速开始

在仓库根目录执行。

### 1) 单项目分析

```bash
python python-project-to-skill/scripts/project_to_skill.py analyze --project <PROJECT_PATH> --out <PROFILE_JSON>
```

### 2) 单项目转换

```bash
python python-project-to-skill/scripts/project_to_skill.py convert --project <PROJECT_PATH> --output-root <SKILL_OUTPUT_ROOT> --mode balanced --copy-source none
```

### 3) 校验生成结果

```bash
python C:/Users/User/.codex/skills/.system/skill-creator/scripts/quick_validate.py <GENERATED_SKILL_DIR>
```

### 4) 任务干跑（不执行真实命令）

```bash
python <GENERATED_SKILL_DIR>/scripts/task_runner.py --task <TASK_ID> --project-root <PROJECT_PATH> --dry-run
```

## 批量转换

### 方式 A：目录发现

```bash
python python-project-to-skill/scripts/batch_convert.py --projects-root <PROJECTS_ROOT> --pattern "*" --output-root <SKILL_OUTPUT_ROOT> --mode balanced --copy-source none --results-out <REPORT_JSON>
```

### 方式 B：Manifest 驱动

先按 `references/manifest-schema.md` 准备 JSON，再执行：

```bash
python python-project-to-skill/scripts/batch_convert.py --manifest <MANIFEST_JSON> --output-root <SKILL_OUTPUT_ROOT> --results-out <REPORT_JSON>
```

## 常用参数建议

- `--mode`：`quick | balanced | deep`，默认推荐 `balanced`
- `--copy-source`：`none | minimal | full`，默认推荐 `none`
- `--interactive`：启用交互式参数确认
- `--force`：覆盖已有输出目录（谨慎）
- `--max-files`：超大仓库可调大扫描上限

## 结果产物

每个生成 skill 通常包含：

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/task_catalog.json`
- `scripts/task_runner.py`
- `references/source-project-profile.json`
- `references/conversion-report.md`

## 注意事项

- 默认不要执行高成本训练/推理命令，先用 `--dry-run`
- 对占资源任务先与用户确认
- 生成后请人工检查 `task_catalog.json`，替换占位命令
- 最终交付前建议跑一遍 `quick_validate.py`
