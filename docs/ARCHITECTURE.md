# Architecture

Agent Context Manager is a local-first Python CLI. It has no server, no database, no cloud sync, no MCP integration, and no AI API calls.

## Boundaries

The shared core owns:

- Project initialization
- Markdown file creation and validation
- Git metadata collection
- Lightweight checkpoint archiving
- Minimal resume output
- Local user config
- Health checks

The Windows PySide6 GUI and the CLI both call this shared core. The GUI does not maintain a second context format or duplicate project state.

Agents and users own:

- Understanding the project
- Editing the source code
- Summarizing current work into `STATE.md`
- Maintaining meaningful TODOs
- Recording important decisions

## Data Model

Each project has a local `.agent/` directory:

```text
.agent/
├── STATE.md
├── TODO.md
├── INDEX.md
├── DECISIONS.md
├── CHANGELOG.md
└── archive/
```

The project root also has `AGENTS.md`.

## Project Isolation

All commands resolve the project path from the current directory or an explicit path argument. Context reads and writes are scoped to:

```text
<project>/.agent/
```

No command scans sibling projects for context.

## Checkpoint Flow

`agent-context checkpoint`:

1. Validates the current project.
2. Checks `.agent/`.
3. Repairs the protocol files before reading them: `STATE.md` missing sections and a missing `# TODO` heading are fixed first, so a damaged file aborts nothing halfway.
4. Collects Git status and recent commits when Git exists.
5. Reads `STATE.md` and `TODO.md`.
6. Updates only the `Last Updated` section in `STATE.md`.
7. Writes a timestamped checkpoint under `.agent/archive/` - second-precision name, numeric suffix on collision, skipped entirely when `archive_enabled` is false.
8. Adds a short checkpoint note to `CHANGELOG.md`.
9. Prints a summary.

The checkpoint does not copy source files or full diffs. It never rewrites TODO items,
`DECISIONS.md` or `INDEX.md`; only a human or an agent can decide their content.

## Transfer Safety

`export_project` writes `.agent/**` plus `AGENTS.md` into one `.agentctx.json`.
`import_project` then:

- rejects absolute paths and any `..` segment (a crafted payload could otherwise write outside the target project)
- copies every file it is about to replace into `.agent/archive/import-backup-<stamp>/`
- keeps an existing hand-written `AGENTS.md` instead of overwriting it, matching `init`
- returns an `ImportReport` so callers can show created/overwritten/unchanged/kept counts

## Change History

Every context file keeps a lightweight history under `.agent/versions/`:

- `record_version()` stores the whole file (they are small) and skips identical content
- snapshots are taken on save, *before* an external change is reloaded, and before/after a checkpoint
- the index keeps the recording order, which is what the diff relies on (sorting by id made two same-second versions compare backwards)
- retention keeps the newest `version_history_limit` versions (default 30) plus the first version of every day
- `build_diff_view()` turns two versions into `+`/`-` lines; the GUI paints inserts green and deletes red, and editors tint lines that are new since the last snapshot
- `.agent/versions/` is excluded from `export_project`

## Token Accounting

`context_token_stats` counts only the files a fresh agent loads: the five `.agent`
Markdown files plus `AGENTS.md`. Archive and import-backup files are reported as separate
counters, because they grow without bound while `resume` never reads them.

## Resume Flow

`agent-context resume` reads only:

```text
.agent/STATE.md
.agent/TODO.md
```

It intentionally avoids `DECISIONS.md`, `CHANGELOG.md`, and `.agent/archive/` unless a user explicitly asks for those files through another command.

## Error Handling

Expected failures produce structured user-facing errors:

```text
Error:
Unable to read STATE.md.

Reason:
File encoding is invalid.

Suggestion:
Run:

agent-context doctor
```

Tracebacks are not part of normal CLI UX.
