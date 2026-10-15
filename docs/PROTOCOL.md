# Context Protocol

The protocol is designed to preserve only the information a future agent needs to continue work.

## Core Rule

Do not save everything. Save the current state needed for continuation.

## STATE.md

`STATE.md` is not a log. It represents the current state of the project.

Required sections:

- Project
- Current Phase
- Current Task
- Completed
- Current Problem
- Current Implementation
- Current Decision
- Next Actions
- Important Constraints
- Known Issues
- Last Updated

Update sections in place. Do not append old state below new state.

## TODO.md

Use priorities:

- P0: current must-do work
- P1: next work
- P2: later work
- Blocked: externally blocked work

Keep items short. Do not repeat long descriptions from `STATE.md`.

A `## P0` / `## P1` / `## P2` heading must appear at most once. `status` and `resume`
read only the first matching block, so a duplicate block was silently ignored; `repair`
merges duplicates into the first block and keeps every line.

## DECISIONS.md

Record only important technical decisions:

- Decision
- Reason
- Alternatives
- Rejected

Do not record chat summaries.

## CHANGELOG.md

Record actual project changes over time. This file is historical.

`CHANGELOG.md` may mention that a checkpoint was created, but it should not duplicate the whole current state.

## INDEX.md

Use `INDEX.md` as a project map:

- Module names
- Paths
- Short descriptions
- Related documentation
- Important files

Do not copy source code into the index.

## archive/

Archives are historical checkpoint snapshots. They are for explicit lookup, not default resume.

## versions/

`agent-context` writes a content snapshot of every context file here whenever one changes
(save, external agent edit, checkpoint, or a manual `record_version` call). The GUI `Changes`
page diffs these snapshots and marks added lines green and removed lines red. The directory is
machine-managed: never edit it by hand and never rely on its layout.

## Minimal Resume

Default resume order:

```text
STATE
TODO
current task
INDEX only if navigation is needed
relevant files only
```

Never default to:

```text
STATE
TODO
DECISIONS
CHANGELOG
archive
entire project
```
