from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
import json
import re

from .project import require_initialized_project
from .templates import CONTEXT_FILES
from .utils import ContextError
from .versions import VERSIONS_DIR_NAME

TRANSFER_SUFFIX = ".agentctx.json"
BACKUP_DIR_PREFIX = "import-backup"

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class TransferStats:
    files: list[str]
    total_chars: int
    estimated_tokens: int
    archive_files: int = 0
    archive_chars: int = 0


@dataclass(frozen=True)
class ImportReport:
    target_dir: Path
    created: list[str]
    overwritten: list[str]
    unchanged: list[str]
    kept: list[str]
    backup_dir: Path | None

    @property
    def changed(self) -> int:
        return len(self.created) + len(self.overwritten)


def chars_to_tokens(char_count: int) -> int:
    """Rough token estimate: about 4 characters per token for mixed CJK/Latin."""
    return max(1, char_count // 4)


def estimate_tokens(text: str) -> int:
    """Rough token estimate for a text blob."""
    return chars_to_tokens(len(text))


def _try_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def context_token_stats(project_path: Path) -> TransferStats:
    """Estimate the context a fresh agent actually loads.

    Only the files used by resume (the .agent Markdown files) plus AGENTS.md are
    counted. .agent/archive is reported separately: resume never reads it and it
    grows forever, so folding it into the headline number made the overview
    counter meaningless after a few weeks of work.
    """
    directory = require_initialized_project(project_path)
    files: list[str] = []
    total_chars = 0
    for name in CONTEXT_FILES:
        text = _try_read(directory / name)
        if text is None:
            continue
        files.append(f".agent/{name}")
        total_chars += len(text)

    agents_text = _try_read(directory.parent / "AGENTS.md")
    if agents_text is not None:
        files.append("AGENTS.md")
        total_chars += len(agents_text)

    archive_files = 0
    archive_chars = 0
    archive_dir = directory / "archive"
    if archive_dir.is_dir():
        for path in sorted(archive_dir.rglob("*.md")):
            text = _try_read(path)
            if text is None:
                continue
            archive_files += 1
            archive_chars += len(text)

    return TransferStats(
        files=files,
        total_chars=total_chars,
        estimated_tokens=chars_to_tokens(total_chars),
        archive_files=archive_files,
        archive_chars=archive_chars,
    )


def export_project(project_path: Path) -> Path:
    """Export .agent/ plus AGENTS.md into a single portable JSON file."""
    directory = require_initialized_project(project_path)
    payload: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        # .agent/versions holds the change history: it grows with every edit and is
        # machine-local noise in a transfer file, so exports carry current state only.
        if VERSIONS_DIR_NAME in path.relative_to(directory).parts:
            continue
        if path.is_file():
            rel = path.relative_to(directory).as_posix()
            payload[f".agent/{rel}"] = path.read_text(encoding="utf-8")
    agents_path = directory.parent / "AGENTS.md"
    if agents_path.exists():
        payload["AGENTS.md"] = agents_path.read_text(encoding="utf-8")

    project_name = directory.parent.name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = directory.parent / f"{project_name}-{timestamp}{TRANSFER_SUFFIX}"
    doc = {
        "format": "agent-context-transfer",
        "version": 1,
        "project": project_name,
        "exported_at": timestamp,
        "files": payload,
    }
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _safe_relative(rel: str) -> PurePosixPath:
    """Reject absolute paths and parent-directory escapes in a transfer payload."""
    raw = str(rel).replace("\\", "/")
    if not raw or raw.startswith("/") or _WINDOWS_DRIVE.match(raw):
        raise ContextError(
            "Invalid transfer file.",
            f"Unsafe path: {rel!r}",
            "Transfer files may only contain project-relative paths.",
        )
    candidate = PurePosixPath(raw)
    if ".." in candidate.parts:
        raise ContextError(
            "Invalid transfer file.",
            f"Path escapes the target directory: {rel!r}",
            "Remove '..' segments from the transfer file.",
        )
    return candidate


def import_project(transfer_file: Path, target_dir: Path) -> ImportReport:
    """Import a .agentctx.json transfer file into target_dir.

    Safety rules learned from a real payload: every path must stay inside the
    target project, files that would be replaced are first copied under
    .agent/archive/import-backup-<stamp>/ so nothing is lost, and an existing
    AGENTS.md is kept instead of overwritten (init_project makes the same
    promise to the user).
    """
    if not transfer_file.exists():
        raise ContextError("Transfer file not found.", str(transfer_file))
    try:
        doc = json.loads(transfer_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContextError("Invalid transfer file.", str(exc)) from exc
    if doc.get("format") != "agent-context-transfer":
        raise ContextError("Not an Agent Context Manager transfer file.", f"format={doc.get('format')!r}")
    files: dict[str, str] = doc.get("files", {})
    if not files:
        raise ContextError("Transfer file contains no files.")

    root = Path(target_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root / ".agent" / "archive" / f"{BACKUP_DIR_PREFIX}-{stamp}"

    created: list[str] = []
    overwritten: list[str] = []
    unchanged: list[str] = []
    kept: list[str] = []

    for rel, content in files.items():
        parts = _safe_relative(rel)
        target = (root / parts).resolve()
        if not target.is_relative_to(root):
            raise ContextError(
                "Invalid transfer file.",
                f"Refusing to write outside the target directory: {rel}",
                "Edit the transfer file so every path stays inside the target project.",
            )

        current = _try_read(target) if target.exists() else None
        if target.exists() and current == content:
            unchanged.append(parts.as_posix())
            continue
        if parts.as_posix() == "AGENTS.md" and target.exists():
            kept.append(parts.as_posix())
            continue
        if target.exists():
            backup = backup_root / parts
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(target.read_bytes())
            overwritten.append(parts.as_posix())
        else:
            created.append(parts.as_posix())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return ImportReport(
        target_dir=root,
        created=created,
        overwritten=overwritten,
        unchanged=unchanged,
        kept=kept,
        backup_dir=backup_root if overwritten else None,
    )
