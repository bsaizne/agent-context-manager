from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from .config import load_config
from .git import git_available, is_git_repository
from .project import agent_dir, context_file_paths
from .state import OPTIONAL_STATE_SECTIONS, REQUIRED_STATE_SECTIONS, _has_section
from .templates import CONTEXT_FILES
from .utils import check_utf8


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str
    suggestion: str | None = None
    severity: str = "error"  # "error" or "warning"


def run_doctor(project_path: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    checks.append(
        DoctorCheck(
            "Python version",
            sys.version_info >= (3, 11),
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "Install Python 3.11 or newer.",
        )
    )
    checks.append(
        DoctorCheck(
            "Project directory",
            project_path.exists() and project_path.is_dir(),
            str(project_path),
            "Run from a project directory or pass a path.",
        )
    )

    directory = agent_dir(project_path)
    checks.append(
        DoctorCheck(
            ".agent directory",
            directory.exists() and directory.is_dir(),
            str(directory),
            "Run: agent-context init",
        )
    )

    paths = context_file_paths(project_path)
    for name in CONTEXT_FILES:
        path = paths[name]
        checks.append(
            DoctorCheck(
                name,
                path.exists() and path.is_file(),
                str(path),
                "Run: agent-context init",
            )
        )

    agents_path = project_path / "AGENTS.md"
    checks.append(
        DoctorCheck(
            "AGENTS.md",
            agents_path.exists() and agents_path.is_file(),
            str(agents_path),
            "Run: agent-context init",
        )
    )

    checks.append(
        DoctorCheck(
            "Git availability",
            git_available(),
            "git on PATH" if git_available() else "git unavailable",
            "Install Git or continue without Git integration.",
        )
    )

    checks.append(
        DoctorCheck(
            "Git repository",
            True,
            "repository detected" if is_git_repository(project_path) else "not a Git repository (allowed)",
            "This is allowed; checkpoint will continue without Git info.",
        )
    )

    encoding_ok = True
    encoding_detail: list[str] = []
    for path in [*paths.values(), agents_path]:
        status = check_utf8(path)
        if status.exists and not status.readable_utf8:
            encoding_ok = False
            encoding_detail.append(f"{path.name}: {status.error}")
    checks.append(
        DoctorCheck(
            "File encoding",
            encoding_ok,
            "; ".join(encoding_detail) if encoding_detail else "UTF-8 readable",
            "Save Markdown files as UTF-8.",
        )
    )

    isolation_ok = directory.resolve().parent == project_path.resolve() if directory.exists() else False
    checks.append(
        DoctorCheck(
            "Project isolation",
            isolation_ok,
            str(directory),
            "Context files must live directly under this project's .agent directory.",
        )
    )

    state_path = paths["STATE.md"]
    if state_path.exists() and state_path.is_file():
        try:
            state_text = state_path.read_text(encoding="utf-8")
            missing_required = [name for name in REQUIRED_STATE_SECTIONS if not _has_section(state_text, name)]
            missing_optional = [name for name in OPTIONAL_STATE_SECTIONS if not _has_section(state_text, name)]
            if missing_required:
                checks.append(
                    DoctorCheck(
                        "STATE.md sections",
                        False,
                        f"missing required: {', '.join(missing_required)}",
                        "Add the required headings, or restore them from an archive.",
                        "error",
                    )
                )
            elif missing_optional:
                checks.append(
                    DoctorCheck(
                        "STATE.md sections",
                        False,
                        f"missing optional: {', '.join(missing_optional)}",
                        "Optional sections are repaired automatically on the next checkpoint.",
                        "warning",
                    )
                )
            else:
                checks.append(DoctorCheck("STATE.md sections", True, "all required and optional sections present", None, "none"))
        except UnicodeDecodeError:
            pass  # Encoding is reported separately by File encoding.

    # max_state_lines / max_todo_lines used to be dead config: defined, printed
    # by `agent-context config`, and read by nothing. They now drive a real
    # warning instead of silently doing nothing.
    limits = (("STATE.md", "max_state_lines"), ("TODO.md", "max_todo_lines"))
    config = load_config()
    for name, limit_key in limits:
        path = paths[name]
        limit = config.get(limit_key)
        if not isinstance(limit, int) or limit <= 0 or not path.exists() or not path.is_file():
            continue
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            continue
        checks.append(
            DoctorCheck(
                f"{name} size",
                line_count <= limit,
                f"{line_count} lines (limit {limit})",
                f"Trim {name} or raise {limit_key} with: agent-context config",
                "warning",
            )
        )
    return checks
