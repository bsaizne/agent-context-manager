from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .project import require_initialized_project
from .utils import ContextError, read_utf8


@dataclass(frozen=True)
class ArchiveItem:
    index: int
    path: Path


def list_archives(project_path: Path) -> list[ArchiveItem]:
    directory = require_initialized_project(project_path) / "archive"
    directory.mkdir(parents=True, exist_ok=True)
    files = sorted(directory.glob("checkpoint-*.md"))
    return [ArchiveItem(index=i + 1, path=path) for i, path in enumerate(files)]


def read_archive(project_path: Path, name_or_index: str) -> str:
    items = list_archives(project_path)
    chosen: ArchiveItem | None = None
    if name_or_index.isdigit():
        index = int(name_or_index)
        chosen = next((item for item in items if item.index == index), None)
    else:
        chosen = next((item for item in items if item.path.name == name_or_index), None)

    if chosen is None:
        raise ContextError(
            "Archive checkpoint not found.",
            name_or_index,
            "Run:\n\nagent-context archive\n\nto list available checkpoints.",
        )
    return read_utf8(chosen.path)
