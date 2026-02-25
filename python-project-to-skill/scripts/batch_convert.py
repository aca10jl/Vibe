#!/usr/bin/env python3
"""Batch conversion entrypoint for project_to_skill.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from project_to_skill import convert_project


def discover_projects(projects_root: Path, pattern: str, max_projects: int) -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(projects_root.glob(pattern)):
        if path.is_dir():
            candidates.append(path.resolve())
        if len(candidates) >= max_projects:
            break
    return candidates


def load_manifest(manifest_path: Path) -> list[dict[str, object]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Manifest root must be an object.")
    projects = payload.get("projects")
    if not isinstance(projects, list):
        raise ValueError("Manifest must contain a 'projects' array.")
    normalized: list[dict[str, object]] = []
    for idx, item in enumerate(projects, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"projects[{idx}] must be an object.")
        if "path" not in item:
            raise ValueError(f"projects[{idx}] is missing required field: path")
        normalized.append(item)
    return normalized


def convert_many(
    *,
    jobs: list[dict[str, object]],
    output_root: Path,
    max_files: int,
    force: bool,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    for job in jobs:
        path = Path(str(job["path"])).resolve()
        mode = str(job.get("mode", "balanced"))
        copy_source = str(job.get("copy_source", "none"))
        skill_name = job.get("skill_name")
        skill_name_text = str(skill_name) if isinstance(skill_name, str) else None
        interactive = bool(job.get("interactive", False))

        row: dict[str, object] = {
            "project": str(path),
            "mode": mode,
            "copy_source": copy_source,
        }

        try:
            generated = convert_project(
                project_root=path,
                output_root=output_root,
                skill_name=skill_name_text,
                mode=mode,
                copy_source=copy_source,
                max_files=max_files,
                interactive=interactive,
                force=force,
            )
            row["status"] = "ok"
            row["skill_dir"] = str(generated)
        except Exception as exc:  # pragma: no cover - runtime error surface
            row["status"] = "error"
            row["error"] = str(exc)

        results.append(row)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch convert Python projects into Codex skill packages.",
    )
    parser.add_argument("--output-root", required=True, help="Output root for generated skills")
    parser.add_argument("--max-files", type=int, default=2500, help="Maximum files to scan per project")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated skill folders")
    parser.add_argument("--results-out", help="Optional output JSON file for batch results")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", help="JSON manifest containing explicit project jobs")
    source.add_argument("--projects-root", help="Directory to discover projects from")

    parser.add_argument(
        "--pattern",
        default="*",
        help="Glob pattern under --projects-root, default '*'",
    )
    parser.add_argument("--max-projects", type=int, default=200, help="Maximum discovered projects")
    parser.add_argument("--mode", choices=["quick", "balanced", "deep"], default="balanced")
    parser.add_argument("--copy-source", choices=["none", "minimal", "full"], default="none")

    args = parser.parse_args()

    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if args.manifest:
        jobs = load_manifest(Path(args.manifest).resolve())
    else:
        roots = discover_projects(Path(args.projects_root).resolve(), args.pattern, args.max_projects)
        jobs = [{"path": str(path), "mode": args.mode, "copy_source": args.copy_source} for path in roots]

    if not jobs:
        raise SystemExit("No projects selected for conversion.")

    results = convert_many(
        jobs=jobs,
        output_root=output_root,
        max_files=args.max_files,
        force=args.force,
    )

    ok = sum(1 for item in results if item.get("status") == "ok")
    failed = sum(1 for item in results if item.get("status") == "error")

    print(f"[DONE] Converted {ok} project(s), {failed} failed.")
    if failed:
        for item in results:
            if item.get("status") == "error":
                print(f"[FAIL] {item.get('project')}: {item.get('error')}")

    if args.results_out:
        out_path = Path(args.results_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[OK] Wrote batch report: {out_path}")
    else:
        print(json.dumps({"results": results}, indent=2, ensure_ascii=False))

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
