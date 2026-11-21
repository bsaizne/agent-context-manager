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
                "index": window.doc_pages["INDEX.md"],
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

    def test_open_popup_never_creates_opaque_roll_effect_window(self) -> None:
        """Regression: opening a dropdown flashed a black box for ~150ms.

        With Windows' "slide open combo boxes" on, Qt enables UI_AnimateCombo
        and animates the popup through a QRollEffect, an opaque top-level that
        repaints a snapshot of the translucent popup, so its transparent corners
        and shadow margin showed black. showPopup() must suppress that effect
        (and restore the global flag) while still fading the real popup in.
        """
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QEvent, QObject, Qt
        from PySide6.QtWidgets import QApplication, QWidget
        from agent_context.gui import MainWindow

        app = _qt_app()
        created: list[str] = []

        class _Spy(QObject):
            def eventFilter(self, obj, event):  # noqa: N802 - Qt API name
                if event.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
                    created.append(obj.metaObject().className())
                return False

        spy = _Spy()
        # isEffectEnabled(UI_AnimateCombo) also requires UI_General, which the
        # offscreen platform leaves off; enable both so Qt really would roll.
        previous = {
            eff: QApplication.isEffectEnabled(eff)
            for eff in (Qt.UIEffect.UI_General, Qt.UIEffect.UI_AnimateCombo)
        }
        QApplication.setEffectEnabled(Qt.UIEffect.UI_General, True)
        QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, True)
        self.assertTrue(QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateCombo))
        app.installEventFilter(spy)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                window = MainWindow(tmp)
                window.show()
                combo = window.recent_combo
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("最近项目", "")
                combo.addItem("alpha", str(Path(tmp) / "alpha"))
                combo.setCurrentIndex(0)
                combo.blockSignals(False)

                combo.showPopup()
                app.processEvents()
                self.assertNotIn("QRollEffect", created)
                self.assertTrue(QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateCombo))
                self.assertIsNotNone(combo._popup_anim)
                combo.hidePopup()
                self.assertIsNone(combo._popup_anim)
                window.close()
        finally:
            app.removeEventFilter(spy)
            for eff, enabled in previous.items():
                QApplication.setEffectEnabled(eff, enabled)


class GuiOverviewPolishTests(unittest.TestCase):
    """Regressions for overview readability, transparent card labels, and tooltips.

    1. Global `QMainWindow, QWidget { background: bg }` painted gray bars behind
       labels inside white/dark cards until `QLabel` and `#cardInner` were made
       explicitly transparent.
    2. Raw Markdown (`**bold**`, `` `code` ``) leaked into Overview phase/task
       labels and long phase text clipped on the right because word-wrap was off.
    3. The 5-step onboarding guide sat permanently above metrics even after a
       project was loaded; it is now collapsible and collapsed by default once
       loaded.
    """

    def test_inline_markdown_escapes_html_and_formats_bold_and_code(self) -> None:
        from agent_context.gui import _render_inline_markdown

        rendered = _render_inline_markdown("完成 **发布**，处理 `a*b.xlsx` & <script>")
        self.assertIn("<b>发布</b>", rendered)
        self.assertIn("a*b.xlsx</span>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)

    def test_loaded_overview_wraps_hero_collapses_guide_and_sets_recent_tooltips(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel, QToolButton
        from agent_context.gui import MainWindow
        from agent_context.project import init_project

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-proj"
            project.mkdir()
            init_project(project)
            window = MainWindow(project)

            qss = window.styleSheet()
            self.assertIn("QLabel { background:transparent; }", qss)
            self.assertIn("QMenu {", qss)

            # Hero phase & task labels must wrap so long lines never clip.
            hero_labels = [
                lbl for lbl in window.overview.findChildren(QLabel)
                if lbl.text().startswith("当前阶段") or lbl.text().startswith("当前任务")
            ]
            self.assertEqual(len(hero_labels), 2)
            for lbl in hero_labels:
                self.assertTrue(lbl.wordWrap())

            # Guide card is collapsible and starts collapsed when a project is loaded.
            toggles = [
                btn for btn in window.overview.findChildren(QToolButton)
                if btn.objectName() == "guideToggle"
            ]
            self.assertEqual(len(toggles), 1)
            self.assertFalse(toggles[0].isChecked())
            toggles[0].click()
            self.assertTrue(toggles[0].isChecked())
            self.assertTrue(window._guide_expanded)

            # Recent project entries expose full directory path as tooltip.
            self.assertGreaterEqual(window.recent_combo.count(), 2)
            self.assertEqual(
                window.recent_combo.itemData(1, Qt.ItemDataRole.ToolTipRole),
                str(project),
            )
            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
