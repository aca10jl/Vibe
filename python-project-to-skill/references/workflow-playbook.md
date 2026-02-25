# Workflow Playbook

## Purpose

Use this file when conversion requirements are complex, multi-stage, or high-risk.
Keep `SKILL.md` as the default path and load this playbook only for deeper strategy.

## Conversion Depth Matrix

| Situation | Recommended Mode | Copy Source | Notes |
| --- | --- | --- | --- |
| Small utility script repo | quick | none | Prioritize speed and minimal scaffolding |
| Typical data/model repo | balanced | none/minimal | Best default for most teams |
| Enterprise monorepo or regulated workflow | deep | minimal/full | Add stronger references and explicit risk notes |

## Archetype Mapping

### Data Processing / ETL

- Strong signals:
  `pandas`, `polars`, `dask`, `spark`, `pipeline`, `etl`.
- Required generated tasks:
  data build, validation, smoke sample.
- Required references:
  source profile, data contract notes, pipeline runbook.

### Model Training

- Strong signals:
  `torch`, `tensorflow`, `xgboost`, `lightgbm`, `train`, `epoch`.
- Required generated tasks:
  training run, evaluation, optional hyperparameter script.
- Guardrail:
  ask before expensive or long-running jobs.

### Image Enhancement / CV

- Strong signals:
  `opencv`, `pillow`, image folders, augmentation scripts.
- Required generated tasks:
  inference sample, batch transform, metric check.
- Guardrail:
  verify image I/O paths before execution.

### Anomaly Detection

- Strong signals:
  `anomaly`, `outlier`, `iforest`, `oneclass`.
- Required generated tasks:
  scoring run, threshold config check, drift or alert summary.

## Interactive Question Packs

Ask in packs to avoid overwhelming the user.

### Pack A: Scope

1. Which repository path(s) should be converted?
2. Should all subfolders be included?
3. Any directories to exclude?

### Pack B: Execution Risk

1. Can this conversion run heavy commands (training/inference)?
2. Is dry-run only required for now?
3. Should source snapshot be copied (`none|minimal|full`)?

### Pack C: Output Expectations

1. Target output root for generated skills?
2. Naming convention (preserve repo name or custom)?
3. Is overwrite allowed (`--force`)?

## Task Catalog Curation Rules

1. Keep only commands with clear execution meaning.
2. Replace placeholders with project-verified commands.
3. Prefer explicit command arguments over hidden defaults.
4. Include test/lint task when available.
5. Add one safety task (`--dry-run` or sample-size run) for expensive pipelines.

## Post-Generation Hardening

1. Tighten generated `description` to include user trigger language.
2. Remove inaccurate domains inferred from noisy keywords.
3. Confirm every task in `task_catalog.json` works in target environment.
4. Add project-specific notes in `references/conversion-report.md`.
5. Re-run quick validation before final delivery.
