"""Regression tests for checkpoint behaviour changed in 0.5.

1. A missing "# TODO" heading aborted the whole run *after* STATE.md had been
   rewritten, leaving no archive and no changelog entry.
2. Two checkpoints inside one minute collided on a single archive filename.
3. A duplicated P0 block in TODO.md was invisible to status/resume.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.checkpoint import run_checkpoint
from agent_context.project import init_project
from agent_context.state import repair_project
from agent_context.status import get_status
from agent_context.utils import read_utf8, write_utf8


class ConfigIsolatedTest(unittest.TestCase):
    """Keep the user's real ~/.agent-context/config.json out of these tests."""

    def setUp(self) -> None:
        self._config_dir = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
        os.environ["AGENT_CONTEXT_CONFIG_DIR"] = self._config_dir.name

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("AGENT_CONTEXT_CONFIG_DIR", None)
        else:
            os.environ["AGENT_CONTEXT_CONFIG_DIR"] = self._previous
        self._config_dir.cleanup()


class CheckpointRepairTests(ConfigIsolatedTest):
    def test_checkpoint_repairs_missing_todo_heading_instead_of_aborting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)
            write_utf8(project / ".agent" / "TODO.md", "## P0 - Current\n\n- [ ] A\n")

            summary = run_checkpoint(project)

            self.assertTrue(summary.todo_repaired)
            self.assertTrue(read_utf8(project / ".agent" / "TODO.md").startswith("# TODO"))
            self.assertIsNotNone(summary.archive_path)
            self.assertTrue(summary.archive_path.exists())
            self.assertIn("checkpoint-", read_utf8(project / ".agent" / "CHANGELOG.md"))


class CheckpointArchiveTests(ConfigIsolatedTest):
    def test_two_checkpoints_in_the_same_minute_produce_two_archives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)

            first = run_checkpoint(project)
            second = run_checkpoint(project)

            self.assertNotEqual(first.archive_path, second.archive_path)
            self.assertTrue(first.archive_path.exists())
            self.assertTrue(second.archive_path.exists())
            self.assertEqual(len(list((project / ".agent" / "archive").glob("checkpoint-*.md"))), 2)

    def test_archive_can_be_disabled_by_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            init_project(project)
            Path(os.environ["AGENT_CONTEXT_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
            (Path(os.environ["AGENT_CONTEXT_CONFIG_DIR"]) / "config.json").write_text(
                '{"archive_enabled": false}', encoding="utf-8"
            )

            summary = run_checkpoint(project)

            self.assertFalse(summary.archive_written)
            self.assertIsNone(summary.archive_path)
            self.assertEqual(list((project / ".agent" / "archive").glob("checkpoint-*.md")), [])
            self.assertIn("archive_enabled", read_utf8(project / ".agent" / "CHANGELOG.md"))


class DuplicateTodoTests(ConfigIsolatedTest):
    def test_duplicate_priority_blocks_are_reported_then_merged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)
            todo = (
                "# TODO\n\n## P0 - Current\n\n- [ ] A\n\n## P1 - Next\n\n- [ ] B\n\n## P0 - Dup\n\n- [ ] C\n"
            )
            write_utf8(project / ".agent" / "TODO.md", todo)

            # Only the first P0 block is read, so C is invisible to status/resume.
            self.assertEqual(get_status(project).p0_count, 1)

            summary = run_checkpoint(project)
            self.assertEqual(summary.todo_duplicate_sections, ["P0"])

            report = repair_project(project)
            self.assertEqual(report.todo_duplicate_sections, ["P0"])
            merged = read_utf8(project / ".agent" / "TODO.md")
            self.assertIn("- [ ] A", merged)
            self.assertIn("- [ ] C", merged)
            self.assertEqual(get_status(project).p0_count, 2)
            self.assertFalse(repair_project(project).todo_changed)


if __name__ == "__main__":
    unittest.main()
