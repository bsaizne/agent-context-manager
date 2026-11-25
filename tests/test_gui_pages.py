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

    def test_topbar_hides_switch_button_until_path_edited(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from agent_context.gui import MainWindow

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "proj-a"
            p2 = Path(tmp) / "proj-b"
            p1.mkdir()
            p2.mkdir()
            window = MainWindow(p1)

            self.assertEqual(window.browse_btn.text(), "选择目录")
            self.assertTrue(window.switch_btn.isHidden())

            window.path_edit.setText(str(p2))
            self.assertFalse(window.switch_btn.isHidden())

            window.path_edit.setText(str(p1))
            self.assertTrue(window.switch_btn.isHidden())

            window.path_edit.setText(str(p2))
            self.assertFalse(window.switch_btn.isHidden())
            window.switch_btn.click()
            self.assertEqual(window.project_path, p2.resolve())
            self.assertTrue(window.switch_btn.isHidden())

            window.close()
            app.processEvents()


class GuiDeleteProjectTests(unittest.TestCase):
    """Verify remove-from-app vs delete-folder project deletion and safety guards."""

    def test_dialog_defaults_to_remove_only_and_requires_name_for_folder_delete(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from agent_context.gui import DeleteProjectDialog, _protected_delete_reason

        _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "sample-app"
            project.mkdir()
            dlg = DeleteProjectDialog(project)

            self.assertFalse(dlg.delete_folder)
            self.assertTrue(dlg.confirm_btn.isEnabled())
            self.assertEqual(dlg.confirm_btn.objectName(), "primary")
            self.assertTrue(dlg.danger_box.isHidden())

            dlg.delete_folder_radio.setChecked(True)
            self.assertTrue(dlg.delete_folder)
            self.assertTrue(dlg.use_trash)
            self.assertFalse(dlg.danger_box.isHidden())
            self.assertEqual(dlg.confirm_btn.objectName(), "danger")
            self.assertFalse(dlg.confirm_btn.isEnabled())

            dlg.confirm_edit.setText("wrong-name")
            self.assertFalse(dlg.confirm_btn.isEnabled())
            dlg.confirm_edit.setText("sample-app")
            self.assertTrue(dlg.confirm_btn.isEnabled())

            dlg.trash_checkbox.setChecked(False)
            self.assertFalse(dlg.use_trash)
            dlg.close()

        # High-risk directories must be protected from folder deletion.
        home = Path.home()
        self.assertIsNotNone(_protected_delete_reason(home))
        self.assertIsNotNone(_protected_delete_reason(Path(home.anchor)))
        home_dlg = DeleteProjectDialog(home)
        self.assertFalse(home_dlg.delete_folder_radio.isEnabled())
        home_dlg.close()

    def test_remove_from_app_and_delete_folder_with_readonly_file(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import stat
        from agent_context.gui import MainWindow

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "proj-one"
            p2 = Path(tmp) / "proj-two"
            p1.mkdir()
            p2.mkdir()
            ro = p1 / "readonly.txt"
            ro.write_text("locked", encoding="utf-8")
            os.chmod(ro, stat.S_IREAD)

            window = MainWindow(p1)
            prev_project = window.settings.value("project_path", "", type=str)
            prev_recent = window.settings.value("recent_projects", [], type=list) or []
            try:
                window.settings.setValue("recent_projects", [str(p1), str(p2)])
                window._set_project_path(p2, persist=True)
                self.assertEqual(window.project_path, p2.resolve())

                # 1) Remove p2 from app only: folder stays on disk, switches back to p1.
                self.assertTrue(window._execute_delete_project(p2.resolve(), delete_folder=False))
                self.assertTrue(p2.exists())
                self.assertEqual(window.project_path, p1.resolve())
                recent_items = [
                    window.recent_combo.itemData(i)
                    for i in range(1, window.recent_combo.count())
                ]
                self.assertNotIn(str(p2.resolve()), recent_items)

                # 2) Delete p1 folder permanently (with read-only file): folder gone, enters empty state.
                self.assertTrue(
                    window._execute_delete_project(p1.resolve(), delete_folder=True, use_trash=False)
                )
                self.assertFalse(p1.exists())
                self.assertFalse(window._has_project)
                self.assertEqual(window.path_edit.text(), "")
                self.assertFalse(window.delete_btn.isEnabled())
                self.assertEqual(window.recent_combo.count(), 1)
            finally:
                window.settings.setValue("project_path", prev_project)
                window.settings.setValue("recent_projects", prev_recent)
                window.settings.sync()
                if ro.exists():
                    os.chmod(ro, stat.S_IWRITE)
                window.close()
                app.processEvents()


class GuiDoctorAndLimitsTests(unittest.TestCase):
    """Verify actionable Doctor page, trim prompt, and Settings line-limit controls."""

    def test_doctor_sorts_warnings_first_drops_duplicate_check_and_jumps_on_double_click(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from agent_context.config import load_config
        from agent_context.gui import MainWindow
        from agent_context.project import init_project

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "cfg"
            cfg_dir.mkdir()
            old_cfg_env = os.environ.get("AGENT_CONTEXT_CONFIG_DIR")
            os.environ["AGENT_CONTEXT_CONFIG_DIR"] = str(cfg_dir)
            try:
                project = Path(tmp) / "demo"
                project.mkdir()
                init_project(project)
                todo_path = project / ".agent" / "TODO.md"
                # Exceed default 100-line limit with completed items so warning triggers.
                done_lines = "\n".join(f"- [x] Done item {i}" for i in range(110))
                todo_path.write_text(
                    f"# TODO\n\n## P0 — Current\n\n{done_lines}\n- [ ] Still pending\n",
                    encoding="utf-8",
                )

                window = MainWindow(project)
                self.assertIn("QPushButton:disabled", window.styleSheet())
                self.assertFalse(hasattr(window, "doctor_trim_btn"))
                window._navigate_by_key("doctor")

                self.assertGreater(window.doctor_list.count(), 0)
                first_text = window.doctor_list.item(0).text()
                # Warning must be pinned to the top and show a Chinese suggestion, with no duplicate checkmark prefix.
                self.assertIn("TODO.md 行数检查", first_text)
                self.assertIn("建议：", first_text)
                for i in range(window.doctor_list.count()):
                    self.assertFalse(window.doctor_list.item(i).text().startswith("✓"))

                # Archive button is shown when checked items exist and hidden when none remain.
                self.assertIn("(110)", window.doctor_archive_btn.text())
                self.assertFalse(window.doctor_archive_btn.isHidden())

                # Resume automatically carries a Maintenance note when over limit.
                self.assertIn("Maintenance:", window.resume_view.toPlainText())

                # Double-clicking the TODO.md size item jumps straight to the TODO editor page.
                window._doctor_item_activated(window.doctor_list.item(0))
                self.assertIs(window.stack.currentWidget(), window.doc_pages["TODO.md"])

                # Saving new line limits in Settings persists to config.json, refreshes Doctor & clears Maintenance note.
                window.state_limit_edit.setText("180")
                window.todo_limit_edit.setText("220")
                window._save_line_limits()
                saved = load_config()
                self.assertEqual(saved["max_state_lines"], 180)
                self.assertEqual(saved["max_todo_lines"], 220)
                self.assertIn("全部", window.doctor_summary.text())
                self.assertNotIn("Maintenance:", window.resume_view.toPlainText())

                # Once no completed items remain, the archive button stays hidden instead of looking like a dead button.
                todo_path.write_text("# TODO\n\n## P0 — Current\n\n- [ ] Only pending\n", encoding="utf-8")
                window._doctor()
                self.assertTrue(window.doctor_archive_btn.isHidden())
                self.assertTrue(window.todo_archive_btn.isHidden())

                window.close()
                app.processEvents()
            finally:
                if old_cfg_env is None:
                    os.environ.pop("AGENT_CONTEXT_CONFIG_DIR", None)
                else:
                    os.environ["AGENT_CONTEXT_CONFIG_DIR"] = old_cfg_env

    def test_checkpoint_page_lists_and_previews_archive_snapshots_newest_first(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from agent_context.gui import MainWindow
        from agent_context.project import init_project

        app = _qt_app()
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "proj"
            project.mkdir()
            init_project(project)
            archive_dir = project / ".agent" / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            (archive_dir / "checkpoint-2026-11-24-090000.md").write_text("# Checkpoint\n\nOLDER SNAPSHOT\n", encoding="utf-8")
            (archive_dir / "checkpoint-2026-11-25-101500.md").write_text("# Checkpoint\n\nNEWER SNAPSHOT\n", encoding="utf-8")

            window = MainWindow(project)
            window._navigate_by_key("checkpoint")

            self.assertEqual(window.archive_list.count(), 2)
            self.assertEqual(window.archive_list.item(0).text(), "2026-11-25 10:15:00")
            self.assertEqual(window.archive_list.item(1).text(), "2026-11-24 09:00:00")
            self.assertIn("NEWER SNAPSHOT", window.archive_preview.toPlainText())
            self.assertTrue(window.archive_copy_btn.isEnabled())

            window.archive_list.setCurrentRow(1)
            self.assertIn("OLDER SNAPSHOT", window.archive_preview.toPlainText())

            window.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
