from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.project import init_project
from agent_context.resume import build_agent_prompt, build_resume, render_agent_prompt
from agent_context.templates import DEFAULT_AGENT_PROMPT_TEMPLATE
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


class AgentPromptTemplateTests(unittest.TestCase):
    """The handoff prompt must come from the user-editable template.

    The old prompt was hardcoded English ("Continue this project."), which
    read as a command to start working immediately. The whole reason the
    template became configurable is to let the user demand that the new agent
    stop and wait for instructions before touching anything.
    """

    def _make_project(self, root: Path) -> Path:
        project = root / "prompt-project"
        project.mkdir()
        init_project(project)
        return project

    def test_default_prompt_tells_agent_to_wait_for_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._make_project(Path(tmp))

            prompt = render_agent_prompt(project, template=DEFAULT_AGENT_PROMPT_TEMPLATE)

            self.assertIn("等我下达具体任务指令", prompt)
            self.assertIn("prompt-project", prompt)
            self.assertIn("AGENT CONTEXT RESUME", prompt)
            self.assertNotIn("Continue this project.", prompt)

    def test_custom_template_substitutes_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._make_project(Path(tmp))

            prompt = render_agent_prompt(project, template="HELLO {project}!\n---\n{resume}\n---\nEND")

            self.assertTrue(prompt.startswith("HELLO prompt-project!\n---\n"))
            self.assertIn("AGENT CONTEXT RESUME", prompt)
            self.assertTrue(prompt.rstrip().endswith("END"))
            self.assertNotIn("{resume}", prompt)

    def test_template_without_resume_placeholder_gets_context_appended(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._make_project(Path(tmp))

            prompt = render_agent_prompt(project, template="只说一句：等我指令再动手。")

            self.assertIn("等我指令再动手", prompt)
            # A handoff without the project state is useless, so the context
            # must still reach the agent even when the template omits it.
            self.assertIn("AGENT CONTEXT RESUME", prompt)
            self.assertIn("{resume} 占位符", prompt)

    def test_stray_braces_do_not_crash_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._make_project(Path(tmp))

            template = 'JSON 例子 {"a": 1}，继续 {resume}。'
            prompt = render_agent_prompt(project, template=template)

            self.assertIn('{"a": 1}', prompt)
            self.assertIn("AGENT CONTEXT RESUME", prompt)

    def test_build_agent_prompt_reads_user_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._make_project(Path(tmp))
            config_dir = Path(tmp) / "config"
            config_dir.mkdir()
            (config_dir / "config.json").write_text(
                json.dumps({"agent_prompt_template": "TEMPLATE {resume} END"}, ensure_ascii=False),
                encoding="utf-8",
            )
            old = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
            os.environ["AGENT_CONTEXT_CONFIG_DIR"] = str(config_dir)
            try:
                prompt = build_agent_prompt(project)
            finally:
                if old is None:
                    os.environ.pop("AGENT_CONTEXT_CONFIG_DIR", None)
                else:
                    os.environ["AGENT_CONTEXT_CONFIG_DIR"] = old

            self.assertTrue(prompt.startswith("TEMPLATE "))
            self.assertTrue(prompt.rstrip().endswith("END"))
            self.assertIn("AGENT CONTEXT RESUME", prompt)


if __name__ == "__main__":
    unittest.main()
