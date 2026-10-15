# Contributing

Thanks for taking a look. This is a small, dependency-light project, so this guide is short.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows: .venv/bin/activate on macOS and Linux
pip install -e ".[test,gui]"
pytest -q
```

The `test` extra alone is enough for the CLI; the GUI tests import PySide6 and skip
themselves when the `gui` extra is missing.

## Before opening a pull request

- Run the whole suite: `pytest -q`, or `python -m unittest discover -s tests` with no extra
  dependencies installed.
- Keep the core promise: the tool writes nothing outside `<project>/.agent/` (plus the
  `AGENTS.md` created once by `init`).
- Add a regression test for every bug fix, and make the test describe what it would have
  caught. Several tests in `tests/test_repair.py` and `tests/test_versions.py` exist only
  because a real bug slipped through.
- If you touch the PyInstaller specs, keep the Windows build **onedir** - see the Packaging
  section of the README for the failure mode that forced it.
- Comments explain *why* a line exists when the reason is not obvious. Please keep that
  style; an unexplained workaround gets deleted by the next person.

## Reporting a bug

Include the output of `agent-context doctor`, your Python version, and - when the GUI is
involved - whether the same thing happens from the CLI.
