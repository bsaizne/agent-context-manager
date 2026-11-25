from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable

from .project import context_file_paths, require_initialized_project
from .utils import ContextError, extract_heading_by_prefix, extract_section, now_text, read_utf8, today_text, update_section, write_utf8
from .versions import record_version

REQUIRED_STATE_SECTIONS = [
    "Project",
    "Current Phase",
    "Current Task",
    "Next Actions",
    "Last Updated",
]

OPTIONAL_STATE_SECTIONS = [
    "Completed",
    "Current Problem",
    "Current Implementation",
    "Current Decision",
    "Important Constraints",
    "Known Issues",
]

SECTION_ORDER = [
    "Project",
    "Current Phase",
    "Current Task",
    "Completed",
    "Current Problem",
    "Current Implementation",
    "Current Decision",
    "Next Actions",
    "Important Constraints",
    "Known Issues",
    "Last Updated",
]

SECTION_DEFAULTS = {
    # Every section in SECTION_ORDER needs an entry. A missing key used to fall
    # back to "", which produced a different (empty) body than an existing empty
    # section did, so auto_repair_state() was not idempotent.
    "Project": "- 未填写：请补充项目名称与目标。",
    "Current Phase": "- 未填写：请补充当前阶段。",
    "Current Task": "- 未填写：请补充当前任务。",
    "Completed": "- None recorded.",
    "Current Problem": "- None identified.",
    "Current Implementation": "- No implementation details recorded.",
    "Current Decision": "- None recorded.",
    "Next Actions": "- 定义下一步行动。",
    "Important Constraints": "- None recorded.",
    "Known Issues": "- None known.",
    "Last Updated": "- 未记录。",
}

TODO_SECTIONS = ["P0", "P1", "P2", "Blocked"]

DUPLICATE_SECTION_NOTE = (
    "<!-- 结构修复：同名章节在源文件中重复出现，以下内容为合并保留。 -->"
)


@dataclass(frozen=True)
class StateSnapshot:
    project_path: Path
    state_text: str
    todo_text: str

    def section(self, name: str) -> str:
        return extract_section(self.state_text, name)

    def todo_section(self, prefix: str) -> str:
        return extract_heading_by_prefix(self.todo_text, prefix)


def load_snapshot(project_path: Path) -> StateSnapshot:
    directory = require_initialized_project(project_path)
    state_path = directory / "STATE.md"
    todo_path = directory / "TODO.md"
    state_text = read_utf8(state_path)
    todo_text = read_utf8(todo_path)
    validate_state_text(state_text)
    validate_todo_text(todo_text)
    return StateSnapshot(project_path=project_path, state_text=state_text, todo_text=todo_text)


def validate_state_text(text: str) -> list[str]:
    """Validate required sections; return list of missing optional sections."""
    missing_required = [s for s in REQUIRED_STATE_SECTIONS if not _has_section(text, s)]
    if missing_required:
        raise ContextError(
            "STATE.md needs attention",
            f"Missing required sections: {', '.join(missing_required)}",
            "Run:\n\nagent-context doctor\n\nThen repair STATE.md.",
        )
    missing_optional = [s for s in OPTIONAL_STATE_SECTIONS if not _has_section(text, s)]
    return missing_optional


def _has_section(text: str, heading: str) -> bool:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    return bool(pattern.search(text))


def validate_todo_text(text: str) -> None:
    if not re.search(r"^#\s+TODO\s*$", text, re.MULTILINE):
        raise ContextError(
            "TODO.md appears to be damaged.",
            "Missing # TODO heading.",
            "Run:\n\nagent-context doctor",
        )


