#!/usr/bin/env python3
"""Convert an existing Python project into a reusable Codex skill package.

This script is intentionally stdlib-only so it can run in constrained environments.
"""

from __future__ import annotations

import argparse
import ast
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None  # type: ignore[assignment]

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".nox",
    ".tox",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".ipynb_checkpoints",
}

DOC_CANDIDATES = (
    "README.md",
    "README.rst",
    "README.txt",
    "readme.md",
    "readme.rst",
)

DATA_EXTS = {".csv", ".parquet", ".jsonl", ".feather", ".tsv", ".xlsx", ".xls"}
MODEL_EXTS = {".pt", ".pth", ".onnx", ".ckpt", ".joblib", ".pkl", ".h5", ".keras"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

FRAMEWORK_SIGNATURES = {
    "pandas": {"pandas"},
    "polars": {"polars"},
    "dask": {"dask"},
    "pyspark": {"pyspark", "spark"},
    "scikit-learn": {"sklearn", "scikit-learn"},
    "pytorch": {"torch", "pytorch", "lightning", "pytorch-lightning"},
    "tensorflow": {"tensorflow", "keras"},
    "xgboost": {"xgboost"},
    "lightgbm": {"lightgbm"},
    "opencv": {"opencv", "opencv-python", "cv2"},
    "pillow": {"pillow", "pil"},
    "albumentations": {"albumentations"},
    "matplotlib": {"matplotlib"},
    "seaborn": {"seaborn"},
    "fastapi": {"fastapi"},
    "flask": {"flask"},
    "django": {"django"},
    "streamlit": {"streamlit"},
    "gradio": {"gradio"},
    "mlflow": {"mlflow"},
    "wandb": {"wandb"},
    "pytest": {"pytest"},
}

DOMAIN_KEYWORDS = {
    "data-processing": {
        "etl",
        "dataset",
        "pandas",
        "polars",
        "feature",
        "preprocess",
        "transform",
        "aggregation",
        "cleaning",
        "pipeline",
    },
    "model-training": {
        "train",
        "trainer",
        "epoch",
        "fit",
        "torch",
        "tensorflow",
        "xgboost",
        "lightgbm",
        "sklearn",
        "loss",
        "optimizer",
    },
    "image-enhancement": {
        "image",
        "opencv",
        "cv2",
        "pillow",
        "albumentations",
        "enhance",
        "superresolution",
        "denoise",
        "augment",
    },
    "anomaly-detection": {
        "anomaly",
        "outlier",
        "iforest",
        "isolation",
        "oneclass",
        "ocsvm",
        "drift",
        "novelty",
    },
    "model-serving": {
        "api",
        "fastapi",
        "flask",
        "django",
        "inference",
        "predict",
        "endpoint",
        "service",
    },
    "experiment-tracking": {
        "mlflow",
        "wandb",
        "tracking",
        "experiment",
        "registry",
    },
}

IMPORTANT_FILE_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "environment.yml",
    "environment.yaml",
    "Makefile",
    "Dockerfile",
    ".env.example",
}

REQ_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+")


@dataclass
class ProjectProfile:
    project_root: str
    project_name: str
    scanned_files: int
    truncated_scan: bool
    top_level_dirs: list[str]
    python_files: list[str]
    dependency_files: list[str]
    dependencies: list[str]
    imports: list[str]
    frameworks: list[str]
    domains: list[dict[str, int]]
    entry_points: list[str]
    notebooks: list[str]
    tests: list[str]
    docs: list[str]
    data_assets: list[str]
    model_assets: list[str]
    image_assets: list[str]
    command_samples: list[str]
    important_files: list[str]
    tree_preview: list[str]


def slugify(raw: str) -> str:
    lowered = raw.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    compact = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return compact or "generated-skill"


def title_from_slug(slug: str) -> str:
    return " ".join(chunk.capitalize() for chunk in slug.split("-") if chunk)


