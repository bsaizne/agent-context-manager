from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys
from typing import Callable

from . import __version__
from .archive import list_archives, read_archive
from .checkpoint import checkpoint_summary_lines, run_checkpoint
from .config import config_path, load_config
from .doctor import run_doctor
from .project import init_project, resolve_project_path
from .resume import build_agent_prompt, build_resume
from .state import repair_project
from .status import get_status
from .utils import ContextError

try:  # Optional at test time; installed package uses Typer.
    import typer
except ImportError:  # pragma: no cover - depends on environment
    typer = None

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover - depends on environment
    Console = None
    Table = None


def build_console():
    """Return a Rich console only when the terminal can render the status glyphs.

    On a Chinese Windows console (cp936/gbk) Rich's legacy Windows renderer raises
    UnicodeEncodeError on '✓' and the whole command dies with a traceback. Rich is
    a nicety, not a requirement, so fall back to the plain-text renderer instead.
    """
    if Console is None:
        return None
    try:
        (sys.stdout.encoding or "utf-8").encode("✓")
    except (UnicodeEncodeError, LookupError):
        return None
    return Console()


console = build_console()


def can_encode(text: str) -> bool:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def ok_marker() -> str:
    return "✓" if can_encode("✓") else "OK"


def fail_marker() -> str:
    return "✗" if can_encode("✗") else "X"


def echo(text: str = "") -> None:
    if console:
        console.print(text)
    else:
        encoding = sys.stdout.encoding or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding)
        print(safe)


def render_error(error: ContextError) -> None:
    echo("Error:")
    echo(error.message)
    if error.reason:
        echo("")
        echo("Reason:")
        echo(error.reason)
    if error.suggestion:
        echo("")
        echo("Suggestion:")
        echo(error.suggestion)


def handle(action: Callable[[], None]) -> None:
    try:
        action()
    except ContextError as exc:
        render_error(exc)
        raise SystemExit(exc.exit_code) from exc


def cmd_init(path: str | Path | None = None) -> None:
    result = init_project(path)
    echo(f"Initialized project: {result.project_path}")
    if result.created:
        echo("")
        echo("Created:")
        for item in result.created:
            echo(f"  {ok_marker()} {item}")
    skipped_agents = [item for item in result.skipped if item == "AGENTS.md already exists. Skipped."]
    if skipped_agents:
        echo("")
        echo("AGENTS.md already exists.")
        echo("Skipped.")


def cmd_status(path: str | Path | None = None) -> None:
    status = get_status(resolve_project_path(path))
    if console and Table:
        table = Table(title="Agent Context Status")
        table.add_column("Item")
        table.add_column("Value")
        table.add_row("Project", status.project_path.name)
        table.add_row("Current Phase", status.phase)
        table.add_row("Current Task", status.task)
        table.add_row("Git", f"{ok_marker()} Repository detected" if status.git_info.repository_detected else "Repository not detected")
        table.add_row("Modified Files", str(status.git_info.modified_file_count))
        table.add_row("Last Checkpoint", status.last_checkpoint or "None")
        table.add_row("TODO", f"P0: {status.p0_count} | P1: {status.p1_count} | P2: {status.p2_count}")
        console.print(table)
        echo("Context Files:")
        for name, exists in status.context_files.items():
            echo(f"{ok_marker() if exists else fail_marker()} {name}")
        return

    echo(f"Project:\n{status.project_path.name}\n")
    echo("Context Files:")
    for name, exists in status.context_files.items():
        echo(f"{ok_marker() if exists else fail_marker()} {name}")
    echo("")
    echo(f"Current Phase:\n{status.phase}\n")
    echo(f"Current Task:\n{status.task}\n")
    echo(f"Git:\n{ok_marker() + ' Repository detected' if status.git_info.repository_detected else 'Repository not detected'}\n")
    echo(f"Modified Files:\n{status.git_info.modified_file_count}\n")
    echo(f"Last Checkpoint:\n{status.last_checkpoint or 'None'}\n")
    echo(f"TODO:\nP0: {status.p0_count}\nP1: {status.p1_count}\nP2: {status.p2_count}")


def cmd_checkpoint(path: str | Path | None = None) -> None:
    summary = run_checkpoint(resolve_project_path(path))
    echo("Checkpoint complete.")
    for line in checkpoint_summary_lines(summary):
        echo(line)


def cmd_resume(path: str | Path | None = None, prompt: bool = False) -> None:
    project_path = resolve_project_path(path)
    echo(build_agent_prompt(project_path) if prompt else build_resume(project_path))


def cmd_doctor(path: str | Path | None = None) -> None:
    checks = run_doctor(resolve_project_path(path))
    failures = 0
    for check in checks:
        marker = ok_marker() if check.ok else fail_marker()
        severity = getattr(check, "severity", "error")
        suffix = ""
        if not check.ok:
            if severity == "warning":
                suffix = " (warning)"
            elif severity == "error":
                suffix = " (error)"
        echo(f"{marker} {check.name}{suffix}: {check.detail}")
        if not check.ok and check.suggestion:
            if getattr(check, "severity", "error") == "warning":
                echo(f"  Note: {check.suggestion}")
            else:
                failures += 1
                echo(f"  Suggestion: {check.suggestion}")
    if failures:
        raise SystemExit(1)