def auto_repair_state(text: str) -> str:
    """Add missing optional sections with defaults, preserving existing content."""
    lines = text.replace("\r\n", "\n").split("\n")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            continue
        m = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
        if m:
            current = m.group(1)
            if current in sections:
                # The same heading occurs more than once. Merge the blocks
                # instead of resetting the list: `sections[current] = []`
                # silently threw away everything the first occurrence held
                # (a 75-line `## Current Task` section was lost this way).
                sections[current].extend(["", DUPLICATE_SECTION_NOTE, ""])
            else:
                sections[current] = []
        elif current is not None:
            sections[current].append(line)

    output = ["# PROJECT STATE", ""]
    for name in SECTION_ORDER:
        content = sections.get(name)
        output.append(f"## {name}")
        # Do not insert a blank line here: existing blocks already start with one,
        # and adding another each pass made the repair non-idempotent.
        if content is None:
            default = SECTION_DEFAULTS.get(name, "")
            if default:
                output.append("")
                output.append(default)
        else:
            while content and not content[-1].strip():
                content.pop()
            output.extend(content)
        output.append("")
    return "\n".join(output).rstrip() + "\n"


def touch_state_last_updated(project_path: Path) -> str:
    paths = context_file_paths(project_path)
    state_path = paths["STATE.md"]
    state_text = read_utf8(state_path)
    # Repair first, validate afterwards. Validating first raised on missing
    # required sections -- which is exactly the damage auto_repair_state() exists
    # to fix -- so the repair code below was unreachable and `checkpoint` could
    # never recover a damaged STATE.md. A file that is still broken after repair
    # fails loudly without being written.
    repaired = auto_repair_state(state_text)
    updated = update_section(repaired, "Last Updated", now_text())
    validate_state_text(updated)
    write_utf8(state_path, updated)
    return updated


@dataclass(frozen=True)
class RepairReport:
    project_path: Path
    state_changed: bool
    state_missing_required: list[str]
    state_missing_optional: list[str]
    state_duplicate_sections: list[str]
    todo_heading_added: bool
    todo_changed: bool
    todo_duplicate_sections: list[str]


def ensure_todo_heading(text: str) -> str:
    """Guarantee TODO.md carries a top-level `# TODO` heading."""
    if re.search(r"^#\s+TODO\s*$", text, re.MULTILINE):
        return text
    return "# TODO\n\n" + text.lstrip("\n")


def ensure_todo_heading_file(project_path: Path) -> bool:
    """Guarantee TODO.md carries a top-level # TODO heading; True when changed.

    STATE.md is repaired at the start of a checkpoint, but a missing TODO.md
    heading used to abort the whole run *after* STATE.md had already been
    rewritten: a half-updated project with no archive and no changelog entry.
    """
    todo_path = context_file_paths(project_path)["TODO.md"]
    text = read_utf8(todo_path)
    repaired = ensure_todo_heading(text)
    if repaired == text:
        return False
    write_utf8(todo_path, repaired)
    return True


def find_duplicate_sections(text: str) -> list[str]:
    """Names of `##` sections that occur more than once."""
    seen: dict[str, int] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
        if m:
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    return [name for name, count in seen.items() if count > 1]


def todo_section_key(heading: str) -> str:
    """Group TODO headings by priority: P0 - Current and P0 - Dup share P0."""
    cleaned = heading.strip()
    for prefix in TODO_SECTIONS:
        if cleaned.startswith(prefix):
            return prefix
    return cleaned


def find_duplicate_todo_sections(text: str) -> list[str]:
    """Priority groups (P0/P1/P2/Blocked) that appear more than once in TODO.md."""
    seen: dict[str, int] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        match = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
        if match:
            key = todo_section_key(match.group(1))
            seen[key] = seen.get(key, 0) + 1
    return [name for name, count in seen.items() if count > 1]