def normalize_dependency_name(name: str) -> str:
    return name.lower().replace("_", "-").strip()


def parse_requirement_name(raw: str) -> str | None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(("-r", "--", "git+", "http://", "https://")):
        return None
    line = line.split(";", 1)[0].strip()
    if " @ " in line:
        line = line.split(" @ ", 1)[0].strip()
    line = line.split("[", 1)[0].strip()
    match = REQ_NAME_RE.match(line)
    if not match:
        return None
    return normalize_dependency_name(match.group(0))


def read_text(path: Path, max_bytes: int = 400_000) -> str:
    try:
        payload = path.read_bytes()
    except OSError:
        return ""
    if len(payload) > max_bytes:
        payload = payload[:max_bytes]
    return payload.decode("utf-8", errors="ignore")


def iter_files(project_root: Path, max_files: int) -> tuple[list[Path], bool]:
    collected: list[Path] = []
    for current_root, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".mypy")]
        for filename in filenames:
            full_path = Path(current_root) / filename
            collected.append(full_path)
            if len(collected) >= max_files:
                return collected, True
    return collected, False


def parse_dependencies_from_pyproject(path: Path) -> set[str]:
    if not tomllib:
        return set()
    text = read_text(path, max_bytes=700_000)
    if not text:
        return set()
    try:
        data = tomllib.loads(text)
    except Exception:
        return set()

    found: set[str] = set()

    def consume_iterable(values: Iterable[object]) -> None:
        for value in values:
            if not isinstance(value, str):
                continue
            dep_name = parse_requirement_name(value)
            if dep_name:
                found.add(dep_name)

    project = data.get("project", {})
    if isinstance(project, dict):
        dependencies = project.get("dependencies", [])
        if isinstance(dependencies, list):
            consume_iterable(dependencies)
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group_values in optional.values():
                if isinstance(group_values, list):
                    consume_iterable(group_values)

    tool = data.get("tool", {})
    if isinstance(tool, dict):
        poetry = tool.get("poetry", {})
        if isinstance(poetry, dict):
            poetry_deps = poetry.get("dependencies", {})
            if isinstance(poetry_deps, dict):
                for key in poetry_deps:
                    if key.lower() != "python":
                        found.add(normalize_dependency_name(key))
            poetry_groups = poetry.get("group", {})
            if isinstance(poetry_groups, dict):
                for group_data in poetry_groups.values():
                    if isinstance(group_data, dict):
                        deps = group_data.get("dependencies", {})
                        if isinstance(deps, dict):
                            for key in deps:
                                if key.lower() != "python":
                                    found.add(normalize_dependency_name(key))

        pdm = tool.get("pdm", {})
        if isinstance(pdm, dict):
            pdm_dev = pdm.get("dev-dependencies", {})
            if isinstance(pdm_dev, dict):
                for deps in pdm_dev.values():
                    if isinstance(deps, list):
                        consume_iterable(deps)

    return found


def parse_dependencies_from_setup_cfg(path: Path) -> set[str]:
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except Exception:
        return set()
    found: set[str] = set()
    if parser.has_section("options"):
        raw = parser.get("options", "install_requires", fallback="")
        for line in raw.splitlines():
            dep_name = parse_requirement_name(line)
            if dep_name:
                found.add(dep_name)
    return found


