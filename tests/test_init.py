from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.project import init_project


class InitTests(unittest.TestCase):
    def test_init_creates_context_files_and_preserves_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "中文项目"
            project.mkdir()
            first = init_project(project)

            self.assertTrue((project / ".agent" / "STATE.md").exists())
            self.assertTrue((project / ".agent" / "TODO.md").exists())
            self.assertTrue((project / ".agent" / "archive").is_dir())
            self.assertTrue((project / "AGENTS.md").exists())
            self.assertIn("AGENTS.md", first.created)

            (project / "AGENTS.md").write_text("custom instructions\n", encoding="utf-8")
            second = init_project(project)

            self.assertEqual((project / "AGENTS.md").read_text(encoding="utf-8"), "custom instructions\n")
            self.assertIn("AGENTS.md already exists. Skipped.", second.skipped)


if __name__ == "__main__":
    unittest.main()
