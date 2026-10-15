"""Regression tests for the structure-repair path.

These cover three defects found while repairing a damaged real-world project:

1. ``extract_heading_by_prefix`` used ``.*$`` together with ``re.DOTALL``. The dot
   matched newlines, the greedy match swallowed the rest of the document and the
   capture group came back empty -- so ``status``/``resume`` reported zero pending
   tasks for every project, including freshly initialised ones.
2. ``auto_repair_state`` reset the block list when a heading occurred twice, which
   silently discarded everything the first occurrence held (a 75-line
   ``## Current Task`` section was lost this way).
3. ``touch_state_last_updated`` validated before repairing, so a STATE.md missing
   required sections could never be repaired by ``checkpoint`` -- the two halves
   of the flow were deadlocked.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.checkpoint import run_checkpoint
from agent_context.project import init_project
from agent_context.state import (
    auto_repair_state,
    ensure_todo_heading,
    find_duplicate_sections,
    find_duplicate_todo_sections,
    load_snapshot,
    merge_duplicate_sections,
    repair_project,
    todo_section_key,
    touch_state_last_updated,
)
from agent_context.templates import todo_template
from agent_context.utils import (
    ContextError,
    count_markdown_tasks,
    extract_heading_by_prefix,
    read_utf8,
    write_utf8,
)


class HeadingPrefixTests(unittest.TestCase):
    def test_returns_section_body_not_empty(self) -> None:
        text = (
            "# TODO\n"
            "\n"
            "## P0 — Current\n"
            "\n"
            "- [ ] First task.\n"
            "- [ ] Second task.\n"
            "\n"
            "## P1 — Next\n"
            "\n"
            "- [ ] Later task.\n"
        )
        p0 = extract_heading_by_prefix(text, "P0")
        self.assertIn("First task.", p0)
        self.assertIn("Second task.", p0)
        self.assertNotIn("Later task.", p0)
        self.assertNotIn("P1", p0)

        p1 = extract_heading_by_prefix(text, "P1")
        self.assertIn("Later task.", p1)
        self.assertNotIn("First task.", p1)

    def test_extracts_last_section_before_eof(self) -> None:
        text = "# TODO\n\n## Blocked\n\n- [ ] Waiting on GPU runner.\n"
        self.assertIn("Waiting on GPU runner.", extract_heading_by_prefix(text, "Blocked"))

    def test_template_todo_yields_non_zero_counts(self) -> None:
        todo = todo_template()
        for prefix in ("P0", "P1", "P2"):
            section = extract_heading_by_prefix(todo, prefix)
            self.assertEqual(count_markdown_tasks(section), 1, f"{prefix} should count 1 task")

    def test_missing_section_returns_empty(self) -> None:
        self.assertEqual(extract_heading_by_prefix("# TODO\n\n## P0\n\n- [ ] x\n", "P2"), "")


class AutoRepairMergeTests(unittest.TestCase):
    def test_duplicate_sections_are_merged_not_overwritten(self) -> None:
        text = (
            "## Current Task\n"
            "\n"
            "NEWEST WORK.\n"
            "\n"
            "## Project\n"
            "\n"
            "Demo project.\n"
            "\n"
            "## Current Task\n"
            "\n"
            "OLDER WORK.\n"
        )
        self.assertEqual(find_duplicate_sections(text), ["Current Task"])

        repaired = auto_repair_state(text)
        self.assertIn("NEWEST WORK.", repaired)
        self.assertIn("OLDER WORK.", repaired)
        self.assertIn("Demo project.", repaired)
        self.assertTrue(repaired.startswith("# PROJECT STATE"))

        # Repair must be stable: running it again changes nothing.
        self.assertEqual(auto_repair_state(repaired), repaired)


class EnsureTodoHeadingTests(unittest.TestCase):
    def test_adds_missing_heading(self) -> None:
        self.assertTrue(ensure_todo_heading("## P0\n\n- [ ] x\n").startswith("# TODO"))

    def test_keeps_existing_heading(self) -> None:
        text = "# TODO\n\n## P0\n\n- [ ] x\n"
        self.assertEqual(ensure_todo_heading(text), text)


class TouchStateTests(unittest.TestCase):
    def test_repairs_state_missing_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "minimal"
            project.mkdir()
            init_project(project)
            write_utf8(project / ".agent" / "STATE.md", "## Project\n\nOnly project.\n")

            updated = touch_state_last_updated(project)
            for name in ("Current Task", "Next Actions", "Last Updated"):
                self.assertIn(f"## {name}", updated)


class RepairProjectTests(unittest.TestCase):
    def _damaged_state(self) -> str:
        return (
            "## Current Task\n"
            "\n"
            "最新一段工作。\n"
            "\n"
            "## Project\n"
            "\n"
            "Demo project.\n"
            "\n"
            "## Current Phase\n"
            "\n"
            "Phase 1\n"
            "\n"
            "## Current Task\n"
            "\n"
            "较早一段工作。\n"
        )

    def test_repair_recovers_damaged_state_and_checkpoint_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "damaged"
            project.mkdir()
            init_project(project)
            state_path = project / ".agent" / "STATE.md"
            write_utf8(state_path, self._damaged_state())

            # Damaged state blocks the normal read path.
            with self.assertRaises(ContextError):
                load_snapshot(project)

            report = repair_project(project)
            self.assertEqual(report.state_duplicate_sections, ["Current Task"])
            self.assertIn("Next Actions", report.state_missing_required)
            self.assertIn("Last Updated", report.state_missing_required)

            repaired = read_utf8(state_path)
            self.assertIn("最新一段工作。", repaired)
            self.assertIn("较早一段工作。", repaired)
            self.assertIn("Demo project.", repaired)

            # The whole point: checkpoint now works on a previously damaged file.
            summary = run_checkpoint(project)
            self.assertTrue(summary.archive_path.exists())

            # And a second repair is a no-op on the repaired file.
            self.assertFalse(repair_project(project).state_changed)

    def test_repair_adds_missing_todo_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "todo-heading"
            project.mkdir()
            init_project(project)
            write_utf8(project / ".agent" / "TODO.md", "## P0 — Current\n\n- [ ] x\n")

            report = repair_project(project)
            self.assertTrue(report.todo_heading_added)
            self.assertTrue(read_utf8(project / ".agent" / "TODO.md").startswith("# TODO"))

    def test_repair_reports_nothing_to_do_on_clean_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "clean"
            project.mkdir()
            init_project(project)

            report = repair_project(project)
            self.assertEqual(report.state_missing_required, [])
            self.assertEqual(report.state_missing_optional, [])
            self.assertEqual(report.state_duplicate_sections, [])
            self.assertFalse(report.todo_heading_added)


class TodoPriorityMergeTests(unittest.TestCase):
    """A second P0 block used to be parsed as nothing at all."""

    def test_merges_duplicate_priority_blocks_and_keeps_every_line(self) -> None:
        text = (
            "# TODO\n"
            "\n"
            "## P0 - Current\n"
            "\n"
            "- [ ] A\n"
            "\n"
            "## P1 - Next\n"
            "\n"
            "- [ ] B\n"
            "\n"
            "## P0 - Dup\n"
            "\n"
            "- [ ] C\n"
        )
        self.assertEqual(find_duplicate_todo_sections(text), ["P0"])

        merged = merge_duplicate_sections(text, key_fn=todo_section_key)
        self.assertIn("- [ ] A", merged)
        self.assertIn("- [ ] C", merged)
        self.assertEqual(count_markdown_tasks(extract_heading_by_prefix(merged, "P0")), 2)
        self.assertEqual(merge_duplicate_sections(merged, key_fn=todo_section_key), merged)

    def test_repair_project_reports_and_merges_todo_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "todo-dup"
            project.mkdir()
            init_project(project)
            write_utf8(project / ".agent" / "TODO.md", "# TODO\n\n## P0\n\n- [ ] A\n\n## P0\n\n- [ ] C\n")

            report = repair_project(project)

            self.assertEqual(report.todo_duplicate_sections, ["P0"])
            self.assertTrue(report.todo_changed)
            merged = read_utf8(project / ".agent" / "TODO.md")
            self.assertEqual(count_markdown_tasks(extract_heading_by_prefix(merged, "P0")), 2)
            self.assertFalse(repair_project(project).todo_changed)


if __name__ == "__main__":
    unittest.main()