def parse_dependencies_from_setup_py(path: Path) -> set[str]:
    text = read_text(path)
    if not text:
        return set()
    found: set[str] = set()
    matches = re.findall(r"install_requires\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
    for block in matches:
        for item in re.findall(r"['\"]([^'\"]+)['\"]", block):
            dep_name = parse_requirement_name(item)
            if dep_name:
                found.add(dep_name)
    return found


def parse_dependencies_from_requirements(path: Path) -> set[str]:
    text = read_text(path)
    if not text:
        return set()
    found: set[str] = set()
    for raw_line in text.splitlines():
        dep_name = parse_requirement_name(raw_line)
        if dep_name:
            found.add(dep_name)
    return found


def parse_dependencies_from_pipfile(path: Path) -> set[str]:
    text = read_text(path)
    if not text:
        return set()
    found: set[str] = set()
    current_section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped.strip("[]").lower()
            continue
        if current_section in {"packages", "dev-packages"} and "=" in stripped:
            pkg = stripped.split("=", 1)[0].strip().strip('"').strip("'")
            dep_name = parse_requirement_name(pkg)
            if dep_name:
                found.add(dep_name)
    return found


def parse_dependencies_from_environment(path: Path) -> set[str]:
    text = read_text(path)
    if not text:
        return set()
    found: set[str] = set()
    in_pip_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- pip:"):
            in_pip_block = True
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            dep_name = parse_requirement_name(item)
            if dep_name:
                found.add(dep_name)
            if in_pip_block and ":" not in item:
                continue
        elif in_pip_block and stripped.startswith("-"):
            dep_name = parse_requirement_name(stripped[1:].strip())
            if dep_name:
                found.add(dep_name)
        elif stripped and not stripped.startswith(" "):
            in_pip_block = False
    return found


def detect_imports(source_text: str) -> set[str]:
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return set()

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0].lower())
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module.split(".")[0].lower())
    return found


def detect_entry_point(source_text: str) -> bool:
    snippets = [
        'if __name__ == "__main__"',
        "if __name__ == '__main__'",
        "argparse.ArgumentParser(",
        "typer.Typer(",
        "@app.command(",
        "@cli.command(",
        "click.command(",
        "fire.Fire(",
    ]
    return any(snippet in source_text for snippet in snippets)


def guess_domains(profile_text: str) -> list[dict[str, int]]:
    scored: list[dict[str, int]] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in profile_text:
                score += 1
        if score > 0:
            scored.append({"name": domain, "score": score})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def pick_frameworks(dependencies: Iterable[str], imports: Iterable[str]) -> list[str]:
    dep_set = {normalize_dependency_name(dep) for dep in dependencies}
    import_set = {item.lower() for item in imports}
    combined = dep_set | import_set

    detected: list[str] = []
    for framework, signatures in FRAMEWORK_SIGNATURES.items():
        if any(signature in combined for signature in signatures):
            detected.append(framework)
    detected.sort()
    return detected


def extract_command_samples(doc_text: str) -> list[str]:
    if not doc_text:
        return []

    candidates: list[str] = []
    in_fence = False
    for raw_line in doc_text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not line:
            continue
        if line.startswith("$"):
            line = line[1:].strip()
        if not in_fence and not line.startswith(("python ", "pip ", "pytest", "poetry ", "uv ", "make ")):
            continue
        if line.startswith(
            (
                "python ",
                "python3 ",
                "pip ",
                "pip3 ",
                "pytest",
                "poetry ",
                "uv ",
                "make ",
                "streamlit ",
                "jupyter ",
            )
        ):
            if line not in candidates:
                candidates.append(line)
    return candidates[:25]


def find_primary_doc(project_root: Path) -> tuple[Path | None, str]:
    for candidate in DOC_CANDIDATES:
        path = project_root / candidate
        if path.exists():
            return path, read_text(path, max_bytes=500_000)
    return None, ""


