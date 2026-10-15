from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .templates import AGENT_DIR_NAME, CONTEXT_FILES, agents_template, file_templates
from .utils import ContextError, write_utf8


@dataclass(frozen=True)
class InitResult:
    project_path: Path
    agent_dir: Path
    created: list[str]
    skipped: list[str]


def resolve_project_path(path: str | Path | None = None) -> Path:
    candidate = Path(path) if path is not None else Path.cwd()
    return candidate.expanduser().resolve()


def agent_dir(project_path: Path) -> Path:
    return project_path / AGENT_DIR_NAME


def find_initialized_project_path(path: str | Path | None = None) -> Path | None:
    """Find the nearest initialized project root at or above ``path``."""
    candidate = resolve_project_path(path)
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / AGENT_DIR_NAME).is_dir():
            return directory
    return None


def require_existing_project(project_path: Path) -> None:
    if not project_path.exists():
        raise ContextError(
            "Project directory does not exist.",
            str(project_path),
            "Create the directory first or pass an existing project path.",
        )
    if not project_path.is_dir():
        raise ContextError(
            "Project path is not a directory.",
            str(project_path),
            "Pass a project directory.",
        )


def require_initialized_project(project_path: Path) -> Path:
    require_existing_project(project_path)
    directory = agent_dir(project_path)
    if not directory.exists():
        raise ContextError(
            ".agent directory not found.",
            "This project has not been initialized.",
            "Run:\n\nagent-context init",
        )
    if not directory.is_dir():
        raise ContextError(
            ".agent exists but is not a directory.",
            str(directory),
            "Rename the file and run:\n\nagent-context init",
        )
    return directory


def init_project(path: str | Path | None = None) -> InitResult:
    project_path = resolve_project_path(path)
    require_existing_project(project_path)

    directory = agent_dir(project_path)
    created: list[str] = []
    skipped: list[str] = []

    if not directory.exists():
        directory.mkdir(parents=True)
        created.append(".agent/")
    elif not directory.is_dir():
        raise ContextError(
            "Unable to initialize project.",
            ".agent exists but is not a directory.",
            "Rename the file and run:\n\nagent-context init",
        )
    else:
        skipped.append(".agent/")

    archive_dir = directory / "archive"
    if not archive_dir.exists():
        archive_dir.mkdir(parents=True)
        created.append(".agent/archive/")
    else:
        skipped.append(".agent/archive/")

    for filename, content in file_templates(project_path).items():
        target = directory / filename
        if target.exists():
            skipped.append(f".agent/{filename}")
            continue
        write_utf8(target, content)
        created.append(f".agent/{filename}")

    agents_path = project_path / "AGENTS.md"
    if agents_path.exists():
        skipped.append("AGENTS.md already exists. Skipped.")
    else:
        write_utf8(agents_path, agents_template())
        created.append("AGENTS.md")

    return InitResult(project_path=project_path, agent_dir=directory, created=created, skipped=skipped)


def context_file_paths(project_path: Path) -> dict[str, Path]:
    directory = agent_dir(project_path)
    return {name: directory / name for name in CONTEXT_FILES}
