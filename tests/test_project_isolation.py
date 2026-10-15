from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.project import find_initialized_project_path, init_project
from agent_context.resume import build_resume
from agent_context.utils import read_utf8, update_section, write_utf8


class ProjectIsolationTests(unittest.TestCase):
    def test_find_initialized_project_path_walks_up_from_nested_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "Project"
            nested = project / "src" / "feature"
            nested.mkdir(parents=True)
            init_project(project)

            self.assertEqual(find_initialized_project_path(nested), project.resolve())

    def test_resume_reads_only_current_project_agent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_a = root / "ProjectA"
            project_b = root / "ProjectB"
            project_a.mkdir()
            project_b.mkdir()
            init_project(project_a)
            init_project(project_b)

            for project, name in [(project_a, "Alpha State"), (project_b, "Beta State")]:
                state_path = project / ".agent" / "STATE.md"
                state_text = read_utf8(state_path)
                state_text = update_section(state_text, "Project", name)
                write_utf8(state_path, state_text)

            resume_a = build_resume(project_a)
            resume_b = build_resume(project_b)

            self.assertIn("Alpha State", resume_a)
            self.assertNotIn("Beta State", resume_a)
            self.assertIn("Beta State", resume_b)
            self.assertNotIn("Alpha State", resume_b)


if __name__ == "__main__":
    unittest.main()