def profile_project(project_root: Path, max_files: int) -> ProjectProfile:
    if not project_root.exists() or not project_root.is_dir():
        raise ValueError(f"Project path does not exist or is not a directory: {project_root}")

    files, truncated = iter_files(project_root, max_files=max_files)
    relative_files = [path.relative_to(project_root).as_posix() for path in files]

    python_files = sorted(path for path in relative_files if path.endswith(".py"))
    notebooks = sorted(path for path in relative_files if path.endswith(".ipynb"))
    tests = sorted(
        path
        for path in relative_files
        if "/tests/" in f"/{path}/" or Path(path).name.startswith("test_")
    )
    docs = sorted(
        path
        for path in relative_files
        if path.lower().endswith((".md", ".rst", ".txt")) and ("readme" in path.lower() or path.lower().startswith("docs/"))
    )
    data_assets = sorted(path for path in relative_files if Path(path).suffix.lower() in DATA_EXTS)
    model_assets = sorted(path for path in relative_files if Path(path).suffix.lower() in MODEL_EXTS)
    image_assets = sorted(path for path in relative_files if Path(path).suffix.lower() in IMAGE_EXTS)

    top_level_dirs = sorted({Path(path).parts[0] for path in relative_files if len(Path(path).parts) > 1})
    important_files = sorted(path for path in relative_files if Path(path).name in IMPORTANT_FILE_NAMES)

    dependency_files = sorted(
        path
        for path in relative_files
        if Path(path).name
        in {
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "requirements.in",
            "setup.py",
            "setup.cfg",
            "Pipfile",
            "environment.yml",
            "environment.yaml",
        }
    )

    dependencies: set[str] = set()
    import_modules: set[str] = set()
    entry_points: list[str] = []

    for path in files:
        rel = path.relative_to(project_root).as_posix()
        name = path.name

        if name == "pyproject.toml":
            dependencies |= parse_dependencies_from_pyproject(path)
        elif name in {"requirements.txt", "requirements-dev.txt", "requirements.in"}:
            dependencies |= parse_dependencies_from_requirements(path)
        elif name == "setup.cfg":
            dependencies |= parse_dependencies_from_setup_cfg(path)
        elif name == "setup.py":
            dependencies |= parse_dependencies_from_setup_py(path)
        elif name == "Pipfile":
            dependencies |= parse_dependencies_from_pipfile(path)
        elif name in {"environment.yml", "environment.yaml"}:
            dependencies |= parse_dependencies_from_environment(path)

        if path.suffix == ".py":
            source_text = read_text(path)
            if source_text:
                import_modules |= detect_imports(source_text)
                if detect_entry_point(source_text):
                    entry_points.append(rel)

    entry_points = sorted(set(entry_points))

    primary_doc_path, primary_doc_text = find_primary_doc(project_root)
    if primary_doc_path and primary_doc_path.relative_to(project_root).as_posix() not in docs:
        docs.insert(0, primary_doc_path.relative_to(project_root).as_posix())
    command_samples = extract_command_samples(primary_doc_text)

    profile_text_parts = [
        project_root.name.lower(),
        " ".join(relative_files).lower(),
        " ".join(sorted(dependencies)).lower(),
        " ".join(sorted(import_modules)).lower(),
        primary_doc_text.lower(),
    ]
    domain_candidates = guess_domains(" ".join(profile_text_parts))
    frameworks = pick_frameworks(dependencies, import_modules)

    tree_preview = relative_files[:400]

    return ProjectProfile(
        project_root=str(project_root.resolve()),
        project_name=project_root.name,
        scanned_files=len(relative_files),
        truncated_scan=truncated,
        top_level_dirs=top_level_dirs,
        python_files=python_files,
        dependency_files=dependency_files,
        dependencies=sorted(dependencies),
        imports=sorted(import_modules),
        frameworks=frameworks,
        domains=domain_candidates[:8],
        entry_points=entry_points,
        notebooks=notebooks,
        tests=tests,
        docs=docs,
        data_assets=data_assets,
        model_assets=model_assets,
        image_assets=image_assets,
        command_samples=command_samples,
        important_files=important_files,
        tree_preview=tree_preview,
    )


def suggest_skill_name(project_name: str) -> str:
    slug = slugify(project_name)
    if not slug.endswith("-skill"):
        slug = f"{slug}-skill"
    return slug[:64].rstrip("-")


