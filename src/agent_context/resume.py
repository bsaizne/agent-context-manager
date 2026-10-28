from __future__ import annotations

from pathlib import Path

from .config import load_config
from .state import load_snapshot
from .templates import DEFAULT_AGENT_PROMPT_TEMPLATE
from .utils import ContextError, compact_lines, first_nonempty_line


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


def render_agent_prompt(project_path: Path, template: str | None = None) -> str:
    """Render the handoff prompt from the user-editable template.

    {project} becomes the project folder name and {resume} the full resume
    text. A template without {resume} would send the agent a handoff with no
    project context at all, so the resume text is appended and the missing
    placeholder is flagged. Substitution deliberately falls back to plain
    str.replace when str.format trips over stray braces — users legitimately
    put JSON snippets and shell examples in their prompts.
    """
    if template is None:
        try:
            template = load_config().get("agent_prompt_template")
        except ContextError:
            template = None
        if not template:
            template = DEFAULT_AGENT_PROMPT_TEMPLATE
    resume_text = build_resume(project_path).strip()
    try:
        rendered = template.format(project=project_path.name, resume=resume_text).strip()
    except (KeyError, IndexError, ValueError):
        rendered = template.replace("{resume}", resume_text).replace("{project}", project_path.name).strip()
    if "{resume}" not in template:
        rendered += (
            "\n\n---\n\n"
            + resume_text
            + "\n\n（提示：模板里没有 {resume} 占位符，交接上下文已自动附加在末尾。）"
        )
    return rendered + "\n"


def build_agent_prompt(project_path: Path) -> str:
    """Handoff prompt = user template from config, rendered with the resume."""
    return render_agent_prompt(project_path)
