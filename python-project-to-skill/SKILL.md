---
name: python-project-to-skill
description: Convert one or many existing Python repositories into reusable Codex skills that AI agents can call. Use when the user asks to package Python projects (data processing, model training, image enhancement, anomaly detection, ETL, notebooks, APIs, automation scripts) into skill folders with SKILL.md, agents/openai.yaml, scripts, references, and validation-ready workflows.
---

# Python Project To Skill

## Overview

Convert existing Python repositories into production-usable skill packages with:

- automated project profiling,
- generated skill scaffolding,
- repeatable task catalogs,
- optional batch conversion across many repositories.

Use deterministic scripts first, then refine generated skill content with user-specific constraints.

## Skill Resources

- `scripts/project_to_skill.py`
  Single-project analyzer and converter.
- `scripts/batch_convert.py`
  Multi-project batch conversion entrypoint.
- `references/workflow-playbook.md`
  Decision rules for complex conversions.
- `references/quality-gates.md`
  Validation and release checklist.
- `references/manifest-schema.md`
  Batch manifest format and examples.

## Workflow Selection

1. If user gives one project path: run **single-project conversion**.
2. If user gives many project paths or asks for scale: run **batch conversion**.
3. If user goals are unclear: run **interactive intake first**, then convert.
4. If repository is huge or high-risk: run `analyze` first and ask for approval before `convert`.

## Interactive Intake Protocol

Ask questions in small batches (max 3 at a time). Prioritize:

1. Source scope:
   Exact project path(s), include/exclude rules.
2. Output scope:
   Skill output root, naming convention, and overwrite policy.
3. Runtime risk policy:
   Whether expensive commands are allowed, and whether source code snapshot is allowed.

When answers are incomplete, proceed with safe defaults:

- `mode=balanced`
- `copy-source=none`
- `max-files=2500`
- no destructive overwrite unless explicitly approved

## Single-Project Conversion

### Step 1: Analyze

Run:

```bash
python scripts/project_to_skill.py analyze --project <PROJECT_PATH> --out <PROFILE_JSON>
```

Inspect inferred domains, frameworks, entry points, and sampled commands from docs.

For large repos, increase scan cap:

```bash
python scripts/project_to_skill.py analyze --project <PROJECT_PATH> --max-files 10000
```

### Step 2: Decide Conversion Strategy

Choose mode:

- `quick`: fast scaffold, less enrichment.
- `balanced`: default, best tradeoff.
- `deep`: more references for complex repos.

Choose source copy policy:

- `none`: no source snapshot (default).
- `minimal`: copy key config/docs only.
- `full`: copy entire repository snapshot into `assets/source-snapshot/`.

### Step 3: Convert

Run:

```bash
python scripts/project_to_skill.py convert --project <PROJECT_PATH> --output-root <SKILL_OUTPUT_ROOT> --mode balanced --copy-source none
```

Optional interactive conversion:

```bash
python scripts/project_to_skill.py convert --project <PROJECT_PATH> --output-root <SKILL_OUTPUT_ROOT> --interactive
```

### Step 4: Refine Generated Skill

After generation, update:

- `SKILL.md` description specificity and trigger quality.
- `scripts/task_catalog.json` command correctness.
- `references/conversion-report.md` assumptions and risk notes.

Replace generic generated commands (for example `python train.py`) with real project commands.

### Step 5: Validate

Run:

```bash
python C:/Users/User/.codex/skills/.system/skill-creator/scripts/quick_validate.py <GENERATED_SKILL_DIR>
```

Then dry-run command catalog:

```bash
python <GENERATED_SKILL_DIR>/scripts/task_runner.py --task <TASK_ID> --project-root <PROJECT_PATH> --dry-run
```

For quality bar, apply `references/quality-gates.md`.

## Batch Conversion

Use when user has many projects.

### Option A: Discover Projects by Folder

```bash
python scripts/batch_convert.py --projects-root <PROJECTS_ROOT> --pattern "*" --output-root <SKILL_OUTPUT_ROOT> --mode balanced --copy-source none --results-out <REPORT_JSON>
```

### Option B: Manifest-Driven Conversion

Create a manifest using `references/manifest-schema.md`, then run:

```bash
python scripts/batch_convert.py --manifest <MANIFEST_JSON> --output-root <SKILL_OUTPUT_ROOT> --results-out <REPORT_JSON>
```

Batch mode returns success/error per project; treat errors as retry backlog, not full-stop failure.

## Output Contract

When reporting results to the user, always include:

1. Generated skill directory path(s).
2. Core inferred domains/frameworks per project.
3. Any commands that remain placeholders and need manual correction.
4. Validation status (passed/failed + failing reason).
5. Next actions for iteration.

## Failure Handling

If conversion fails:

1. Run `analyze` only and return profile + blocker.
2. Reduce scope (`quick` mode, lower copy depth).
3. Ask only the minimum missing question.
4. Retry conversion with explicit assumptions.

If source repository is inaccessible, request corrected path and continue.

## Safety Rules

- Do not execute expensive training/inference commands without explicit user approval.
- Default to `copy-source=none` to reduce accidental data/code leakage.
- Never remove existing outputs unless `--force` is explicitly chosen.
- Keep deterministic logic in scripts and narrative guidance in references.

## Deep Guidance

For complex projects (multi-package monorepos, mixed frameworks, strict compliance constraints), load:

- `references/workflow-playbook.md`
- `references/quality-gates.md`

Use them as extension guides; keep this SKILL.md as the execution spine.
