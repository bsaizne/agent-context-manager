"""The version used to live in three places and they disagreed (0.1.0 vs v0.5)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context import __version__

ROOT = Path(__file__).resolve().parents[1]


class VersionConsistencyTests(unittest.TestCase):
    def test_pyproject_matches_the_package(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), __version__)

    def test_gui_executable_name_uses_the_same_minor_version(self) -> None:
        spec = (ROOT / "agent-context-gui.spec").read_text(encoding="utf-8")
        match = re.search(r'name="Agent Context Manager v([0-9.]+)"', spec)
        self.assertIsNotNone(match)
        # The exe name carries either the full version (v0.8.1, patch releases)
        # or just the minor (v0.8). Either way it must start with the package's
        # major.minor - this still catches the historical 0.1.0-vs-v0.5 drift.
        self.assertEqual(
            match.group(1).split(".")[:2],
            __version__.split(".")[:2],
        )


if __name__ == "__main__":
    unittest.main()
