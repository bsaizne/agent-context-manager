from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.project import init_project
from agent_context.resume import build_resume
from agent_context.utils import read_utf8, update_section, write_utf8


class ResumeTests(unittest.TestCase):
    def test_resume_is_short_and_uses_current_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "resume-project"
            project.mkdir()
            init_project(project)
            state_path = project / ".agent" / "STATE.md"
            state_text = read_utf8(state_path)
            state_text = update_section(state_text, "Project", "Resume Project")
            state_text = update_section(state_text, "Current Task", "Improve temporal ranking.")
            state_text = update_section(state_text, "Current Problem", "Similar frames can rank incorrectly.")
            write_utf8(state_path, state_text)

            resume = build_resume(project)

            self.assertIn("Resume Project", resume)
            self.assertIn("Improve temporal ranking.", resume)
            self.assertIn("Read AGENTS.md first.", resume)
            self.assertNotIn("DECISIONS", resume)
            self.assertNotIn("CHANGELOG", resume)
            self.assertNotIn("archive", resume.lower())


if __name__ == "__main__":
    unittest.main()
