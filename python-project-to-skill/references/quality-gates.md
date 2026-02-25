# Quality Gates

## Gate 1: Structural Completeness

- `SKILL.md` exists with valid frontmatter.
- `agents/openai.yaml` exists and includes:
  `display_name`, `short_description`, `default_prompt`.
- `scripts/` and `references/` contain useful, non-placeholder content.
- `short_description` length is between 25 and 64 characters.

## Gate 2: Trigger Quality

- `description` clearly states what the skill does.
- `description` clearly states when to use the skill.
- Trigger context includes domain hints (for example training/ETL/CV/anomaly).
- Description is specific enough to avoid accidental triggering.

## Gate 3: Operational Correctness

- `scripts/task_catalog.json` commands are reviewed.
- `scripts/task_runner.py --dry-run` works for at least one task.
- Placeholder commands are removed or explicitly marked as pending.
- Risky commands are labeled and require approval before execution.

## Gate 4: Validation

Run:

```bash
python C:/Users/User/.codex/skills/.system/skill-creator/scripts/quick_validate.py <SKILL_DIR>
```

Expected:

- Exit code `0`.
- Message includes `Skill is valid!`.

## Gate 5: Usability

- Conversion report explains inferred domains/frameworks.
- Assumptions and unresolved items are explicit.
- User can continue iteration without re-discovering project context.

## Scoring Rubric (Optional)

Use 0-2 scoring per dimension:

- Structure
- Trigger quality
- Operational correctness
- Validation
- Usability

Interpretation:

- `9-10`: Ready for routine use.
- `7-8`: Usable with minor fixes.
- `5-6`: Needs additional curation before regular use.
- `<5`: Re-run conversion with clearer scope.