def safe_short_description(display_name: str) -> str:
    candidate = f"Operate {display_name} project workflows"
    if len(candidate) < 25:
        candidate = f"Help with {display_name} workflows"
    if len(candidate) > 64:
        candidate = f"{display_name} workflow helper"
    if len(candidate) > 64:
        candidate = candidate[:64].rstrip()
    if len(candidate) < 25:
        candidate = f"{display_name} task helper"
    return candidate


def make_description(project_name: str, domains: list[dict[str, int]], frameworks: list[str]) -> str:
    domain_names = [d["name"] for d in domains[:4]]
    domain_text = ", ".join(domain_names) if domain_names else "general Python automation"
    framework_text = ", ".join(frameworks[:6]) if frameworks else "project-specific libraries"
    return (
        f"Operate and evolve the {project_name} repository as an AI-agent callable skill. "
        f"Use when requests involve running or modifying workflows for {domain_text}, "
        f"debugging scripts, adapting data/model pipelines, or exposing reusable commands backed by {framework_text}."
    )


def build_task_catalog(profile: ProjectProfile) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    seen_commands: set[str] = set()

    def add_task(task_id: str, title: str, purpose: str, command: str) -> None:
        if command in seen_commands:
            return
        seen_commands.add(command)
        catalog.append(
            {
                "id": task_id,
                "title": title,
                "purpose": purpose,
                "command": command,
            }
        )

    for idx, command in enumerate(profile.command_samples[:10], start=1):
        add_task(
            task_id=f"sample-{idx}",
            title=f"Run sampled command {idx}",
            purpose="Execute a command extracted from project documentation.",
            command=command,
        )

    if profile.tests:
        add_task(
            task_id="run-tests",
            title="Run tests",
            purpose="Validate behavior before and after edits.",
            command="pytest",
        )

    if any(d["name"] == "model-training" for d in profile.domains):
        add_task(
            task_id="train-model",
            title="Run training entry point",
            purpose="Kick off model training with project defaults.",
            command="python train.py",
        )

    if any(d["name"] == "data-processing" for d in profile.domains):
        add_task(
            task_id="process-data",
            title="Run data pipeline",
            purpose="Execute preprocessing or ETL flow.",
            command="python pipeline.py",
        )

    if any(d["name"] == "image-enhancement" for d in profile.domains):
        add_task(
            task_id="enhance-images",
            title="Run image enhancement",
            purpose="Apply enhancement or denoise pipeline.",
            command="python enhance.py",
        )

    if any(d["name"] == "anomaly-detection" for d in profile.domains):
        add_task(
            task_id="detect-anomalies",
            title="Run anomaly detection",
            purpose="Execute anomaly scoring workflow.",
            command="python detect_anomaly.py",
        )

    if not catalog:
        add_task(
            task_id="inspect-project",
            title="Inspect package",
            purpose="Run a basic introspection command when no explicit command is discovered.",
            command="python -m pip list",
        )

    return catalog


