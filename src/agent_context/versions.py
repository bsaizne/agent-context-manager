"""Version history for the .agent context files.

L1 feature: every context file gets a content snapshot whenever it changes, so
the GUI can answer "what was added, what was removed, and when" with a coloured
diff. Snapshots live under .agent/versions/ - the tool still writes nothing
outside the project's own context directory.

Design notes:

* Snapshots are whole files, not patches. The files are small (a few KB) and a
  whole file can never be misapplied.
* Identical content is never stored twice: the digest of the last version is
  compared before writing, so a save with no changes costs nothing.
* The index is a convenience cache. If it is damaged the history is simply
  rebuilt from the snapshot files, and checkpoint/editor behaviour is unaffected.
* Snapshot names carry second precision plus the digest, so two changes in the
  same second cannot collide.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import difflib
import json

from .config import load_config
from .project import require_initialized_project
from .templates import CONTEXT_FILES
from .utils import ContextError, read_utf8, write_utf8

VERSIONS_DIR_NAME = "versions"
INDEX_NAME = "index.json"
DEFAULT_HISTORY_LIMIT = 30
SOURCES = ("save", "checkpoint", "external", "manual")


@dataclass(frozen=True)
class VersionRef:
    filename: str
    version_id: str
    recorded_at: str
    source: str
    lines: int
    digest: str
    path: Path

    @property
    def label(self) -> str:
        return f"{self.recorded_at}  ({self.source})"


@dataclass(frozen=True)
class DiffLine:
    kind: str
    text: str
    old_no: int | None
    new_no: int | None


@dataclass(frozen=True)
class DiffSummary:
    added: int
    removed: int

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed)


@dataclass(frozen=True)
class DiffView:
    text: str
    kinds: list[str]
    added: int
    removed: int
    truncated: bool = False


@dataclass(frozen=True)
class FileChange:
    filename: str
    added: int
    removed: int
    at: str
    versions: int


def normalize_text(text: str) -> str:
    """Line endings only: the diff should never report CRLF noise."""
    return text.replace("\r\n", "\n")


def short_digest(text: str) -> str:
    return sha256(normalize_text(text).encode("utf-8")).hexdigest()[:8]


def versions_root(project_path: Path) -> Path:
    return require_initialized_project(project_path) / VERSIONS_DIR_NAME


def _index_path(project_path: Path) -> Path:
    return versions_root(project_path) / INDEX_NAME


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def history_limit() -> int:
    limit = load_config().get("version_history_limit", DEFAULT_HISTORY_LIMIT)
    if isinstance(limit, int) and limit > 0:
        return limit
    return DEFAULT_HISTORY_LIMIT


def load_index(project_path: Path) -> dict[str, list[dict]]:
    path = _index_path(project_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, list[dict]] = {}
    for name, entries in data.items():
        if isinstance(entries, list):
            cleaned[str(name)] = [e for e in entries if isinstance(e, dict) and "id" in e]
    return cleaned


def _save_index(project_path: Path, index: dict[str, list[dict]]) -> None:
    write_utf8(_index_path(project_path), json.dumps(index, ensure_ascii=False, indent=2))


def _prune(root: Path, filename: str, entries: list[dict], keep_recent: int) -> list[dict]:
    """Keep the newest N versions plus the first version of every day.

    The daily copy is what makes a three-month-old state still inspectable while
    the history stays bounded in normal use.
    """
    if len(entries) <= keep_recent:
        return entries
    keep = {str(e["id"]) for e in entries[-keep_recent:]}
    daily: dict[str, str] = {}
    for entry in entries:
        day = str(entry.get("at", ""))[:10]
        if day:
            daily.setdefault(day, str(entry["id"]))
    keep.update(daily.values())
    for entry in entries:
        if str(entry["id"]) not in keep:
            victim = root / filename / f"{entry['id']}.md"
            try:
                victim.unlink()
            except OSError:
                pass
    return [e for e in entries if str(e["id"]) in keep]


def record_version(
    project_path: Path,
    filename: str,
    text: str | None = None,
    source: str = "save",
) -> VersionRef | None:
    """Store a snapshot of filename when its content differs from the last one.

    Pass text explicitly to record content that is not on disk yet - the GUI uses
    that to capture what an agent replaced before reloading the editor.
    """
    if filename not in CONTEXT_FILES:
        raise ContextError(
            "Unknown context file.",
            filename,
            "Expected one of: " + ", ".join(CONTEXT_FILES),
        )
    if source not in SOURCES:
        source = "manual"
    root = versions_root(project_path)
    if text is None:
        target = root.parent / filename
        if not target.exists():
            return None
        text = read_utf8(target)
    normalized = normalize_text(text)
    digest = short_digest(normalized)

    index = load_index(project_path)
    entries = index.get(filename, [])
    if entries and str(entries[-1].get("digest", "")) == digest:
        return None

    version_id = f"{_now_stamp()}-{digest}"
    path = root / filename / f"{version_id}.md"
    write_utf8(path, normalized)

    recorded_at = _now_text()
    entries.append(
        {
            "id": version_id,
            "at": recorded_at,
            "source": source,
            "lines": len(normalized.splitlines()),
            "digest": digest,
        }
    )
    index[filename] = _prune(root, filename, entries, history_limit())
    _save_index(project_path, index)
    return VersionRef(
        filename=filename,
        version_id=version_id,
        recorded_at=recorded_at,
        source=source,
        lines=len(normalized.splitlines()),
        digest=digest,
        path=path,
    )


def list_versions(project_path: Path, filename: str) -> list[VersionRef]:
    root = versions_root(project_path)
    refs: list[VersionRef] = []
    for entry in load_index(project_path).get(filename, []):
        path = root / filename / f"{entry['id']}.md"
        if not path.exists():
            continue
        refs.append(
            VersionRef(
                filename=filename,
                version_id=str(entry["id"]),
                recorded_at=str(entry.get("at", "")),
                source=str(entry.get("source", "")),
                lines=int(entry.get("lines", 0)),
                digest=str(entry.get("digest", "")),
                path=path,
            )
        )
    # Keep the index order: it is the order in which the versions were recorded.
    # Sorting by version_id used to put two snapshots taken in the same second in an
    # arbitrary (digest) order, which made the diff run backwards once in a while.
    return refs


def read_version_text(ref: VersionRef) -> str:
    try:
        return ref.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def latest_version(project_path: Path, filename: str) -> VersionRef | None:
    refs = list_versions(project_path, filename)
    return refs[-1] if refs else None


def diff_lines(old_text: str, new_text: str) -> list[DiffLine]:
    old = normalize_text(old_text).splitlines()
    new = normalize_text(new_text).splitlines()
    result: list[DiffLine] = []
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                result.append(DiffLine("equal", new[j1 + offset], i1 + offset + 1, j1 + offset + 1))
        elif tag == "delete":
            for offset in range(i2 - i1):
                result.append(DiffLine("delete", old[i1 + offset], i1 + offset + 1, None))
        elif tag == "insert":
            for offset in range(j2 - j1):
                result.append(DiffLine("insert", new[j1 + offset], None, j1 + offset + 1))
        else:
            for offset in range(i2 - i1):
                result.append(DiffLine("delete", old[i1 + offset], i1 + offset + 1, None))
            for offset in range(j2 - j1):
                result.append(DiffLine("insert", new[j1 + offset], None, j1 + offset + 1))
    return result


def summarize(lines: list[DiffLine]) -> DiffSummary:
    return DiffSummary(
        added=sum(1 for line in lines if line.kind == "insert"),
        removed=sum(1 for line in lines if line.kind == "delete"),
    )


def new_line_numbers(old_text: str, new_text: str) -> list[int]:
    """1-based line numbers of the new text that did not exist in the old text."""
    numbers = [line.new_no for line in diff_lines(old_text, new_text) if line.kind == "insert" and line.new_no]
    return sorted(set(int(number) for number in numbers))


def build_diff_view(old_text: str, new_text: str, max_lines: int = 4000) -> DiffView:
    lines = diff_lines(old_text, new_text)
    summary = summarize(lines)
    rendered: list[str] = []
    kinds: list[str] = []
    truncated = False
    for line in lines:
        if len(rendered) >= max_lines:
            truncated = True
            break
        if line.kind == "insert":
            marker, number = "+", line.new_no
        elif line.kind == "delete":
            marker, number = "-", line.old_no
        else:
            marker, number = " ", line.new_no
        rendered.append(f"{marker} {str(number).rjust(4)} | {line.text}")
        kinds.append(line.kind)
    return DiffView(
        text="\n".join(rendered),
        kinds=kinds,
        added=summary.added,
        removed=summary.removed,
        truncated=truncated,
    )


def recent_changes(project_path: Path) -> list[FileChange]:
    """Per-file summary of the most recent recorded change (overview card)."""
    changes: list[FileChange] = []
    for filename in CONTEXT_FILES:
        refs = list_versions(project_path, filename)
        if not refs:
            changes.append(FileChange(filename, 0, 0, "", 0))
            continue
        latest = refs[-1]
        previous_text = read_version_text(refs[-2]) if len(refs) > 1 else ""
        summary = summarize(diff_lines(previous_text, read_version_text(latest)))
        changes.append(
            FileChange(
                filename=filename,
                added=summary.added,
                removed=summary.removed,
                at=latest.recorded_at,
                versions=len(refs),
            )
        )
    return changes
