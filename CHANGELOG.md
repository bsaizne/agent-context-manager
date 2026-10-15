# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-10-14

### Added

- **Change history (L1).** Every context file keeps a content snapshot under
  `.agent/versions/` whenever it changes. The GUI gains a `Changes` page that diffs any
  two recorded versions: added lines are painted green, removed lines red, and each side
  carries its own timestamp.
- The editor tints lines that are new since the last snapshot, and the Overview page
  shows a "recent changes" card with the `+N / -N` counts per file.
- `version_history_limit` (default 30) controls retention; the first version of every day
  is always kept so a months-old state stays inspectable.
- The history is excluded from `export_project`, so transfer files stay small.

### Fixed

- `icons.py`: an unknown icon name called the non-existent `QPainter.drawCircle()`, and
  the `warning` icon passed coordinate tuples to `drawPolygon()`. Both left the painter
  open and aborted the process with
  `QPaintDevice: Cannot destroy paint device that is being painted`; the Doctor page hit
  the second one as soon as any check warned. `icon()` now closes the painter in a
  `finally` block and both call sites are correct.
- Version history: two snapshots recorded in the same second were sorted by digest, which
  could make the diff run backwards.

### Changed

- Windows packaging switched from **onefile to onedir**. A onefile build unpacks itself
  into `%TEMP%` on every launch; on a machine whose `%TEMP%` is damaged the bootloader
  aborted with `Could not create temporary directory!` before any application code ran.
  The onedir build loads its DLLs from its own folder and never needs a writable `%TEMP%`.
- `scripts/build-windows.ps1` accepts both `dist\<name>\<name>.exe` (onedir) and
  `dist\<name>.exe` (onefile) when verifying the output.
- Version bumped to 0.8.0 in `pyproject.toml`, `agent_context.__version__` and both
  PyInstaller specs, which may no longer drift apart unnoticed.

## [0.5.0] - 2026-10-11

### Added

- `agent-context version`.
- `repair` merges duplicated `##` sections in `TODO.md` and reports them. Priority sections
  are matched by prefix, so a second `## P0` block no longer disappears from `status` and
  `resume`.
- `checkpoint` restores a missing `# TODO` heading instead of aborting *after* `STATE.md`
  had already been rewritten.
- Import safety: `import_project` rejects absolute paths and `..` segments, backs up every
  file it replaces under `.agent/archive/import-backup-<stamp>/`, keeps an existing
  hand-written `AGENTS.md`, and returns an `ImportReport`.
- `doctor` warns when `STATE.md` / `TODO.md` exceed `max_state_lines` / `max_todo_lines`;
  `archive_enabled` really controls archiving; `default_editor` is wired to the GUI action
  that opens a file externally.

### Fixed

- Checkpoint archives collided when two ran inside the same minute (now second precision
  plus a numeric suffix).
- Token accounting counted `.agent/archive/` as resume context; archives are reported
  separately now.
- GUI: a programmatic navigation left the sidebar highlight on the previous entry, and the
  base stylesheet font size used `px`, which made Qt print `QFont::setPointSize: Point
  size <= 0` at every launch.

## [0.1.0] - 2026-08-23

### Added

- Initial CLI (`init`, `status`, `checkpoint`, `resume`, `doctor`, `archive`, `repair`,
  `config`) with the `.agent/` Markdown protocol and the `AGENTS.md` bootstrap.
- PySide6 desktop GUI sharing the same core.
- The unittest suite and the local user config at `~/.agent-context/config.json`.

[0.8.0]: https://github.com/bsaizne/agent-context-manager/releases/tag/v0.8.0
[0.5.0]: https://github.com/bsaizne/agent-context-manager/releases/tag/v0.5.0
[0.1.0]: https://github.com/bsaizne/agent-context-manager/releases/tag/v0.1.0