def render_converter_runner() -> str:
    return textwrap.dedent(
        """\
        #!/usr/bin/env python3
        \"\"\"Execute named tasks from task_catalog.json in the source project root.\"\"\"

        from __future__ import annotations

        import argparse
        import json
        import subprocess
        from pathlib import Path


        def main() -> int:
            parser = argparse.ArgumentParser(description="Run a task by id from task_catalog.json")
            parser.add_argument("--task", required=True, help="Task id in task_catalog.json")
            parser.add_argument(
                "--catalog",
                default=str(Path(__file__).with_name("task_catalog.json")),
                help="Path to task catalog JSON",
            )
            parser.add_argument(
                "--project-root",
                required=True,
                help="Source project root where the command should execute",
            )
            parser.add_argument("--dry-run", action="store_true", help="Print command without executing")
            args = parser.parse_args()

            catalog_path = Path(args.catalog).resolve()
            project_root = Path(args.project_root).resolve()

            if not catalog_path.exists():
                raise SystemExit(f"Task catalog not found: {catalog_path}")
            if not project_root.exists():
                raise SystemExit(f"Project root not found: {project_root}")

            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            tasks = payload.get("tasks", [])
            selected = None
            for task in tasks:
                if task.get("id") == args.task:
                    selected = task
                    break
            if not selected:
                known = ", ".join(task.get("id", "?") for task in tasks)
                raise SystemExit(f"Unknown task id '{args.task}'. Known: {known}")

            command = str(selected.get("command", "")).strip()
            if not command:
                raise SystemExit(f"Task '{args.task}' has no executable command.")

            print(f"[TASK] {args.task}: {selected.get('title', '')}")
            print(f"[CMD ] {command}")
            print(f"[CWD ] {project_root}")

            if args.dry_run:
                return 0

            completed = subprocess.run(command, cwd=project_root, shell=True, check=False)
            return int(completed.returncode)


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def render_generated_skill_md(
    *,
    skill_name: str,
    project_name: str,
    project_root: str,
    description: str,
    profile: ProjectProfile,
    task_catalog: list[dict[str, str]],
) -> str:
    title = title_from_slug(skill_name)
    domain_names = [item["name"] for item in profile.domains[:5]]
    domain_text = ", ".join(domain_names) if domain_names else "general Python workflows"
    frameworks = ", ".join(profile.frameworks[:8]) if profile.frameworks else "project-specific dependencies"
    entry_points = "\n".join(f"- `{item}`" for item in profile.entry_points[:20]) or "- None detected"
    top_tasks = "\n".join(f"- `{item['id']}`: {item['title']} -> `{item['command']}`" for item in task_catalog[:12])
    top_tasks = top_tasks or "- No executable tasks discovered"

    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {description}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## Overview\n\n"
        f"Operate and evolve `{project_name}` as a reusable skill-backed project assistant.\n"
        "Use `references/source-project-profile.json` for factual project inventory and\n"
        "`scripts/task_runner.py` + `scripts/task_catalog.json` for repeatable command execution.\n\n"
        "## Source Context\n\n"
        f"- Source project root: `{project_root}`\n"
        f"- Primary domains: {domain_text}\n"
        f"- Framework signals: {frameworks}\n"
        f"- Python files detected: {len(profile.python_files)}\n"
        f"- Notebook files detected: {len(profile.notebooks)}\n"
        f"- Tests detected: {len(profile.tests)}\n\n"
        "## Workflow\n\n"
        "1. Read `references/source-project-profile.json` and `references/conversion-report.md`.\n"
        "2. Confirm the user's objective and map it to one or more task ids in `scripts/task_catalog.json`.\n"
        f'3. Run existing commands via `python scripts/task_runner.py --task <id> --project-root "{project_root}"`.\n'
        "4. For new tasks, add an entry to `scripts/task_catalog.json` and explain assumptions before execution.\n"
        "5. After code changes, run validation tasks (tests/lint/train-smoke) and capture outputs in the response.\n\n"
        "## Entry Points\n\n"
        f"{entry_points}\n\n"
        "## Task Catalog Highlights\n\n"
        f"{top_tasks}\n\n"
        "## Guardrails\n\n"
        "- Never assume environment parity; verify dependencies before execution.\n"
        "- Prefer minimally invasive edits and preserve existing project conventions.\n"
        "- For expensive workflows (training/inference on large data), ask for explicit approval.\n"
        "- Keep operational knowledge in `references/` and deterministic commands in `scripts/`.\n"
    )


def render_conversion_report(
    profile: ProjectProfile,
    skill_name: str,
    task_catalog: list[dict[str, str]],
    copy_source: str,
) -> str:
    domain_lines = "\n".join(
        f"- `{item['name']}` (score: {item['score']})"
        for item in profile.domains
    ) or "- No strong domain signals detected."
    framework_lines = "\n".join(f"- `{item}`" for item in profile.frameworks) or "- None detected"
    command_lines = "\n".join(f"- `{item['id']}`: `{item['command']}`" for item in task_catalog) or "- None"
    trunc_note = "Yes" if profile.truncated_scan else "No"

    return (
        "# Conversion Report\n\n"
        "## Summary\n\n"
        f"- Generated skill name: `{skill_name}`\n"
        f"- Source project: `{profile.project_root}`\n"
        f"- Files scanned: {profile.scanned_files}\n"
        f"- Scan truncated by max-file cap: {trunc_note}\n"
        f"- Source copy mode: `{copy_source}`\n\n"
        "## Domain Inference\n\n"
        f"{domain_lines}\n\n"
        "## Framework Inference\n\n"
        f"{framework_lines}\n\n"
        "## Generated Task Seeds\n\n"
        f"{command_lines}\n\n"
        "## Notes\n\n"
        "- Review task commands before execution in production environments.\n"
        "- Add project-specific safety checks if tasks mutate data or model artifacts.\n"
    )


def write_openai_yaml(skill_dir: Path, skill_name: str, project_name: str) -> None:
    display_name = title_from_slug(skill_name)
    short_description = safe_short_description(display_name)
    default_prompt = (
        f"Help me operate and modify the {project_name} Python project using the skill task catalog."
    )
    content = textwrap.dedent(
        f"""\
        interface:
          display_name: "{display_name}"
          short_description: "{short_description}"
          default_prompt: "{default_prompt}"
        """
    )
    target = skill_dir / "agents" / "openai.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def copy_source_snapshot(project_root: Path, destination_assets_dir: Path, mode: str) -> None:
    if mode == "none":
        return

    snapshot_dir = destination_assets_dir / "source-snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    if mode == "minimal":
        keep_files = {
            "README.md",
            "README.rst",
            "pyproject.toml",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "setup.cfg",
            "Pipfile",
            "environment.yml",
            "environment.yaml",
            ".env.example",
        }
        for item in project_root.iterdir():
            if item.is_file() and item.name in keep_files:
                shutil.copy2(item, snapshot_dir / item.name)
        return

    if mode == "full":

        def ignore_patterns(_: str, names: list[str]) -> set[str]:
            ignored = {name for name in names if name in IGNORE_DIRS}
            return ignored

        shutil.copytree(project_root, snapshot_dir / project_root.name, dirs_exist_ok=True, ignore=ignore_patterns)
        return

    raise ValueError(f"Unsupported copy mode: {mode}")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def select_choice(prompt: str, options: list[str], default: str) -> str:
    option_text = "/".join(options)
    answer = input(f"{prompt} [{option_text}] (default: {default}): ").strip().lower()
    if not answer:
        return default
    if answer in options:
        return answer
    print(f"Invalid choice '{answer}', using default '{default}'.")
    return default


def select_text(prompt: str, default: str) -> str:
    answer = input(f"{prompt} (default: {default}): ").strip()
    return answer or default


def convert_project(
    *,
    project_root: Path,
    output_root: Path,
    skill_name: str | None,
    mode: str,
    copy_source: str,
    max_files: int,
    interactive: bool,
    force: bool,
) -> Path:
    profile = profile_project(project_root, max_files=max_files)
    final_skill_name = skill_name or suggest_skill_name(profile.project_name)

    if interactive:
        print("\n[Interactive setup]")
        final_skill_name = slugify(select_text("Skill name", final_skill_name))
        if not final_skill_name.endswith("-skill"):
            final_skill_name = f"{final_skill_name}-skill"
        mode = select_choice("Conversion mode", ["quick", "balanced", "deep"], mode)
        copy_source = select_choice("Source copy mode", ["none", "minimal", "full"], copy_source)

    skill_dir = (output_root / final_skill_name).resolve()
    if skill_dir.exists():
        if not force:
            raise FileExistsError(
                f"Output skill directory already exists: {skill_dir}. "
                "Use --force to overwrite."
            )
        shutil.rmtree(skill_dir)

    description = make_description(profile.project_name, profile.domains, profile.frameworks)
    task_catalog = build_task_catalog(profile)

    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "agents").mkdir(parents=True, exist_ok=True)

    if copy_source != "none":
        (skill_dir / "assets").mkdir(parents=True, exist_ok=True)

    generated_md = render_generated_skill_md(
        skill_name=final_skill_name,
        project_name=profile.project_name,
        project_root=profile.project_root,
        description=description,
        profile=profile,
        task_catalog=task_catalog,
    )
    (skill_dir / "SKILL.md").write_text(generated_md, encoding="utf-8")

    write_openai_yaml(skill_dir, final_skill_name, profile.project_name)

    write_json(skill_dir / "references" / "source-project-profile.json", asdict(profile))
    write_json(
        skill_dir / "scripts" / "task_catalog.json",
        {"tasks": task_catalog, "source_project_root": profile.project_root},
    )
    (skill_dir / "scripts" / "task_runner.py").write_text(render_converter_runner(), encoding="utf-8")
    report = render_conversion_report(profile, final_skill_name, task_catalog, copy_source)
    (skill_dir / "references" / "conversion-report.md").write_text(report, encoding="utf-8")
    (skill_dir / "references" / "tree-preview.txt").write_text(
        "\n".join(profile.tree_preview) + "\n",
        encoding="utf-8",
    )

    mode_notes = {
        "quick": "Quick mode prioritizes fast scaffolding with minimal enrichment.",
        "balanced": "Balanced mode keeps defaults and generated references for iterative use.",
        "deep": "Deep mode is intended for large repositories and should be followed by manual curation.",
    }
    (skill_dir / "references" / "mode-notes.md").write_text(
        mode_notes[mode] + "\n",
        encoding="utf-8",
    )

    copy_source_snapshot(project_root, skill_dir / "assets", copy_source)

    return skill_dir


def run_analyze(args: argparse.Namespace) -> int:
    profile = profile_project(Path(args.project).resolve(), max_files=args.max_files)
    payload = asdict(profile)

    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(out_path, payload)
        print(f"[OK] Wrote profile JSON to: {out_path}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    return 0


def run_convert(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    skill_dir = convert_project(
        project_root=Path(args.project).resolve(),
        output_root=output_root,
        skill_name=args.skill_name,
        mode=args.mode,
        copy_source=args.copy_source,
        max_files=args.max_files,
        interactive=args.interactive,
        force=args.force,
    )

    print(f"[OK] Generated skill at: {skill_dir}")
    print(f"[TIP] Validate generated skill with:")
    print(
        "      python C:/Users/User/.codex/skills/.system/skill-creator/scripts/quick_validate.py "
        f"\"{skill_dir}\""
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Python projects into reusable Codex skill packages."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze a Python project and emit a profile JSON.",
    )
    analyze.add_argument("--project", required=True, help="Path to Python project root")
    analyze.add_argument("--out", help="Optional output JSON path")
    analyze.add_argument("--max-files", type=int, default=2500, help="Maximum files to scan")
    analyze.set_defaults(func=run_analyze)

    convert = subparsers.add_parser(
        "convert",
        help="Generate a new skill from a Python project profile.",
    )
    convert.add_argument("--project", required=True, help="Path to Python project root")
    convert.add_argument(
        "--output-root",
        required=True,
        help="Directory where the generated skill folder will be created",
    )
    convert.add_argument("--skill-name", help="Override generated skill name")
    convert.add_argument(
        "--mode",
        default="balanced",
        choices=["quick", "balanced", "deep"],
        help="Conversion depth profile",
    )
    convert.add_argument(
        "--copy-source",
        default="none",
        choices=["none", "minimal", "full"],
        help="How much source material to copy into generated skill/assets",
    )
    convert.add_argument("--max-files", type=int, default=2500, help="Maximum files to scan")
    convert.add_argument("--interactive", action="store_true", help="Ask interactive setup questions")
    convert.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    convert.set_defaults(func=run_convert)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 130
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