def cmd_archive(path: str | Path | None = None, show: str | None = None) -> None:
    project_path = resolve_project_path(path)
    if show:
        echo(read_archive(project_path, show))
        return
    items = list_archives(project_path)
    if not items:
        echo("No checkpoints found.")
        return
    for item in items:
        echo(f"{item.index}. {item.path.name}")


def cmd_repair(path: str | Path | None = None) -> None:
    report = repair_project(resolve_project_path(path))
    echo(f"Repair complete: {report.project_path}")
    echo("")
    if report.state_missing_required:
        echo("STATE.md was missing required sections (now added):")
        for name in report.state_missing_required:
            echo(f"  - {name}")
    if report.state_missing_optional:
        echo("STATE.md was missing optional sections (now added):")
        for name in report.state_missing_optional:
            echo(f"  - {name}")
    if report.state_duplicate_sections:
        echo("STATE.md had duplicated sections (merged, no content lost):")
        for name in report.state_duplicate_sections:
            echo(f"  - {name}")
    if report.todo_duplicate_sections:
        echo("TODO.md had duplicated sections (merged, no content lost):")
        for name in report.todo_duplicate_sections:
            echo(f"  - {name}")
    if report.todo_heading_added:
        echo("TODO.md was missing its top-level '# TODO' heading (added).")
    if report.state_changed:
        echo("STATE.md rewritten into the protocol section order.")
    elif not report.todo_heading_added:
        echo("Nothing to repair; both files already match the protocol.")


def cmd_version() -> None:
    echo(f"agent-context {__version__}")


def cmd_config() -> None:
    config = load_config(create=True)
    echo(f"Config file: {config_path()}")
    echo(json.dumps(config, ensure_ascii=False, indent=2))


def build_typer_app():
    app = typer.Typer(help="Local Agent context handoff manager.")

    @app.command("init")
    def init_command(path: Path | None = typer.Argument(None, help="Project directory.")):
        handle(lambda: cmd_init(path))

    @app.command("status")
    def status_command(path: Path | None = typer.Argument(None, help="Project directory.")):
        handle(lambda: cmd_status(path))

    @app.command("checkpoint")
    def checkpoint_command(path: Path | None = typer.Argument(None, help="Project directory.")):
        handle(lambda: cmd_checkpoint(path))

    @app.command("resume")
    def resume_command(
        path: Path | None = typer.Argument(None, help="Project directory."),
        prompt: bool = typer.Option(False, "--prompt", help="Wrap resume in the minimal agent prompt."),
    ):
        handle(lambda: cmd_resume(path, prompt=prompt))

    @app.command("doctor")
    def doctor_command(path: Path | None = typer.Argument(None, help="Project directory.")):
        handle(lambda: cmd_doctor(path))

    @app.command("archive")
    def archive_command(
        path: Path | None = typer.Argument(None, help="Project directory."),
        show: str | None = typer.Option(None, "--show", help="Show a checkpoint by index or file name."),
    ):
        handle(lambda: cmd_archive(path, show=show))

    @app.command("repair")
    def repair_command(path: Path | None = typer.Argument(None, help="Project directory.")):
        handle(lambda: cmd_repair(path))

    @app.command("config")
    def config_command():
        handle(cmd_config)

    @app.command("version")
    def version_command():
        handle(cmd_version)

    return app


def argparse_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="agent-context", description="Local Agent context handoff manager.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ["init", "status", "checkpoint", "resume", "doctor", "archive", "repair"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("path", nargs="?")
        if command == "resume":
            sub.add_argument("--prompt", action="store_true")
        if command == "archive":
            sub.add_argument("--show")
    subparsers.add_parser("config")
    subparsers.add_parser("version")

    args = parser.parse_args(argv)
    handle(lambda: dispatch_argparse(args))


def dispatch_argparse(args: argparse.Namespace) -> None:
    if args.command == "init":
        cmd_init(args.path)
    elif args.command == "status":
        cmd_status(args.path)
    elif args.command == "checkpoint":
        cmd_checkpoint(args.path)
    elif args.command == "resume":
        cmd_resume(args.path, prompt=args.prompt)
    elif args.command == "doctor":
        cmd_doctor(args.path)
    elif args.command == "archive":
        cmd_archive(args.path, show=args.show)
    elif args.command == "repair":
        cmd_repair(args.path)
    elif args.command == "config":
        cmd_config()
    elif args.command == "version":
        cmd_version()
    else:  # pragma: no cover
        raise ContextError("Unknown command.", args.command, "Run:\n\nagent-context --help")


def main(argv: list[str] | None = None) -> None:
    if typer is not None and argv is None:
        app = build_typer_app()
        app()
        return
    argparse_main(sys.argv[1:] if argv is None else argv)
