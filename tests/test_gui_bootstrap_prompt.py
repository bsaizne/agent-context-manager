from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from _helpers import SRC  # noqa: F401

try:  # The GUI tests need the optional gui extra (PySide6).
    import PySide6  # noqa: F401
except ImportError as exc:  # pragma: no cover - depends on the environment
    raise unittest.SkipTest("PySide6 is not installed; install the gui extra to run GUI tests.") from exc

from agent_context.gui import build_context_bootstrap_prompt

_APP = None


def _qt_app():
    """Keep exactly one QApplication alive for the whole test session.

    Creating it inside a test and letting it fall out of scope destroyed the
    application while icons and widgets still held pixmaps; Qt then aborted the
    process at exit with "QPaintDevice: Cannot destroy paint device that is being
    painted" (the same message an unclosed QPainter used to produce).
    """
    global _APP
    if _APP is None:
        from PySide6.QtWidgets import QApplication
        _APP = QApplication.instance() or QApplication([])
    return _APP


class GuiBootstrapPromptTests(unittest.TestCase):
    def test_bootstrap_prompt_targets_context_files_only(self) -> None:
        project_path = Path("C:/Projects/Demo")

        prompt = build_context_bootstrap_prompt(project_path)

        self.assertIn(str(project_path), prompt)
        self.assertIn("AGENTS.md", prompt)
        self.assertIn(".agent/STATE.md", prompt)
        self.assertIn(".agent/TODO.md", prompt)
        self.assertIn(".agent/INDEX.md", prompt)
        self.assertIn(".agent/DECISIONS.md", prompt)
        self.assertIn(".agent/CHANGELOG.md", prompt)
        self.assertIn("\u4e0d\u5f97\u4fee\u6539\u4e1a\u52a1\u4ee3\u7801", prompt)
        self.assertIn("\u4e0d\u8981\u7f16\u9020", prompt)
        self.assertIn("\u53ea\u5904\u7406\u8fd9\u4e2a\u9879\u76ee", prompt)
        self.assertIn("\u5b8c\u6210\u524d\u81ea\u68c0", prompt)

    def test_overview_exposes_bootstrap_button(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QPushButton
        from agent_context.gui import MainWindow

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(tmp)
            button_texts = [button.text() for button in window.findChildren(QPushButton)]

        self.assertIn("复制填充提示词", button_texts)
        app.processEvents()

    def test_every_navigation_entry_has_a_drawable_icon(self) -> None:
        """An unknown icon name must not abort the process (it used to)."""
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication  # noqa: F401
        from agent_context.gui import NAV, EDITABLE_FILES  # noqa: F401
        from agent_context.icons import icon

        app = _qt_app()
        keys = [entry[0] for entry in NAV] + [
            "checkpoint", "resume", "doctor", "settings", "folder", "arrow",
            "refresh", "copy", "save", "check", "warning", "moon", "system",
            "unknown-name-that-must-not-crash",
        ]
        for key in keys:
            with self.subTest(key=key):
                self.assertFalse(icon(key).isNull())
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
