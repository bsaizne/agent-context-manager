"""Version history (L1) regression tests.

Covers: snapshot de-duplication, the retention policy, diff classification,
CRLF noise, and the "no history yet" path used by the GUI.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.project import init_project
from agent_context.utils import read_utf8, write_utf8
from agent_context.versions import (
    build_diff_view,
    diff_lines,
    list_versions,
    new_line_numbers,
    normalize_text,
    recent_changes,
    record_version,
    summarize,
    versions_root,
)


class IsolatedConfigTest(unittest.TestCase):
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


class RecordVersionTests(IsolatedConfigTest):
    def _project(self, tmp: str) -> Path:
        project = Path(tmp) / "project"
        project.mkdir()
        init_project(project)
        return project

    def test_identical_content_is_not_stored_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp)
            state = project / ".agent" / "STATE.md"

            self.assertIsNotNone(record_version(project, "STATE.md"))
            self.assertIsNone(record_version(project, "STATE.md"))
            self.assertEqual(len(list_versions(project, "STATE.md")), 1)

            write_utf8(state, read_utf8(state).replace("Phase 1", "Phase 2"))
            self.assertIsNotNone(record_version(project, "STATE.md"))
            self.assertEqual(len(list_versions(project, "STATE.md")), 2)

    def test_explicit_text_is_recorded_without_touching_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp)
            before = read_utf8(project / ".agent" / "STATE.md")

            ref = record_version(project, "STATE.md", text="custom\ncontent\n", source="external")

            self.assertIsNotNone(ref)
            self.assertEqual(read_utf8(project / ".agent" / "STATE.md"), before)
            self.assertEqual(read_utf8(ref.path), "custom\ncontent\n")

    def test_history_lives_under_the_agent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp)
            record_version(project, "TODO.md")

            root = versions_root(project)
            self.assertEqual(root.parent.name, ".agent")
            self.assertTrue((root / "index.json").exists())

    def test_retention_keeps_recent_versions_and_one_per_day(self) -> None:
        config_dir = Path(os.environ["AGENT_CONTEXT_CONFIG_DIR"])
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text('{"version_history_limit": 3}', encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp)
            root = versions_root(project)
            directory = root / "STATE.md"
            directory.mkdir(parents=True, exist_ok=True)

            today = datetime.now()
            old_day = (today - timedelta(days=2)).strftime("%Y-%m-%d")
            yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

            entries: list[dict] = []

            def add(version_id: str, at: str, digest: str) -> None:
                (directory / f"{version_id}.md").write_text("x\n", encoding="utf-8")
                entries.append({"id": version_id, "at": at, "source": "save", "lines": 1, "digest": digest})

            old_id = f"{old_day}-090000-old00001"
            add(old_id, f"{old_day} 09:00:00", "old00001")
            first_yesterday = ""
            for index in range(5):
                version_id = f"{yesterday}-1200{index:02d}-abcd{index:04d}"
                if not first_yesterday:
                    first_yesterday = version_id
                add(version_id, f"{yesterday} 12:00:{index:02d}", f"abcd{index:04d}")
            (root / "index.json").write_text(json.dumps({"STATE.md": entries}), encoding="utf-8")

            ref = record_version(project, "STATE.md", text="fresh content\n")
            self.assertIsNotNone(ref)

            ids = [item.version_id for item in list_versions(project, "STATE.md")]
            self.assertEqual(len(ids), 5)
            self.assertIn(old_id, ids)
            self.assertIn(first_yesterday, ids)
            self.assertNotIn(f"{yesterday}-120001-abcd0001", ids)
            self.assertEqual(ids[-1], ref.version_id)


class DiffTests(unittest.TestCase):
    def test_classifies_insert_delete_and_equal(self) -> None:
        old = "alpha\nbeta\ngamma\n"
        new = "alpha\ngamma\ndelta\n"

        lines = diff_lines(old, new)
        summary = summarize(lines)

        self.assertEqual(summary.added, 1)
        self.assertEqual(summary.removed, 1)
        removed = [line for line in lines if line.kind == "delete"]
        added = [line for line in lines if line.kind == "insert"]
        self.assertEqual(removed[0].text, "beta")
        self.assertEqual(removed[0].old_no, 2)
        self.assertEqual(added[0].text, "delta")
        self.assertEqual(added[0].new_no, 3)

    def test_crlf_input_does_not_report_noise(self) -> None:
        old = "alpha\r\nbeta\r\n"
        new = "alpha\nbeta\n"
        self.assertEqual(summarize(diff_lines(old, new)).added, 0)
        self.assertEqual(normalize_text("a\r\nb"), "a\nb")

    def test_new_line_numbers_point_at_added_lines(self) -> None:
        old = "# TODO\n\n## P0\n\n- [ ] A\n"
        new = "# TODO\n\n## P0\n\n- [ ] A\n- [ ] B\n"
        self.assertEqual(new_line_numbers(old, new), [6])

    def test_build_diff_view_marks_every_line(self) -> None:
        view = build_diff_view("one\ntwo\n", "one\nthree\n")

        self.assertEqual(view.added, 1)
        self.assertEqual(view.removed, 1)
        self.assertEqual(len(view.kinds), len(view.text.splitlines()))
        self.assertEqual(view.kinds.count("insert"), 1)
        self.assertEqual(view.kinds.count("delete"), 1)
        self.assertIn("+ ", view.text)
        self.assertIn("- ", view.text)

    def test_build_diff_view_truncates_long_histories(self) -> None:
        old = "\n".join(f"line {i}" for i in range(50))
        new = "\n".join(f"changed {i}" for i in range(50))
        view = build_diff_view(old, new, max_lines=10)
        self.assertTrue(view.truncated)
        self.assertEqual(len(view.kinds), 10)


class RecentChangesTests(IsolatedConfigTest):
    def test_reports_every_file_even_without_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)

            changes = recent_changes(project)

            self.assertEqual(len(changes), 5)
            self.assertTrue(all(change.versions == 0 for change in changes))

    def test_reports_added_and_removed_since_the_previous_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            init_project(project)
            todo = project / ".agent" / "TODO.md"

            write_utf8(todo, "# TODO\n\n## P0\n\n- [ ] A\n")
            record_version(project, "TODO.md")
            write_utf8(todo, "# TODO\n\n## P0\n\n- [ ] A\n- [ ] B\n")
            record_version(project, "TODO.md")

            change = next(item for item in recent_changes(project) if item.filename == "TODO.md")

            self.assertEqual(change.added, 1)
            self.assertEqual(change.removed, 0)
            self.assertEqual(change.versions, 2)
            self.assertTrue(change.at)


if __name__ == "__main__":
    unittest.main()
