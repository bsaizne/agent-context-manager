from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .git import GitInfo, collect_git_info
from .project import context_file_paths, require_initialized_project
from .state import load_snapshot
from .utils import count_markdown_tasks, extract_heading_by_prefix, first_nonempty_line


@dataclass(frozen=True)
class ProjectStatus:
    project_path: Path
    context_files: dict[str, bool]
    phase: str
    task: str
    git_info: GitInfo
    last_checkpoint: str | None
    p0_count: int
    p1_count: int
    p2_count: int


def get_status(project_path: Path) -> ProjectStatus:
    directory = require_initialized_project(project_path)
    snapshot = load_snapshot(project_path)
    files = context_file_paths(project_path)
    archive_files = sorted((directory / "archive").glob("checkpoint-*.md"))

    todo = snapshot.todo_text
    p0 = extract_heading_by_prefix(todo, "P0")
    p1 = extract_heading_by_prefix(todo, "P1")
    p2 = extract_heading_by_prefix(todo, "P2")

    return ProjectStatus(
        project_path=project_path,
        context_files={name: path.exists() for name, path in files.items()},
        phase=first_nonempty_line(snapshot.section("Current Phase"), "Unknown"),
        task=first_nonempty_line(snapshot.section("Current Task"), "Unknown"),
        git_info=collect_git_info(project_path),
        last_checkpoint=archive_files[-1].stem.replace("checkpoint-", "") if archive_files else None,
        p0_count=count_markdown_tasks(p0),
        p1_count=count_markdown_tasks(p1),
        p2_count=count_markdown_tasks(p2),
    )
