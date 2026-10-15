from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable


class ContextError(Exception):
    """User-facing error with a reason and suggested recovery."""

    def __init__(
        self,
        message: str,
        reason: str | None = None,
        suggestion: str | None = None,
        exit_code: int = 1,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason
        self.suggestion = suggestion
        self.exit_code = exit_code


@dataclass(frozen=True)
class FileStatus:
    path: Path
    exists: bool
    readable_utf8: bool
    error: str | None = None


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def now_stamp() -> str:
    # Second precision. A minute-level stamp let two checkpoints created in the
    # same minute collide on one archive filename: the second run silently
    # replaced the first archive, while the changelog note was de-duplicated,
    # so nothing in the UI or the log looked wrong. unique_path() covers the
    # remaining edge case of two runs inside the same second.
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def unique_path(path: Path) -> Path:
    """Return the given path, or the first free name-2.ext / name-3.ext variant."""
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ContextError(
        f"Unable to create {path.name}.",
        "Too many files with the same name.",
        "Remove old archives or run:\n\nagent-context archive",
    )


def today_text() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else f"{text}\n"


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContextError(
            f"Unable to read {path.name}.",
            "File does not exist.",
            "Run:\n\nagent-context init",
        ) from exc
    except UnicodeDecodeError as exc:
        raise ContextError(
            f"Unable to read {path.name}.",
            "File encoding is invalid.",
            "Run:\n\nagent-context doctor",
        ) from exc
    except OSError as exc:
        raise ContextError(
            f"Unable to read {path.name}.",
            str(exc),
            "Check file permissions or run:\n\nagent-context doctor",
        ) from exc


def write_utf8(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(ensure_trailing_newline(text), encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError as exc:
        raise ContextError(
            f"Unable to write {path.name}.",
            str(exc),
            "Check file permissions and try again.",
        ) from exc


def check_utf8(path: Path) -> FileStatus:
    if not path.exists():
        return FileStatus(path=path, exists=False, readable_utf8=False)
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return FileStatus(path=path, exists=True, readable_utf8=False, error=str(exc))
    except OSError as exc:
        return FileStatus(path=path, exists=True, readable_utf8=False, error=str(exc))
    return FileStatus(path=path, exists=True, readable_utf8=True)


def extract_section(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n?(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def extract_heading_by_prefix(markdown: str, prefix: str) -> str:
    """Return the body of the first `##` heading whose text starts with ``prefix``.

    Do not use ``.*$`` for the heading line here. This pattern is compiled with
    re.DOTALL (needed so the captured body can span lines), and under DOTALL the
    dot also matches newlines -- ``.*$`` therefore swallows the remainder of the
    document and the capture group always comes back empty. That made every
    `## P0`/`## P1`/`## P2` section in TODO.md read as empty, so `status` and
    `resume` reported zero pending tasks for every project. Match the heading's
    own line with an explicit non-newline class instead.
    """
    pattern = re.compile(
        rf"^##[ \t]+{re.escape(prefix)}[^\n]*\n?(.*?)(?=^##[ \t]+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def update_section(markdown: str, heading: str, content: str) -> str:
    replacement = f"## {heading}\n\n{content.strip()}\n"
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n?(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(markdown):
        return pattern.sub(replacement, markdown).strip() + "\n"
    return markdown.rstrip() + f"\n\n{replacement}"


def first_nonempty_line(text: str, default: str = "") -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return default


def compact_lines(text: str, limit: int = 6) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return lines
    return [*lines[:limit], f"... ({len(lines) - limit} more line(s))"]


def count_markdown_tasks(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.lstrip().startswith("- ["))


def bullet_list(values: Iterable[str]) -> str:
    items = [value.strip() for value in values if value.strip()]
    if not items:
        return "- None."
    return "\n".join(f"- {item}" for item in items)
