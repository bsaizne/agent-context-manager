# Agent Context Manager

[简体中文](README.md) | **English**

[![tests](https://github.com/bsaizne/agent-context-manager/actions/workflows/tests.yml/badge.svg)](https://github.com/bsaizne/agent-context-manager/actions/workflows/tests.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)

A local, file-based way to hand a project from one AI coding agent conversation to the
next - without keeping a transcript.

## What is Agent Context Manager?

Agent Context Manager is a local CLI for handing off project state between AI coding agent conversations. It stores the minimum useful project memory in Markdown files under each project's `.agent/` directory.

It does not save full chat logs. It preserves current state, tasks, decisions, changes, and navigation hints so a new agent can continue without reconstructing the whole conversation.

## Why?

Long agent conversations eventually hit context limits. The useful handoff is rarely the full transcript; it is the current task, what is already done, what is blocked, where the relevant files live, and what constraints must be respected.

Agent Context Manager keeps that information short, local, and project-scoped.

## Requirements

- Python 3.11 or newer. The CLI needs only the standard library plus Typer and Rich.
- Git is optional; when present, checkpoints record `git status` and recent commits.
- The Windows GUI needs PySide6 6.7+ and Windows 10 1903 or newer (Qt links against the
  OS-provided ICU, so the ICU runtime is never bundled).
- macOS and Linux are supported for the CLI; the GUI is Windows-only today.

## Installation

Development install:

```bash
pip install -e .
```

Optional development tools:

```bash
pip install -e ".[test,package]"
```

After installation:

```bash
agent-context --help
```

## Quick Start

```bash
cd my-project
agent-context init
agent-context status
agent-context resume
```

When context is getting large:

```bash
agent-context checkpoint
```

In a fresh agent conversation:

```bash
agent-context resume
```

## Commands

### init

Creates `.agent/` and the initial Markdown protocol files:

```bash
agent-context init
agent-context init /path/to/project
```

If `AGENTS.md` already exists, it is not overwritten.

### status

Shows context file presence, current phase, current task, Git detection, modified file count, last checkpoint, and TODO counts:

```bash
agent-context status
```

### checkpoint

Refreshes `.agent/STATE.md` last-updated timestamp, records a lightweight archive checkpoint, updates `.agent/CHANGELOG.md`, and summarizes Git status when available:

```bash
agent-context checkpoint
```

It only writes inside `.agent/`.

### resume

Prints the minimal resume context. By default it reads only `.agent/STATE.md` and `.agent/TODO.md`:

```bash
agent-context resume
agent-context resume --prompt
```

### doctor

Checks Python version, project setup, context files, `AGENTS.md`, Git availability, UTF-8 encoding, and project isolation:

```bash
agent-context doctor
```

### repair

Rewrites `STATE.md` and `TODO.md` into the protocol structure **without losing content**. It
adds missing required and optional sections, merges duplicated sections (both blocks are
kept and marked), and restores a missing top-level `# TODO` heading:

```bash
agent-context repair
```

Run it when a context file has been rewritten by hand or by an agent and `status` /
`resume` / `checkpoint` start failing with `STATE.md needs attention`. It also restores a
missing top-level `# TODO` heading and merges duplicated `##` sections in `TODO.md`
(no content is lost). The same action is available in the GUI from the Doctor page and
from the "STATE.md needs repair" card on Overview.

### archive

Lists archived checkpoints without restoring or overwriting current state:

```bash
agent-context archive
agent-context archive --show 1
```

### config

Shows and creates local user-level config at `~/.agent-context/config.json`:

```bash
agent-context config
```

For tests or sandboxed runs, set `AGENT_CONTEXT_CONFIG_DIR` to write `config.json` somewhere else.

### version

Prints the installed version:

```bash
agent-context version
```

## Windows GUI

The Windows desktop version uses PySide6 and shares the same `.agent/` files with the CLI.

Install the GUI dependency:

```powershell
pip install -e ".[gui]"
```

Launch it from a project directory:

```powershell
agent-context-gui
```

Or pass a project path directly:

```powershell
agent-context-gui "D:\Projects\MyProject"
```

The GUI provides project selection, initialization, context Markdown editing, checkpoint creation, resume text copying, archive preview, and health checks. It also adds:

- **复制填充提示词** - copies a Chinese bootstrap prompt that tells a fresh agent which files to read and which files it may write.
- **导出项目 / 导入项目** - `.agentctx.json` transfer files. Import backs up every file it replaces under `.agent/archive/import-backup-<stamp>/`, keeps an existing hand-written `AGENTS.md`, and refuses paths that try to escape the target directory.
- **上下文档案 tokens** - the context a fresh agent actually loads. `.agent/archive/` is reported separately because `resume` never reads it.
- **外部打开** - opens the current context file with `default_editor` or the OS default program.
- **Changes / 变更** - diffs any two recorded versions of a file: added lines on green, removed lines on red, each side stamped with its time. While you type, the editor also tints the lines you have added but not saved yet.

## Project Structure

An initialized project contains:

```text
.agent/
├── STATE.md
├── TODO.md
├── INDEX.md
├── DECISIONS.md
├── CHANGELOG.md
├── archive/
└── versions/        # change history snapshots (managed automatically)
AGENTS.md
```

Source layout:

```text
src/agent_context/
├── cli.py
├── config.py
├── project.py
├── state.py
├── checkpoint.py
├── resume.py
├── git.py
├── archive.py
├── doctor.py
├── templates.py
└── utils.py
```

## Context Protocol

`STATE.md` is the current project state, not a historical log. Each checkpoint keeps it current rather than appending old summaries.

`TODO.md` stores short P0/P1/P2/Blocked task lists. It should not duplicate long descriptions already present in `STATE.md`.

`DECISIONS.md` stores important technical decisions only.

`CHANGELOG.md` stores actual changes over time.

`INDEX.md` points agents to relevant files. It should not copy source code.

`.agent/archive/` stores historical checkpoint snapshots. `resume` does not read archives by default.

`.agent/versions/` stores one content snapshot per change of every context file, including
changes an agent made while the app was open. It is what the GUI `Changes` page diffs
against, it is pruned automatically (see `version_history_limit` in `agent-context config`),
and it must never be hand-edited. `export` leaves it out so transfer files stay small.

## Claude Usage

### New Project

```bash
cd my-project
agent-context init
```

Tell Claude:

```text
Read AGENTS.md and follow the project context protocol.
```

### Working

Work normally. When the conversation becomes large:

```bash
agent-context checkpoint
```

### New Conversation

```bash
agent-context resume
```

Paste the output into Claude.

## Codex Usage

Initialize once:

```bash
agent-context init
```

At the start of a new Codex task, run:

```bash
agent-context resume
```

Ask Codex to read `AGENTS.md`, then inspect only files relevant to the current task.

## Cursor Usage

Initialize the project:

```bash
agent-context init
```

When switching Cursor chats:

```bash
agent-context resume
```

Paste the resume output and tell Cursor not to scan the full project unless needed.

## Windows

Use PowerShell or Command Prompt:

```powershell
pip install -e .
agent-context init
agent-context status
```

Paths with Chinese, spaces, and Unicode characters are supported through `pathlib` and UTF-8 Markdown reads/writes.

## Troubleshooting

Run:

```bash
agent-context doctor
```

Common fixes:

- Missing `.agent/`: run `agent-context init`.
- Invalid Markdown encoding: save files as UTF-8.
- Git not detected: install Git, or continue without Git integration.
- Existing `AGENTS.md`: the tool skips it by design and will not overwrite your project instructions.
- `STATE.md needs attention` / `missing required sections`: the file was rewritten without the protocol headings. Run `agent-context repair` to re-add them (content is preserved).
- Pending-task counts show `P0: 0`: `TODO.md` needs `## P0` / `## P1` / `## P2` / `## Blocked` headings. `repair` restores the `# TODO` heading but will not invent priorities.
- Never rewrite `.agent/STATE.md` wholesale, and never delete or rename its `##` sections. Update sections in place; a full rewrite is what breaks `status` / `resume` / `checkpoint`.
- Duplicated `## P0` / `## P1` blocks in `TODO.md`: only the first block is read, so the rest used to disappear silently from `status` and `resume`. `repair` now merges duplicates and keeps every line.
- `checkpoint` with a `TODO.md` that lost its heading: the heading is restored automatically. Before 0.5 the run aborted *after* `STATE.md` had already been rewritten, leaving no archive behind.
- Importing a transfer file: replaced files are backed up under `.agent/archive/import-backup-<stamp>/` and an existing hand-written `AGENTS.md` is kept rather than overwritten.
- `.agent/versions/` growing: it keeps the newest 30 versions per file plus the first version of every day. Lower `version_history_limit` with `agent-context config` if that is too much history.

## Development

Run the standard library tests without external test dependencies:

```bash
python -m unittest discover -s tests
```

Run with pytest when installed:

```bash
pip install -e ".[test,gui]"
pytest
```

The GUI tests import PySide6. When the `gui` extra is missing they skip
themselves; installing only `[test]` used to abort pytest collection entirely.

The CLI implementation uses Typer and Rich when installed. A small argparse/plain-text fallback exists so core logic can still be exercised in minimal local Python environments.

## Testing

The test suite covers:

- Initialization and `AGENTS.md` preservation
- UTF-8 state parsing
- Checkpoint archive creation
- Minimal resume output
- Project isolation between separate `.agent/` directories
- Git detection and `git status --short`

## Packaging

Install PyInstaller:

```bash
pip install -e ".[gui,package]"
```

Windows PowerShell:

```powershell
.\scripts\build-windows.ps1
```

If Windows blocks local scripts (`... cannot be loaded because running scripts is
disabled on this system`), run the same script through a bypass policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Output:

```text
dist\agent-context\agent-context.exe                            (CLI)
dist\Agent Context Manager v0.8\Agent Context Manager v0.8.exe  (Windows GUI)
```

The Windows builds are **onedir**, not onefile: everything the app needs lives next
to the executable, so the whole folder has to be shipped. This is deliberate. A
onefile build unpacks itself into `%TEMP%` on every start, and on a machine whose
`%TEMP%` is damaged (for example leftover `_MEI` folders that cannot even be opened)
the bootloader fails with `Could not create temporary directory!` before any of the
application code runs. The onedir build loads its DLLs from its own folder and never
needs a writable `%TEMP%`.

The Windows build is local and does not require Node.js, a database, or a server.

## Updating

Pull or copy the updated source, then reinstall:

```bash
pip install -e .
```

For the packaged Windows executable, rebuild with `scripts\build-windows.ps1`.

## Changelog and contributing

What changed between releases is in [CHANGELOG.md](CHANGELOG.md). If you want to send a
patch, [CONTRIBUTING.md](CONTRIBUTING.md) describes the setup and the two rules that
matter most: keep the `.agent/` boundary, and add a regression test for every fix.

## Author

Created and maintained by **bsaizne**.

## License

MIT - see [LICENSE](LICENSE).
