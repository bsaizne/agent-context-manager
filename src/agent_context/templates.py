from __future__ import annotations

from pathlib import Path

from .utils import now_text

AGENT_DIR_NAME = ".agent"

CONTEXT_FILES = [
    "STATE.md",
    "TODO.md",
    "INDEX.md",
    "DECISIONS.md",
    "CHANGELOG.md",
]

# Handoff prompt template. {project} is replaced with the project folder name
# and {resume} with the full build_resume() output; resume.render_agent_prompt
# does the substitution. The stock default tells the new agent to stop and wait
# for instructions instead of starting work on its own. Users edit it in the
# GUI Settings page (or by hand in config.json).
DEFAULT_AGENT_PROMPT_TEMPLATE = """以下是「{project}」项目的交接上下文。

请先读 AGENTS.md，再看下面的项目状态。读完请停下来等我下达具体任务指令；在我明确给出指令之前，不要主动修改任何文件、不要开始任何任务。

{resume}
"""

# Every key here must be read by real code, otherwise `agent-context config`
# advertises settings that do nothing. archive_enabled drives checkpoint
# archiving, max_state_lines/max_todo_lines drive the doctor size warnings,
# default_editor is used by the GUI external-open action,
# version_history_limit caps how many change-history snapshots are kept, and
# agent_prompt_template is rendered by resume.build_agent_prompt.
DEFAULT_CONFIG = {
    "archive_enabled": True,
    "max_state_lines": 120,
    "max_todo_lines": 100,
    "default_editor": None,
    "version_history_limit": 30,
    "agent_prompt_template": DEFAULT_AGENT_PROMPT_TEMPLATE,
}


def agents_template() -> str:
    return """# Agent Project Instructions

## Context Management

Before starting work:

1. Read `.agent/STATE.md`.
2. Read `.agent/TODO.md`.
3. Read `.agent/INDEX.md` only when necessary.
4. Do not read `.agent/archive/` unless explicitly required.
5. Do not read the entire project automatically.

## Working Rules

- Treat source code as the source of truth.
- Do not copy large code blocks into context documents.
- Do not rewrite completed work without a reason.
- Respect existing architectural decisions.
- Check `.agent/DECISIONS.md` before reversing an important decision.
- Update project state after major milestones.

## Checkpoint

When the conversation becomes large or before switching to a new Agent conversation:

Run:

```bash
agent-context checkpoint
```

The checkpoint only writes inside `.agent/`. It:

- refreshes `.agent/STATE.md` (Last Updated, and repairs missing sections)
- restores a missing `# TODO` heading in `.agent/TODO.md`
- appends a note to `.agent/CHANGELOG.md`
- stores a snapshot under `.agent/archive/` (disable with `archive_enabled` in the user config)
- records a content snapshot of every context file under `.agent/versions/`, which is what the
  GUI change view diffs against (never hand-edit it; the tool prunes it automatically)

It does not rewrite your TODO items, `.agent/DECISIONS.md` or `.agent/INDEX.md`.
Update those yourself when the work changes; the tool cannot guess their content.

## Resume

When starting a new Agent conversation:

Run:

```bash
agent-context resume
```

Only load the minimum information required to continue the project.
"""


def state_template(project_path: Path) -> str:
    return f"""# PROJECT STATE

## Project

{project_path.name}

## Current Phase

Phase 1

## Current Task

No active task.

## Completed

- Nothing yet.

## Current Problem

No known problems.

## Current Implementation

No implementation details yet.

## Current Decision

No major decisions yet.

## Next Actions

1. Define the next task.

## Important Constraints

- None.

## Known Issues

- None.

## Last Updated

{now_text()}
"""


def todo_template() -> str:
    return """# TODO

## P0 — Current

- [ ] Define current task.

## P1 — Next

- [ ] None.

## P2 — Later

- [ ] None.

## Blocked

- None.
"""


def decisions_template() -> str:
    return """# DECISIONS

No major decisions yet.
"""


def changelog_template() -> str:
    return """# CHANGELOG

No changes recorded yet.
"""


def index_template(project_path: Path) -> str:
    return f"""# PROJECT INDEX

## Module

### Name

{project_path.name}

### Path

.

### Description

Project root. Update this index with module locations as the project evolves.

### Related Documentation

docs/

---

## Important Files

### File

AGENTS.md

### Purpose

Agent instructions for the project context protocol.
"""


def file_templates(project_path: Path) -> dict[str, str]:
    return {
        "STATE.md": state_template(project_path),
        "TODO.md": todo_template(),
        "INDEX.md": index_template(project_path),
        "DECISIONS.md": decisions_template(),
        "CHANGELOG.md": changelog_template(),
    }
