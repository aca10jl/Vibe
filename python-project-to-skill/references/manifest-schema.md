# Manifest Schema

Use this schema with:

```bash
python scripts/batch_convert.py --manifest <MANIFEST_JSON> --output-root <SKILL_OUTPUT_ROOT>
```

## JSON Shape

```json
{
  "projects": [
    {
      "path": "C:/path/to/project-a",
      "skill_name": "project-a-skill",
      "mode": "balanced",
      "copy_source": "none",
      "interactive": false
    }
  ]
}
```

## Fields

- `projects` (required, array)
  List of project conversion jobs.

Per job:

- `path` (required, string)
  Absolute or relative path to source project root.
- `skill_name` (optional, string)
  Override generated skill folder name.
- `mode` (optional, string)
  One of `quick`, `balanced`, `deep`.
- `copy_source` (optional, string)
  One of `none`, `minimal`, `full`.
- `interactive` (optional, boolean)
  If true, converter asks follow-up questions during this job.

## Example: Mixed Portfolio

```json
{
  "projects": [
    {
      "path": "D:/repos/etl-pipeline",
      "mode": "balanced",
      "copy_source": "minimal"
    },
    {
      "path": "D:/repos/vision-enhancer",
      "skill_name": "vision-enhancer-skill",
      "mode": "deep",
      "copy_source": "none"
    },
    {
      "path": "D:/repos/anomaly-engine",
      "mode": "balanced",
      "copy_source": "none"
    }
  ]
}
```

## Validation Tips

1. Verify every `path` exists before batch execution.
2. Keep `copy_source=none` unless source snapshot is explicitly needed.
3. Use `--results-out` to capture full success/failure status.
