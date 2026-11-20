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

from test_gui_bootstrap_prompt import _qt_app


class GuiPageRoutingTests(unittest.TestCase):
    """Regression: each sidebar key must open its own page.

    _navigate() used to locate the tool pages with the arithmetic
    `index - len(NAV) + 1 + len(EDITABLE_FILES)`. That assumes NAV's
    non-overview entries map 1:1 onto the EDITABLE_FILES editors, but "changes"
    is also a NAV entry with its own stack slot, so every tool page was shifted
    by one: Checkpoint opened Changes, Resume opened Checkpoint, Doctor opened
    Resume and Settings opened Doctor. This test asserts the widget identity
    directly instead of trusting any index arithmetic.
    """

    def test_every_sidebar_key_shows_its_own_page(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication  # noqa: F401
        from agent_context.gui import MainWindow, NAV

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(tmp)
            expected = {
                "overview": window.overview,
                "state": window.doc_pages["STATE.md"],
                "tasks": window.doc_pages["TODO.md"],
                "decisions": window.doc_pages["DECISIONS.md"],
                "changelog": window.doc_pages["CHANGELOG.md"],
                "changes": window.changes_page,
                "checkpoint": window.checkpoint_page,
                "resume": window.resume_page,
                "doctor": window.doctor_page,
                "settings": window.settings_page,
            }
            for key, page in expected.items():
                with self.subTest(key=key):
                    window._navigate_by_key(key)
                    self.assertIs(window.stack.currentWidget(), page)
            # Same path a real user takes: clicking the sidebar buttons. The
            # button order is NAV keys followed by the tool keys.
            keys = [entry[0] for entry in NAV] + ["checkpoint", "resume", "doctor", "settings"]
            for button, key in zip(window.nav_buttons, keys):
                with self.subTest(key=key):
                    button.click()
                    self.assertIs(window.stack.currentWidget(), expected[key])
                    self.assertTrue(button.isChecked())
            app.processEvents()


class GuiChangesRowTests(unittest.TestCase):
    """Regression: the Changes controls must never overlap each other.

    A single controls row with two 200px-min version combos, the file combo
    (minimumSizeHint ~170px) and the checkbox could not fit the default 1200px
    window, let alone the 1000px minimum. QBoxLayout squeezed the arrow label
    and the checkbox on top of the combo borders, which read as "the arrow is
    boxed into the combo". The controls are now two rows; the test walks the
    layout geometry at both window widths and fails if any two items touch.
    """

    def _row_overlaps(self, window) -> list[tuple[int, int]]:
        card_layout = window.changes_file_combo.parent().layout()
        overlaps: list[tuple[int, int]] = []
        for i in range(card_layout.count()):
            sub = card_layout.itemAt(i).layout()
            if sub is None:
                continue
            geoms = [sub.itemAt(j).geometry() for j in range(sub.count())]
            for left, right in zip(geoms, geoms[1:]):
                if right.x() < left.x() + left.width():
                    overlaps.append((left.x() + left.width(), right.x()))
        return overlaps

    def test_controls_fit_at_minimum_and_default_window_width(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication  # noqa: F401
        from agent_context.gui import MainWindow

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(tmp)
            for width in (1000, 1200):
                with self.subTest(width=width):
                    window.resize(width, 800)
                    window._navigate_by_key("changes")
                    window.grab()  # forces a full layout pass at this size
                    self.assertEqual(self._row_overlaps(window), [])
            app.processEvents()


class GuiPromptTemplateCardTests(unittest.TestCase):
    """The Settings card must edit the handoff prompt template end to end."""

    def test_edit_save_and_reset_round_trip(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from agent_context.config import load_config
        from agent_context.gui import MainWindow
        from agent_context.project import init_project
        from agent_context.templates import DEFAULT_AGENT_PROMPT_TEMPLATE

        _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
            os.environ["AGENT_CONTEXT_CONFIG_DIR"] = str(Path(tmp) / "config")
            try:
                init_project(Path(tmp))  # no .agent yet -> resume view would stay empty by design
                window = MainWindow(tmp)
                edit = window.prompt_template_edit
                self.assertEqual(edit.toPlainText(), DEFAULT_AGENT_PROMPT_TEMPLATE)
                edit.setPlainText("自定义模板 {resume}")
                window._save_prompt_template()
                self.assertEqual(load_config()["agent_prompt_template"], "自定义模板 {resume}")
                # Resume view refreshes so what a user copies next already
                # reflects the saved template, not the previous one.
                self.assertIn("自定义模板", window.resume_view.toPlainText())
                window._reset_prompt_template()
                self.assertEqual(load_config()["agent_prompt_template"], DEFAULT_AGENT_PROMPT_TEMPLATE)
                self.assertEqual(edit.toPlainText(), DEFAULT_AGENT_PROMPT_TEMPLATE)
            finally:
                if old is None:
                    os.environ.pop("AGENT_CONTEXT_CONFIG_DIR", None)
                else:
                    os.environ["AGENT_CONTEXT_CONFIG_DIR"] = old


class GuiComboPopupTests(unittest.TestCase):
    """The dropdown popup must carry the app theme without Fusion/Windows artifacts.

    Three visual regressions were observed on Windows + Fusion:
    1. Window-level `QMainWindow, QWidget { background: ... }` painted
       QComboBoxPrivateContainer opaque, and its default StyledPanel frame drew
       a sharp gray rectangle around the rounded QListView corners.
    2. Fusion's SH_ComboBox_Popup overlaid the popup on top of the closed combo
       and added top/bottom scroller strips; `combobox-popup: 0` disables that.
    3. Opening "最近项目" displayed the non-selectable placeholder row (row 0)
       highlighted at the top of the list even when real recent projects existed.
    """

    def test_every_combobox_uses_frameless_polished_popup(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QFrame, QListView
        from agent_context.gui import MainWindow, _ComboItemDelegate

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(tmp)
            self.assertIn("combobox-popup:0;", window.styleSheet())
            combos = [
                window.recent_combo,
                window.changes_file_combo,
                window.changes_from_combo,
                window.changes_to_combo,
            ]
            for combo in combos:
                with self.subTest(combo=combo.objectName() or combo.toolTip() or str(combo)):
                    view = combo.view()
                    self.assertIsInstance(view, QListView)
                    self.assertIsInstance(view.itemDelegate(), _ComboItemDelegate)
                    popup = view.window()
                    flags = popup.windowFlags()
                    self.assertTrue(flags & Qt.FramelessWindowHint)
                    self.assertTrue(flags & Qt.NoDropShadowWindowHint)
                    self.assertTrue(popup.testAttribute(Qt.WA_TranslucentBackground))
                    self.assertEqual(popup.objectName(), "comboPopupContainer")
                    if isinstance(popup, QFrame):
                        self.assertEqual(popup.frameShape(), QFrame.Shape.NoFrame)
                    self.assertIn("background: transparent", popup.styleSheet())
            app.processEvents()

    def test_recent_combo_hides_placeholder_row_and_survives_theme_switch(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from agent_context.gui import MainWindow

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(tmp)
            combo = window.recent_combo
            self.assertEqual(combo.objectName(), "recentProjectCombo")

            # When recent projects exist, row 0 ("最近项目") stays as closed
            # display text while being hidden inside the open dropdown list.
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("最近项目", "")
            combo.addItem("alpha", str(Path(tmp) / "alpha"))
            combo.addItem("beta", str(Path(tmp) / "beta"))
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

            combo._adjust_popup()
            self.assertTrue(combo.view().isRowHidden(0))
            self.assertFalse(combo.view().isRowHidden(1))
            self.assertFalse(combo.view().isRowHidden(2))

            # With no recent projects, keep row 0 visible so the popup isn't blank.
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("最近项目", "")
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            combo._adjust_popup()
            self.assertFalse(combo.view().isRowHidden(0))

            # Switching between dark and light themes must refresh popup styling
            # and elevation shadow without error.
            for mode, expected_card in (("dark", "#2C2C2E"), ("light", "#FFFFFF")):
                with self.subTest(theme=mode):
                    window.theme_mode = mode
                    window._apply_theme()
                    self.assertIn(expected_card, combo.view().styleSheet())
                    self.assertIsInstance(combo.view().graphicsEffect(), QGraphicsDropShadowEffect)
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
