from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class GitInfo:
    git_available: bool
    repository_detected: bool
    status_lines: list[str]
    recent_commits: list[str]
    message: str | None = None

    @property
    def modified_file_count(self) -> int:
        return len(self.status_lines)


def git_available() -> bool:
    return shutil.which("git") is not None


def subprocess_window_options() -> dict[str, int]:
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def run_git(project_path: Path, args: list[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            **subprocess_window_options(),
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def is_git_repository(project_path: Path) -> bool:
    if not git_available():
        return False
    code, stdout, _ = run_git(project_path, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and stdout.strip().lower() == "true"


def collect_git_info(project_path: Path) -> GitInfo:
    if not git_available():
        return GitInfo(
            git_available=False,
            repository_detected=False,
            status_lines=[],
            recent_commits=[],
            message="Git is not installed or not available on PATH.",
        )

    if not is_git_repository(project_path):
        return GitInfo(
            git_available=True,
            repository_detected=False,
            status_lines=[],
            recent_commits=[],
            message="Git repository not detected. Checkpoint will continue without Git information.",
        )

    status_code, status_stdout, status_stderr = run_git(project_path, ["status", "--short"])
    log_code, log_stdout, _ = run_git(project_path, ["log", "-5", "--oneline"])

    status_lines = status_stdout.splitlines() if status_code == 0 and status_stdout else []
    recent_commits = log_stdout.splitlines() if log_code == 0 and log_stdout else []
    message = status_stderr if status_code != 0 else None

    return GitInfo(
        git_available=True,
        repository_detected=True,
        status_lines=status_lines,
        recent_commits=recent_commits,
        message=message,
    )
