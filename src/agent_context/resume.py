from __future__ import annotations

from pathlib import Path

from .state import load_snapshot
from .utils import compact_lines, first_nonempty_line


def build_resume(project_path: Path) -> str:
    snapshot = load_snapshot(project_path)

    project = first_nonempty_line(snapshot.section("Project"), project_path.name)
    phase = first_nonempty_line(snapshot.section("Current Phase"), "Unknown")
    task = first_nonempty_line(snapshot.section("Current Task"), "No active task.")
    problem = first_nonempty_line(snapshot.section("Current Problem"), "No known problems.")

    completed = compact_lines(snapshot.section("Completed"), limit=5)
    next_actions = compact_lines(snapshot.section("Next Actions"), limit=5)
    constraints = compact_lines(snapshot.section("Important Constraints"), limit=5)

    p0 = compact_lines(snapshot.todo_section("P0"), limit=5)

    lines: list[str] = [
        "AGENT CONTEXT RESUME",
        "",
        "Project:",
        project,
        "",
        "Phase:",
        phase,
        "",
        "Current Task:",
        task,
        "",
        "Completed:",
        *completed,
        "",
        "Current Problem:",
        problem,
        "",
        "Next:",
    ]

    lines.extend(next_actions or p0 or ["- No next actions recorded."])
    lines.extend(
        [
            "",
            "Important Constraints:",
            *(constraints or ["- None."]),
            "",
            "Instructions:",
            "Read AGENTS.md first.",
            "Read only relevant project files.",
            "Do not scan the entire project.",
            "Do not reconstruct the entire conversation.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_agent_prompt(project_path: Path) -> str:
    return f"""Continue this project.

Read AGENTS.md first.

Then use the following project state:

{build_resume(project_path).strip()}

Do not reconstruct the entire conversation.
Do not scan the entire project.
Only inspect files relevant to the current task.
"""