def merge_duplicate_sections(
    text: str,
    key_fn: Callable[[str], str] | None = None,
    note: str = DUPLICATE_SECTION_NOTE,
) -> str:
    """Merge repeated ## sections into their first occurrence, keeping every line.

    extract_heading_by_prefix() returns the first matching heading only, so a second
    P0 block in TODO.md was parsed as nothing at all: its tasks silently disappeared
    from status and from resume. key_fn decides which headings belong together.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    head: list[str] = []
    order: list[str] = []
    titles: dict[str, str] = {}
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        match = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
        if match:
            name = match.group(1)
            key = key_fn(name) if key_fn is not None else name
            if key in blocks:
                blocks[key].extend(["", note, ""])
            else:
                blocks[key] = []
                titles[key] = name
                order.append(key)
            current = key
        elif current is None:
            head.append(line)
        else:
            blocks[current].append(line)

    output = list(head)
    while output and not output[-1].strip():
        output.pop()
    output.append("")
    for key in order:
        content = blocks[key]
        while content and not content[-1].strip():
            content.pop()
        output.append(f"## {titles[key]}")
        output.extend(content)
        output.append("")
    return "\n".join(output).rstrip() + "\n"


def repair_project(project_path: Path) -> RepairReport:
    """Rewrite STATE.md / TODO.md into the protocol structure without losing content."""
    require_initialized_project(project_path)
    paths = context_file_paths(project_path)

    state_path = paths["STATE.md"]
    state_text = read_utf8(state_path)
    missing_required = [name for name in REQUIRED_STATE_SECTIONS if not _has_section(state_text, name)]
    missing_optional = [name for name in OPTIONAL_STATE_SECTIONS if not _has_section(state_text, name)]
    duplicates = find_duplicate_sections(state_text)

    repaired_state = auto_repair_state(state_text)
    state_changed = repaired_state != state_text.replace("\r\n", "\n")
    if state_changed:
        write_utf8(state_path, repaired_state)

    todo_path = paths["TODO.md"]
    todo_text = read_utf8(todo_path)
    todo_duplicates = find_duplicate_todo_sections(todo_text)
    todo_heading_added = not re.search(r"^#\s+TODO\s*$", todo_text, re.MULTILINE)
    repaired_todo = ensure_todo_heading(todo_text)
    if todo_duplicates:
        # A second P0 block is invisible to extract_heading_by_prefix(), which
        # returns the first match only. Merge by priority, exactly like STATE.md.
        repaired_todo = merge_duplicate_sections(repaired_todo, key_fn=todo_section_key)
    todo_changed = repaired_todo != todo_text.replace("\r\n", "\n")
    if todo_changed:
        write_utf8(todo_path, repaired_todo)

    return RepairReport(
        project_path=project_path,
        state_changed=state_changed,
        state_missing_required=missing_required,
        state_missing_optional=missing_optional,
        state_duplicate_sections=duplicates,
        todo_heading_added=todo_heading_added,
        todo_changed=todo_changed,
        todo_duplicate_sections=todo_duplicates,
    )


_COMPLETED_TODO_RE = re.compile(r"^([ \t]*)-[ \t]+\[[xX]\](?:[ \t]+(.*))?$")


@dataclass(frozen=True)
class ArchiveTodosReport:
    project_path: Path
    archived_count: int
    archived_items: list[str]
    todo_lines_before: int
    todo_lines_after: int


def count_completed_todos(todo_text: str) -> int:
    """Count checked (- [x] / - [X]) top-level task entries in TODO.md."""
    return sum(
        1
        for line in todo_text.replace("\r\n", "\n").split("\n")
        if _COMPLETED_TODO_RE.match(line)
    )


def _split_completed_todos(todo_text: str) -> tuple[str, list[tuple[str, list[str]]]]:
    """Split checked task entries (including indented sub-lines) out of TODO.md.

    Returns (remaining_todo_text, archived_entries) where each archived entry is
    (section_label, raw_lines).
    """
    lines = todo_text.replace("\r\n", "\n").split("\n")
    kept: list[str] = []
    archived: list[tuple[str, list[str]]] = []
    current_section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^##[ \t]+(.+?)[ \t]*$", line)
        if heading:
            current_section = todo_section_key(heading.group(1))
            kept.append(line)
            i += 1
            continue
        match = _COMPLETED_TODO_RE.match(line)
        if match:
            base_indent = len(match.group(1).expandtabs(4))
            body = (match.group(2) or "").strip()
            entry_lines = [body] if body else []
            i += 1
            # Carry any deeper-indented continuation or sub-bullet lines with the task
            # so archiving never leaves orphaned indented fragments behind in TODO.md.
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    # Look ahead: only swallow a blank line if followed by a deeper-indented line.
                    if i + 1 < len(lines):
                        after = lines[i + 1]
                        after_indent = len(after[: len(after) - len(after.lstrip(" \t"))].expandtabs(4))
                        if after.strip() and after_indent > base_indent:
                            entry_lines.append("")
                            i += 1
                            continue
                    break
                nxt_indent = len(nxt[: len(nxt) - len(nxt.lstrip(" \t"))].expandtabs(4))
                if nxt_indent > base_indent:
                    entry_lines.append(nxt.rstrip())
                    i += 1
                else:
                    break
            if entry_lines:
                archived.append((current_section, entry_lines))
            continue
        kept.append(line)
        i += 1

    # Collapse runs of 3+ blank lines left behind where completed blocks were removed.
    cleaned: list[str] = []
    blank_run = 0
    for line in kept:
        if not line.strip():
            blank_run += 1
            if blank_run <= 1:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(line)
    remaining = "\n".join(cleaned).rstrip() + "\n"
    return remaining, archived


def _append_archived_todos_to_changelog(changelog_text: str, entries: list[tuple[str, list[str]]]) -> str:
    """Append archived TODO entries to CHANGELOG.md under today's archive heading.

    Each entry preserves its original priority tag and wording so an agent can
    find prior completed work with a single keyword grep instead of reading the
    whole changelog.
    """
    text = changelog_text.replace("\r\n", "\n")
    if "No changes recorded yet." in text:
        text = text.replace("No changes recorded yet.", "").rstrip()

    formatted: list[str] = []
    for section, entry_lines in entries:
        prefix = f"[{section}] " if section else ""
        formatted.append(f"- {prefix}{entry_lines[0]}")
        for extra in entry_lines[1:]:
            formatted.append(f"  {extra}" if extra else "")
    block = "\n".join(formatted)

    heading = f"## {today_text()}（已完成待办归档）"
    if heading in text:
        start = text.index(heading)
        next_h = text.find("\n## ", start + len(heading))
        if next_h == -1:
            return text.rstrip() + "\n" + block + "\n"
        return text[:next_h].rstrip() + "\n" + block + "\n" + text[next_h:]

    return text.rstrip() + f"\n\n{heading}\n\n{block}\n"


def archive_completed_todos(project_path: Path) -> ArchiveTodosReport:
    """Move checked (- [x]) items from TODO.md into CHANGELOG.md with version snapshots."""
    require_initialized_project(project_path)
    paths = context_file_paths(project_path)
    todo_path = paths["TODO.md"]
    changelog_path = paths["CHANGELOG.md"]

    todo_text = read_utf8(todo_path)
    lines_before = len(todo_text.splitlines())
    remaining, archived = _split_completed_todos(todo_text)
    if not archived:
        return ArchiveTodosReport(
            project_path=project_path,
            archived_count=0,
            archived_items=[],
            todo_lines_before=lines_before,
            todo_lines_after=lines_before,
        )

    changelog_text = read_utf8(changelog_path) if changelog_path.exists() else "# CHANGELOG\n"
    updated_changelog = _append_archived_todos_to_changelog(changelog_text, archived)

    # Snapshot before and after so the Changes page shows the exact lines archived.
    record_version(project_path, "TODO.md", source="archive-todo")
    record_version(project_path, "CHANGELOG.md", source="archive-todo")
    write_utf8(todo_path, remaining)
    write_utf8(changelog_path, updated_changelog)
    record_version(project_path, "TODO.md", source="archive-todo")
    record_version(project_path, "CHANGELOG.md", source="archive-todo")

    lines_after = len(remaining.splitlines())
    return ArchiveTodosReport(
        project_path=project_path,
        archived_count=len(archived),
        archived_items=[entry_lines[0] for _, entry_lines in archived],
        todo_lines_before=lines_before,
        todo_lines_after=lines_after,
    )
