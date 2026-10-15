from __future__ import annotations

import unittest

import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401
from agent_context.doctor import run_doctor
from agent_context.project import init_project
from agent_context.resume import build_resume
from agent_context.state import (
    OPTIONAL_STATE_SECTIONS,
    REQUIRED_STATE_SECTIONS,
    SECTION_ORDER,
    _has_section,
    auto_repair_state,
    touch_state_last_updated,
    validate_state_text,
)
from agent_context.utils import ContextError, extract_section, read_utf8, update_section, write_utf8


class StateParsingTests(unittest.TestCase):
    def test_extracts_utf8_sections(self) -> None:
        text = "# PROJECT STATE\n\n## Project\n\n中文项目 🚀\n\n## Current Task\n\n实现恢复协议。\n"
        self.assertEqual(extract_section(text, "Project"), "中文项目 🚀")
        self.assertEqual(extract_section(text, "Current Task"), "实现恢复协议。")

    def test_updates_section_without_appending_history(self) -> None:
        text = "# PROJECT STATE\n\n## Last Updated\n\n2026-01-01 10:00\n"
        updated = update_section(text, "Last Updated", "2026-08-23 22:00")
        self.assertIn("2026-08-23 22:00", updated)
        self.assertNotIn("2026-01-01 10:00", updated)




def _minimal_state_text() -> str:
    return (
        "# PROJECT STATE\n"
        "\n"
        "## Project\n"
        "\n"
        "演示项目 中文 🚀\n"
        "\n"
        "## Current Phase\n"
        "\n"
        "Testing\n"
        "\n"
        "## Current Task\n"
        "\n"
        "Verify STATE validation.\n"
        "\n"
        "## Next Actions\n"
        "\n"
        "- Run tests.\n"
        "\n"
        "## Last Updated\n"
        "\n"
        "2026-08-25 00:00\n"
    )


class StateValidationTests(unittest.TestCase):
    def test_required_sections_only_is_valid(self) -> None:
        missing_optional = validate_state_text(_minimal_state_text())
        self.assertEqual(
            missing_optional,
            [
                "Completed",
                "Current Problem",
                "Current Implementation",
                "Current Decision",
                "Important Constraints",
                "Known Issues",
            ],
        )

    def test_missing_required_section_raises(self) -> None:
        text = _minimal_state_text().replace("## Current Task", "## Renamed Task")
        with self.assertRaises(ContextError) as ctx:
            validate_state_text(text)
        self.assertIn("Current Task", ctx.exception.reason or "")

    def test_missing_optional_sections_do_not_raise(self) -> None:
        text = _minimal_state_text()
        self.assertEqual(len(validate_state_text(text)), len(OPTIONAL_STATE_SECTIONS))


class StateAutoRepairTests(unittest.TestCase):
    def test_auto_repair_adds_only_missing_optionals(self) -> None:
        original = _minimal_state_text()
        repaired = auto_repair_state(original)

        for name in SECTION_ORDER:
            self.assertTrue(_has_section(repaired, name))
        self.assertIn("- None recorded.", repaired)
        self.assertIn("演示项目 中文 🚀", repaired)

        # Existing required content must not be changed.
        self.assertIn("Verify STATE validation.", repaired)
        # Repair is stable after a second pass.
        self.assertEqual(auto_repair_state(repaired), repaired)

    def test_auto_repair_preserves_empty_sections(self) -> None:
        text = _minimal_state_text() + "\n## Known Issues\n\n\n"
        repaired = auto_repair_state(text)
        known = extract_section(repaired, "Known Issues")
        self.assertEqual(known, "")
        self.assertNotIn("- None known.", repaired)

    def test_auto_repair_handles_crlf_and_reordered_sections(self) -> None:
        crlf = _minimal_state_text().replace("\n", "\r\n")
        repaired = auto_repair_state(crlf)
        self.assertNotIn("\r", repaired)

        headings = [line[3:] for line in repaired.splitlines() if line.startswith("## ")]
        self.assertEqual(headings, SECTION_ORDER)
        self.assertEqual(auto_repair_state(repaired), repaired)
        self.assertEqual(headings, SECTION_ORDER)


class StateWorkflowTests(unittest.TestCase):
    def test_checkpoint_repairs_minimal_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "repair-project"
            project.mkdir()
            init_project(project)
            state_path = project / ".agent" / "STATE.md"
            write_utf8(state_path, _minimal_state_text())

            touch_state_last_updated(project)
            repaired = read_utf8(state_path)

            for name in SECTION_ORDER:
                self.assertTrue(_has_section(repaired, name))
            self.assertIn("演示项目 中文 🚀", repaired)

    def test_resume_works_with_required_sections_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "resume-minimal"
            project.mkdir()
            init_project(project)
            write_utf8(project / ".agent" / "STATE.md", _minimal_state_text())

            resume = build_resume(project)
            self.assertIn("演示项目 中文 🚀", resume)
            self.assertIn("Verify STATE validation.", resume)

    def test_doctor_reports_missing_required_as_error_and_missing_optional_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "doctor-project"
            project.mkdir()
            init_project(project)
            state_path = project / ".agent" / "STATE.md"

            write_utf8(state_path, _minimal_state_text())
            warning_check = next(c for c in run_doctor(project) if c.name == "STATE.md sections")
            self.assertFalse(warning_check.ok)
            self.assertEqual(warning_check.severity, "warning")
            self.assertIn("missing optional", warning_check.detail)

            broken = _minimal_state_text().replace("## Next Actions", "## Later Actions")
            write_utf8(state_path, broken)
            error_check = next(c for c in run_doctor(project) if c.name == "STATE.md sections")
            self.assertFalse(error_check.ok)
            self.assertEqual(error_check.severity, "error")
            self.assertIn("missing required", error_check.detail)


if __name__ == "__main__":
    unittest.main()
