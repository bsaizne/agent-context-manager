from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.checkpoint import run_checkpoint
from agent_context.project import init_project
from agent_context.utils import read_utf8, update_section, write_utf8


class CheckpointTests(unittest.TestCase):
    def test_checkpoint_updates_agent_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "sample"
            project.mkdir()
            init_project(project)
            source = project / "app.py"
            source.write_text("print('keep me')\n", encoding="utf-8")

            state_path = project / ".agent" / "STATE.md"
            state_text = read_utf8(state_path)
            state_text = update_section(state_text, "Current Task", "Implement checkpoint test.")
            write_utf8(state_path, state_text)

            summary = run_checkpoint(project)

            self.assertTrue(summary.archive_path.exists())
            self.assertEqual(source.read_text(encoding="utf-8"), "print('keep me')\n")
            self.assertNotIn("YYYY-MM-DD", read_utf8(state_path))
            changelog = read_utf8(project / ".agent" / "CHANGELOG.md")
            self.assertIn("checkpoint-", changelog)


if __name__ == "__main__":
    unittest.main()
