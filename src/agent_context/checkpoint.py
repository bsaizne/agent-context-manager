from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import load_config
from .git import GitInfo, collect_git_info
from .project import context_file_paths, require_initialized_project
from .state import ensure_todo_heading_file, find_duplicate_todo_sections, load_snapshot, touch_state_last_updated
from .templates import CONTEXT_FILES
from .utils import compact_lines, now_stamp, now_text, read_utf8, today_text, unique_path, write_utf8
from .versions import record_version


@dataclass(frozen=True)
class CheckpointSummary:
    project_path: Path
    archive_path: Path | None
    git_info: GitInfo
    state_updated: bool
    changelog_updated: bool
    todo_repaired: bool = False
    archive_written: bool = True
    todo_duplicate_sections: list[str] = field(default_factory=list)


def run_checkpoint(project_path: Path) -> CheckpointSummary:
    directory = require_initialized_project(project_path)
    # Snapshot the current content before checkpoint touches anything: together with
    # the post-write snapshot below this is what makes "what did the checkpoint
    # change" visible in the change history.
    for filename in CONTEXT_FILES:
        record_version(project_path, filename, source="checkpoint")
    # Repair both protocol files before reading the snapshot. Repairing first and
    # validating afterwards is what lets checkpoint recover a damaged file; a
    # missing TODO heading used to abort the run *after* STATE.md had already been
    # rewritten, leaving no archive and no changelog entry behind.
    updated_state = touch_state_last_updated(project_path)
    todo_repaired = ensure_todo_heading_file(project_path)
    snapshot = load_snapshot(project_path)
    # Detect, do not silently rewrite: merging duplicate priority blocks changes a
    # file the user owns, so checkpoint reports it and points at `repair`.
    todo_duplicates = find_duplicate_todo_sections(snapshot.todo_text)
    git_info = collect_git_info(project_path)

    config = load_config()
    archive_enabled = bool(config.get("archive_enabled", True))

    archive_path: Path | None = None
    if archive_enabled:
        archive_path = unique_path(directory / "archive" / f"checkpoint-{now_stamp()}.md")
        archive_text = build_archive_checkpoint(
            project_path=project_path,
            state_text=updated_state,
            todo_text=snapshot.todo_text,
            git_info=git_info,
        )
        write_utf8(archive_path, archive_text)

    changelog_path = context_file_paths(project_path)["CHANGELOG.md"]
    changelog_text = read_utf8(changelog_path)
    updated_changelog = add_changelog_checkpoint_note(
        changelog_text,
        archive_name=archive_path.name if archive_path else "",
        modified_count=git_info.modified_file_count,
        archive_enabled=archive_enabled,
    )
    write_utf8(changelog_path, updated_changelog)

    # Post-write snapshots: the diff between the two states is exactly what the
    # checkpoint itself changed (Last Updated plus the changelog note).
    record_version(project_path, "STATE.md", source="checkpoint")
    record_version(project_path, "CHANGELOG.md", source="checkpoint")

    return CheckpointSummary(
        project_path=project_path,
        archive_path=archive_path,
        git_info=git_info,
        state_updated=True,
        changelog_updated=True,
        todo_repaired=todo_repaired,
        archive_written=archive_enabled,
        todo_duplicate_sections=todo_duplicates,
    )


def build_archive_checkpoint(
    project_path: Path,
    state_text: str,
    todo_text: str,
    git_info: GitInfo,
) -> str:
    status_block = "\n".join(git_info.status_lines) if git_info.status_lines else "No modified files detected."
    commits_block = "\n".join(git_info.recent_commits) if git_info.recent_commits else "No recent commits available."
    git_message = git_info.message or "Git information collected."
    fence = chr(96) * 3

    return f"""# Checkpoint

## Project

{project_path.name}

## Created

{now_text()}

## Git

Repository detected: {git_info.repository_detected}

{git_message}

### Modified Files

{fence}text
{status_block}
{fence}

### Recent Commits

{fence}text
{commits_block}
{fence}

## State Snapshot

{state_text.strip()}

## TODO Snapshot

{todo_text.strip()}
"""


def add_changelog_checkpoint_note(
    text: str,
    archive_name: str,
    modified_count: int,
    archive_enabled: bool = True,
) -> str:
    date = today_text()
    tick = chr(96)
    if archive_enabled:
        note = f"- Created {tick}{archive_name}{tick} checkpoint ({modified_count} modified/untracked file(s))."
    else:
        note = (
            "- Checkpoint written without an archive snapshot "
            f"({modified_count} modified/untracked file(s)); archive_enabled is false in the user config."
        )

    if "No changes recorded yet." in text:
        text = text.replace("No changes recorded yet.", "").rstrip()

    date_heading = f"## {date}"
    if date_heading not in text:
        entry = f"""{date_heading}

### Added

- None.

### Modified

- Updated {tick}.agent/STATE.md{tick} last-updated timestamp.

### Fixed

- None.

### Removed

- None.

### Notes

{note}
"""
        return text.rstrip() + "\n\n" + entry

    if note in text:
        return text

    marker = "### Notes"
    date_start = text.index(date_heading)
    next_date = text.find("\n## ", date_start + len(date_heading))
    section = text[date_start:] if next_date == -1 else text[date_start:next_date]
    if marker in section:
        insert_at = text.index(marker, date_start) + len(marker)
        return text[:insert_at] + f"\n\n{note}" + text[insert_at:]
    return text.rstrip() + f"\n\n### Notes\n\n{note}\n"


def checkpoint_summary_lines(summary: CheckpointSummary) -> list[str]:
    lines = [f"Project: {summary.project_path.name}"]
    if summary.archive_path is not None:
        lines.append(f"Archive: {summary.archive_path.name}")
    else:
        lines.append("Archive: disabled (archive_enabled = false in the user config)")
    lines.append(f"Modified files: {summary.git_info.modified_file_count}")
    if summary.todo_repaired:
        lines.append("TODO.md: restored the missing '# TODO' heading")
    if summary.todo_duplicate_sections:
        duplicated = ", ".join(summary.todo_duplicate_sections)
        lines.append(f"TODO.md: duplicated priority sections ({duplicated}); run: agent-context repair")
    if summary.git_info.message:
        lines.extend(compact_lines(summary.git_info.message, limit=2))
    return lines
