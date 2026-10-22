from __future__ import annotations

import sys
import ctypes
import subprocess
import time
import os
from pathlib import Path


# Do not add bundle-directory DLL preloading here.
#
# Builds 0.5-0.9 prepended sys._MEIPASS (and its PySide6/shiboken6
# subdirectories) to PATH and called os.add_dll_directory() before importing
# PySide6. Combined with a UCRT that PyInstaller had collected into the bundle,
# Windows then resolved ucrtbase.dll from the temporary extraction directory
# instead of C:\Windows\System32, and the app died at startup with
# "unable to locate procedure entry point ucrtv_open ... on Qt6Core.dll".
#
# PyInstaller already registers the bundle as a DLL search path, so the plain
# imports below are enough. Keep the bundle free of UCRT binaries instead; see
# agent-context-gui.spec.
#
# packaging/qt_runtime_hook.py did exactly what the comment above warns about. It
# was referenced by no spec and has been deleted in 0.5; do not reconnect it.

from PySide6.QtCore import QObject, QSettings, QThread, Qt, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAction, QColor, QFont, QIcon, QKeySequence, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QTextFormat,
)
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QComboBox, QRadioButton, QScrollArea, QSizePolicy, QStackedWidget, QStatusBar, QTextEdit,
    QToolButton, QVBoxLayout, QWidget,
)

from .archive import list_archives, read_archive
from .checkpoint import run_checkpoint
from .config import load_config
from .doctor import run_doctor
from .icons import icon
from .project import context_file_paths, find_initialized_project_path, init_project, resolve_project_path
from .resume import build_agent_prompt
from .state import repair_project
from .status import ProjectStatus, get_status
from .transfer import context_token_stats, export_project, import_project
from .utils import ContextError, read_utf8, write_utf8
from .versions import (
    build_diff_view, latest_version, list_versions, new_line_numbers, read_version_text,
    recent_changes, record_version,
)


EDITABLE_FILES = ["STATE.md", "TODO.md", "INDEX.md", "DECISIONS.md", "CHANGELOG.md"]
NAV = [("overview", "Overview", "概览"), ("state", "STATE.md", "状态"), ("tasks", "TODO.md", "任务"),
       ("decisions", "DECISIONS.md", "决策"), ("changelog", "CHANGELOG.md", "变更记录"),
       # "changes" is not an editor page: _navigate() routes it to self.changes_page.
       ("changes", "Changes", "变更")]


def resource_path(name: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle_root / "assets" / name


def app_icon() -> QIcon:
    ico_path = resource_path("branding.ico")
    if ico_path.exists():
        return QIcon(str(ico_path))
    return QIcon(str(resource_path("branding.svg")))


def set_windows_app_id() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "AgentContextManager.Desktop"
            )
        except (AttributeError, OSError):
            pass


def build_context_bootstrap_prompt(project_path: Path) -> str:
    files = [
        "AGENTS.md",
        ".agent/STATE.md",
        ".agent/TODO.md",
        ".agent/INDEX.md",
        ".agent/DECISIONS.md",
        ".agent/CHANGELOG.md",
    ]
    file_list = "\n".join(f"- `{item}`" for item in files)
    return f"""你现在负责为一个已有项目建立或补全 Agent 可接续使用的上下文档案。

## 项目范围

项目根目录：
`{project_path}`

所有相对路径都相对于这个目录。只处理这个项目，不要跨到父目录、兄弟目录或其他项目。

## 第一阶段：先读规则和现状

开始写文件前，先读取并遵守：
- 如果存在，读取项目根目录的 `AGENTS.md`。
- 读取项目中的 README、贡献指南、开发文档和明确的项目规则文件。
- 读取 `.agent/STATE.md`、`.agent/TODO.md`、`.agent/INDEX.md`、`.agent/DECISIONS.md`、`.agent/CHANGELOG.md`（如果存在）。
- 如果 `.agent` 文件已有真实内容，保留仍然正确的信息；不要把已有进度全部替换成模板或泛泛总结。

## 第二阶段：有边界地了解项目

重点检查：项目目标和产品用途、技术栈和依赖、入口文件、源码目录、测试目录、构建/运行脚本、配置文件、重要外部服务、当前 Git 状态，以及最近能确认的实现情况。

优先读取小而关键的文件。默认忽略：`.git`、`.agent/archive`、`build`、`dist`、`.venv`、`venv`、`node_modules`、缓存目录、覆盖率目录、二进制文件、媒体文件、生成物和明显的大型数据文件。不要为了“完整”读取整个仓库或把源代码复制进 Markdown。

如果项目有测试或静态检查命令，可以运行已有命令来确认状态；不要安装依赖、联网下载、启动长期运行的服务或修改环境。不能运行的命令要记录原因。

## 第三阶段：只更新上下文档案

除非用户明确要求，否则只允许修改这些文件：
{file_list}

不得修改业务代码、配置、依赖锁文件、测试、Git 历史、删除文件或重构项目。`AGENTS.md` 已经存在时，只在确有项目规则缺失且能从事实确认时补充，不要覆盖用户已有规则。

请按以下协议写入：
- `AGENTS.md`：项目协作规则、运行/测试/构建命令、重要目录、禁止误改的边界、上下文更新约定。
- `.agent/STATE.md`：按 `Project`、`Current Phase`、`Current Task`、`Completed`、`Current Problem`、`Current Implementation`、`Current Decision`、`Next Actions`、`Important Constraints`、`Known Issues`、`Last Updated` 组织；它表示当前状态，不是历史日志。
- `.agent/TODO.md`：按 P0/P1/P2/Blocked 列出短小、具体、可执行的任务，不重复 STATE.md 的长篇说明。
- `.agent/INDEX.md`：列出关键模块、路径、用途、相关文档和重要入口；不要复制源代码。
- `.agent/DECISIONS.md`：只记录重要决策，并说明 Decision、Reason、Alternatives、Rejected；不要写聊天记录。
- `.agent/CHANGELOG.md`：记录这次实际做了哪些上下文整理或项目变更；不要复制完整状态。

## 信息可靠性

把“已从文件/命令确认的事实”和“推断/待确认事项”分开。无法确认的信息写成 `待确认`，不要编造版本、命令、功能、完成情况或技术决策。不要把“文件存在”当成“功能已完成”。如果当前任务无法从项目中判断，写明需要用户确认的问题。

## 完成前自检

完成后检查：
1. 上述允许修改的文件是否存在且能正常读取。
2. STATE.md 是否有当前任务、完成项、问题、下一步和更新时间。
3. TODO.md 是否有优先级明确的下一步任务。
4. INDEX.md 是否能帮助新 Agent 找到关键文件。
5. 是否误改了允许列表之外的文件。
6. 如果运行了测试或检查，记录实际结果；没有运行则明确写明未运行及原因。

最后只汇报：更新了哪些文件、确认了哪些关键事实、哪些内容仍待确认、测试/检查结果和建议的下一步。"""


def relative_time(timestamp: float) -> str:
    if timestamp <= 0:
        return "未知"
    delta = max(0.0, time.time() - timestamp)
    if delta < 60:
        return "刚刚"
    if delta < 3600:
        return f"{int(delta // 60)} 分钟前"
    if delta < 86400:
        return f"{int(delta // 3600)} 小时前"
    return f"{int(delta // 86400)} 天前"


class CheckpointWorker(QObject):
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, project_path: Path) -> None:
        super().__init__(); self.project_path = project_path

    @Slot()
    def run(self) -> None:
        try: self.finished.emit(run_checkpoint(self.project_path))
        except (ContextError, OSError) as exc: self.failed.emit(exc)


class MarkdownHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        if text.startswith("#"):
            fmt = QTextCharFormat(); fmt.setForeground(QColor("#2775D3")); fmt.setFontWeight(QFont.Bold)
            self.setFormat(0, len(text), fmt)
        elif text.lstrip().startswith("-"):
            fmt = QTextCharFormat(); fmt.setForeground(QColor("#6E6E73")); self.setFormat(0, len(text), fmt)


class Page(QWidget):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__(); self.layout = QVBoxLayout(self); self.layout.setContentsMargins(28, 28, 28, 28); self.layout.setSpacing(20)
        heading = QVBoxLayout(); heading.setSpacing(6)
        self.title = QLabel(title); self.title.setObjectName("pageTitle"); heading.addWidget(self.title)
        if subtitle:
            self.subtitle = QLabel(subtitle); self.subtitle.setObjectName("pageSubtitle"); heading.addWidget(self.subtitle)
        self.layout.addLayout(heading)


class MainWindow(QMainWindow):
    def __init__(self, initial_path: str | Path | None = None) -> None:
        super().__init__(); self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "Agent Context Manager", "Agent Context Manager")
        saved_path = self.settings.value("project_path", "", type=str).strip()
        self.project_path = resolve_project_path(initial_path or saved_path or None)
        self.editors: dict[str, QPlainTextEdit] = {}; self.file_paths: dict[str, Path] = {}
        self.current_status: ProjectStatus | None = None; self.nav_buttons: list[QToolButton] = []
        self.checkpoint_thread: QThread | None = None; self.checkpoint_worker: CheckpointWorker | None = None
        self.checkpoint_buttons: list[QPushButton] = []
        self._pending_external_changes: list[str] = []
        self._project_load_message = ""
        # Cache key of the last rendered overview. _update_overview() rebuilds about 186
        # widgets on every call, and the 3s watcher called it even when nothing it
        # renders had changed.
        self._overview_key_cache: tuple | None = None
        self._recent_changes: list = []
        # Line-level marks are recomputed at most every 250ms while typing; a diff on
        # every keystroke would be wasteful and made no visible difference.
        self._marks_timer = QTimer(self); self._marks_timer.setSingleShot(True); self._marks_timer.setInterval(250)
        self._marks_timer.timeout.connect(lambda: self._apply_editor_marks())
        self._changes_view_kinds: list[str] | None = None
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(3000)
        self._watch_timer.timeout.connect(self._watch_check)
        self.theme_mode = "system"
        self.setWindowTitle("Agent Context Manager"); self.setWindowIcon(app_icon()); self.resize(1200, 800); self.setMinimumSize(1000, 700)
        self._build_ui(); self._apply_theme(); self._set_project_path(self.project_path, persist=False)

    def _build_ui(self) -> None:
        self._build_menu()
        shell = QWidget(); outer = QHBoxLayout(shell); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("sidebar"); self.sidebar.setFixedWidth(248)
        side = QVBoxLayout(self.sidebar); side.setContentsMargins(20, 24, 16, 20); side.setSpacing(8)
        brand = QHBoxLayout(); brand.setSpacing(10); mark = QLabel(); mark.setObjectName("brandMark"); mark.setPixmap(QIcon(str(resource_path("branding.svg"))).pixmap(32, 32)); mark.setFixedSize(32, 32); brand.addWidget(mark)
        brand_text = QVBoxLayout(); brand_text.setSpacing(0); name = QLabel("Agent Context"); name.setObjectName("brandName"); brand_text.addWidget(name)
        small = QLabel("PROJECT WORKSPACE"); small.setObjectName("eyebrow"); brand_text.addWidget(small); brand.addLayout(brand_text); side.addLayout(brand)
        side.addSpacing(24); project_label = QLabel("PROJECT"); project_label.setObjectName("eyebrow"); side.addWidget(project_label)
        self.nav_group = QButtonGroup(self); self.nav_group.setExclusive(True)
        for key, text, _ in NAV:
            b = self._nav_button(key, text); self.nav_group.addButton(b); side.addWidget(b); self.nav_buttons.append(b)
        side.addSpacing(20); tools_label = QLabel("TOOLS"); tools_label.setObjectName("eyebrow"); side.addWidget(tools_label)
        for key, text in [("checkpoint", "Checkpoint"), ("resume", "Resume"), ("doctor", "Doctor")]:
            b = self._nav_button(key, text); self.nav_group.addButton(b); side.addWidget(b); self.nav_buttons.append(b)
        side.addStretch(); self.project_name = QLabel("未加载项目"); self.project_name.setObjectName("sidebarProject"); self.project_name.setWordWrap(True); side.addWidget(self.project_name)
        settings = self._nav_button("settings", "Settings"); self.nav_group.addButton(settings); side.addWidget(settings)
        outer.addWidget(self.sidebar)

        content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(0, 0, 0, 0); content_layout.setSpacing(0)
        top = QFrame(); top.setObjectName("topbar"); top_layout = QHBoxLayout(top); top_layout.setContentsMargins(28, 18, 28, 18)
        self.recent_combo = QComboBox(); self.recent_combo.setMinimumWidth(220); self.recent_combo.setToolTip("最近打开的项目"); self.recent_combo.currentIndexChanged.connect(self._recent_project_selected); top_layout.addWidget(self.recent_combo)
        self.path_edit = QLineEdit(); self.path_edit.setPlaceholderText("项目目录"); self.path_edit.returnPressed.connect(self._open_project); top_layout.addWidget(self.path_edit, 1)
        browse = QPushButton("浏览"); browse.setIcon(icon("folder")); browse.clicked.connect(self._browse_project); top_layout.addWidget(browse)
        open_btn = QPushButton("打开"); open_btn.setIcon(icon("arrow")); open_btn.clicked.connect(self._open_project); top_layout.addWidget(open_btn); content_layout.addWidget(top)
        self.stack = QStackedWidget(); content_layout.addWidget(self.stack, 1); outer.addWidget(content, 1); self.setCentralWidget(shell)
        self.setStatusBar(QStatusBar()); self.statusBar().showMessage("请选择项目目录")
        self._refresh_recent_projects()
        self._make_pages(); self.nav_buttons[0].setChecked(True); self._navigate(0)

    def _nav_button(self, key: str, text: str) -> QToolButton:
        button = QToolButton(); button.setObjectName("navButton"); button.setText(text); button.setIcon(icon(key)); button.setIconSize(icon(key).availableSizes()[0] if icon(key).availableSizes() else button.sizeHint()); button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon); button.setCheckable(True); button.setAutoExclusive(True); button.clicked.connect(lambda: self._navigate_by_key(key)); return button

    def _make_pages(self) -> None:
        self.overview = Page("Overview", "项目上下文的当前快照和下一步行动")
        self.overview_body = QWidget(); self.overview_grid = QVBoxLayout(self.overview_body); self.overview_grid.setContentsMargins(0, 0, 0, 0); self.overview_grid.setSpacing(16)
        self.overview_scroll = QScrollArea(); self.overview_scroll.setObjectName("overviewScroll"); self.overview_scroll.setWidgetResizable(True); self.overview_scroll.setFrameShape(QFrame.NoFrame); self.overview_scroll.setWidget(self.overview_body); self.overview_scroll.setAlignment(Qt.AlignHCenter); self.overview_body.setMaximumWidth(760)
        self.overview.layout.addWidget(self.overview_scroll, 1); self.stack.addWidget(self.overview)
        self.doc_pages: dict[str, Page] = {}
        for filename in EDITABLE_FILES:
            page = Page(filename, "编辑项目上下文，保存后立即用于 checkpoint 和 resume")
            editor = QPlainTextEdit(); editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap); editor.setFont(QFont("Cascadia Mono", 10)); editor.setEnabled(False); MarkdownHighlighter(editor.document()); editor.document().modificationChanged.connect(self._update_dirty_label); editor.textChanged.connect(self._schedule_editor_marks)
            self.editors[filename] = editor; self.file_paths[filename] = Path(); self.doc_pages[filename] = page
            actions = QHBoxLayout(); dirty = QLabel(""); dirty.setObjectName("muted"); setattr(editor, "dirty_label", dirty); actions.addWidget(dirty); actions.addStretch(); open_ext = QPushButton("外部打开"); open_ext.setIcon(icon("folder")); open_ext.setToolTip("用系统默认程序打开该文件（可用 default_editor 配置指定编辑器）"); open_ext.clicked.connect(lambda _=False, name=filename: self._open_in_editor(name)); actions.addWidget(open_ext); save = QPushButton("保存"); save.setIcon(icon("save")); save.clicked.connect(self._save_current); actions.addWidget(save); page.layout.addWidget(editor, 1); page.layout.addLayout(actions); self.stack.addWidget(page)
        self._make_changes_page(); self._make_checkpoint_page(); self._make_resume_page(); self._make_doctor_page(); self._make_settings_page()

    def _make_changes_page(self) -> None:
        """Diff view: what was added (green) and removed (red) between two versions."""
        self.changes_page = Page("Changes", "查看每个文档新增了什么、删除了什么，以及发生的时间")
        controls = self._card()
        row = QHBoxLayout(controls); row.setContentsMargins(16, 14, 16, 14); row.setSpacing(8)
        row.addWidget(QLabel("文件"))
        self.changes_file_combo = QComboBox(); self.changes_file_combo.addItems(EDITABLE_FILES)
        self.changes_file_combo.currentIndexChanged.connect(self._refresh_changes)
        row.addWidget(self.changes_file_combo)
        row.addWidget(QLabel("对比"))
        self.changes_from_combo = QComboBox(); self.changes_from_combo.setMinimumWidth(200)
        self.changes_from_combo.currentIndexChanged.connect(self._render_changes)
        row.addWidget(self.changes_from_combo)
        arrow = QLabel("→"); row.addWidget(arrow)
        self.changes_to_combo = QComboBox(); self.changes_to_combo.setMinimumWidth(200)
        self.changes_to_combo.currentIndexChanged.connect(self._render_changes)
        row.addWidget(self.changes_to_combo)
        self.changes_use_editor = QCheckBox("右侧用编辑器内容")
        self.changes_use_editor.setToolTip("直接和不保存的编辑内容比较，边写边看增删")
        self.changes_use_editor.toggled.connect(self._render_changes)
        row.addWidget(self.changes_use_editor)
        refresh = QPushButton("刷新"); refresh.setIcon(icon("refresh")); refresh.clicked.connect(self._refresh_changes)
        row.addWidget(refresh); row.addStretch()
        self.changes_page.layout.addWidget(controls)

        self.changes_summary = QLabel("")
        self.changes_summary.setObjectName("pageSubtitle"); self.changes_summary.setWordWrap(True)
        self.changes_page.layout.addWidget(self.changes_summary)

        self.changes_view = QPlainTextEdit(); self.changes_view.setReadOnly(True)
        self.changes_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.changes_view.setFont(QFont("Cascadia Mono", 10))
        self.changes_view.setPlaceholderText("选择两个版本后，这里会显示新增（绿）与删除（红）的行")
        self.changes_page.layout.addWidget(self.changes_view, 1)
        self.stack.addWidget(self.changes_page)

    def _refresh_changes(self) -> None:
        """Reload the version list for the selected file and redraw the diff."""
        if not hasattr(self, "changes_view"):
            return
        filename = self.changes_file_combo.currentText()
        try:
            refs = list_versions(self.project_path, filename)
        except (ContextError, OSError):
            refs = []
        self._changes_refs = refs
        labels = [ref.label for ref in refs]
        for combo, offset in ((self.changes_from_combo, 2), (self.changes_to_combo, 1)):
            combo.blockSignals(True); combo.clear(); combo.addItems(labels)
            if labels:
                combo.setCurrentIndex(max(0, len(labels) - offset))
            combo.blockSignals(False)
        if not refs:
            self.changes_summary.setText("这个文件还没有历史版本：保存一次，或运行 checkpoint 之后就会出现。")
            self.changes_view.clear(); self.changes_view.setExtraSelections([])
            self._changes_view_kinds = None
            return
        self._render_changes()

    def _render_changes(self) -> None:
        refs = getattr(self, "_changes_refs", [])
        if not refs:
            return
        from_index = self.changes_from_combo.currentIndex()
        to_index = self.changes_to_combo.currentIndex()
        if from_index < 0 or to_index < 0 or from_index >= len(refs) or to_index >= len(refs):
            return
        old_ref = refs[from_index]; new_ref = refs[to_index]
        old_text = read_version_text(old_ref)
        if self.changes_use_editor.isChecked() and new_ref.filename in self.editors:
            new_text = self.editors[new_ref.filename].toPlainText()
            new_label = "编辑器内容（未保存）"
        else:
            new_text = read_version_text(new_ref)
            new_label = new_ref.recorded_at
        view = build_diff_view(old_text, new_text)
        self.changes_view.setPlainText(view.text)
        self._changes_view_kinds = view.kinds
        self._apply_diff_highlights(self.changes_view, view.kinds)
        truncated = "（内容过长，已截断显示）" if view.truncated else ""
        self.changes_summary.setText(
            f"{new_ref.filename}  新增 {view.added} 行 / 删除 {view.removed} 行　"
            f"{old_ref.recorded_at} → {new_label}　该文件共 {len(refs)} 个历史版本{truncated}"
        )

    def _diff_colors(self) -> tuple[QColor, QColor]:
        palette = getattr(self, "_palette", {})
        return (QColor(palette.get("diff_add", "#E6F4EA")), QColor(palette.get("diff_del", "#FCE8E6")))

    def _apply_diff_highlights(self, widget: QPlainTextEdit, kinds: list[str]) -> None:
        add_color, del_color = self._diff_colors()
        selections: list = []
        document = widget.document()
        for index, kind in enumerate(kinds):
            if kind == "equal":
                continue
            block = document.findBlockByNumber(index)
            if not block.isValid():
                continue
            selection = QTextEdit.ExtraSelection()
            char_format = QTextCharFormat()
            char_format.setBackground(add_color if kind == "insert" else del_color)
            selection.format = char_format
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selection.cursor = cursor
            selections.append(selection)
        widget.setExtraSelections(selections)

    def _schedule_editor_marks(self) -> None:
        if hasattr(self, "_marks_timer"):
            self._marks_timer.start()

    def _apply_editor_marks(self, filename: str | None = None) -> None:
        """Green background for lines that were added since the last snapshot."""
        add_color, _ = self._diff_colors()
        names = [filename] if filename else list(self.editors)
        for name in names:
            editor = self.editors.get(name)
            if editor is None:
                continue
            path = self.file_paths.get(name)
            if not editor.document().isModified() or path is None or not path.exists():
                editor.setExtraSelections([])
                continue
            try:
                latest = latest_version(self.project_path, name)
            except (ContextError, OSError):
                latest = None
            if latest is None:
                editor.setExtraSelections([])
                continue
            numbers = new_line_numbers(read_version_text(latest), editor.toPlainText())
            selections: list = []
            document = editor.document()
            for number in numbers:
                block = document.findBlockByNumber(number - 1)
                if not block.isValid():
                    continue
                selection = QTextEdit.ExtraSelection()
                char_format = QTextCharFormat()
                char_format.setBackground(add_color)
                char_format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                selection.format = char_format
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                selection.cursor = cursor
                selections.append(selection)
            editor.setExtraSelections(selections)

    def _apply_diff_colors(self) -> None:
        """Re-paint diff backgrounds after a theme switch."""
        if self._changes_view_kinds is not None and hasattr(self, "changes_view"):
            self._apply_diff_highlights(self.changes_view, self._changes_view_kinds)
        self._apply_editor_marks()

    def _make_checkpoint_page(self) -> None:
        self.checkpoint_page = Page("Checkpoint", "保存一个可追溯的项目状态快照")
        card = self._card(); lay = QVBoxLayout(card); lay.setContentsMargins(28, 28, 28, 28); lay.setSpacing(12); h = QLabel("Save Project State"); h.setObjectName("cardTitle"); lay.addWidget(h); lay.addWidget(QLabel("创建检查点会保存当前状态、待办和 Git 信息，方便之后继续工作。")); self.checkpoint_result = QLabel("尚未创建检查点"); self.checkpoint_result.setObjectName("muted"); lay.addWidget(self.checkpoint_result); lay.addSpacing(8); b = QPushButton("创建 Checkpoint"); b.setObjectName("primary"); b.setMinimumWidth(154); b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed); b.setIcon(icon("checkpoint", "#FFFFFF")); b.clicked.connect(self._checkpoint); self.checkpoint_buttons.append(b); lay.addWidget(b, alignment=Qt.AlignLeft); self.checkpoint_page.layout.addWidget(card); self.checkpoint_page.layout.addStretch(); self.stack.addWidget(self.checkpoint_page)

    def _make_resume_page(self) -> None:
        self.resume_page = Page("Resume", "快速恢复项目，让下一次对话从正确上下文开始")
        row = QHBoxLayout(); self.resume_view = QPlainTextEdit(); self.resume_view.setReadOnly(True); self.resume_view.setPlaceholderText("打开一个已初始化的项目后，恢复上下文会显示在这里"); row.addWidget(self.resume_view, 1); self.resume_page.layout.addLayout(row, 1)
        actions = QHBoxLayout(); actions.addStretch(); copy = QPushButton("复制给 Agent"); copy.setObjectName("primary"); copy.setIcon(icon("copy", "#FFFFFF")); copy.clicked.connect(self._copy_resume); actions.addWidget(copy); refresh = QPushButton("重新生成"); refresh.setIcon(icon("refresh")); refresh.clicked.connect(self._resume); actions.addWidget(refresh); self.resume_page.layout.addLayout(actions); self.stack.addWidget(self.resume_page)

    def _make_doctor_page(self) -> None:
        self.doctor_page = Page("Doctor", "检查项目结构、编码和 Git 环境")
        self.doctor_list = QListWidget(); self.doctor_page.layout.addWidget(self.doctor_list, 1)
        row = QHBoxLayout()
        run = QPushButton("运行健康检查"); run.setIcon(icon("doctor")); run.clicked.connect(self._doctor); row.addWidget(run)
        repair = QPushButton("修复 STATE.md 结构"); repair.setIcon(icon("check")); repair.setToolTip("补齐缺失章节并按协议重排；同名章节会合并，不会丢失内容"); repair.clicked.connect(self._repair_context); row.addWidget(repair)
        row.addStretch()
        self.doctor_page.layout.addLayout(row); self.stack.addWidget(self.doctor_page)

    def _make_settings_page(self) -> None:
        self.settings_page = Page("Settings", "保持简洁，只保留影响工作流的设置")
        card = self._card(); lay = QVBoxLayout(card); lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(14); title = QLabel("Appearance"); title.setObjectName("cardTitle"); lay.addWidget(title); self.theme_group = QButtonGroup(self)
        for mode, text in [("system", "跟随系统"), ("light", "浅色"), ("dark", "深色")]:
            radio = QRadioButton(text); radio.setProperty("themeMode", mode); self.theme_group.addButton(radio); radio.toggled.connect(self._theme_changed); lay.addWidget(radio); 
            if mode == "system": radio.setChecked(True)
        export_card = self._card()
        el = QVBoxLayout(export_card)
        el.setContentsMargins(20, 16, 20, 16)
        el.setSpacing(8)
        et = QLabel("数据迁移")
        et.setObjectName("cardTitle")
        el.addWidget(et)
        edesc = QLabel("导出当前项目的 .agent 上下文档案为单个文件，可在新电脑上导入恢复。")
        edesc.setObjectName("pageSubtitle")
        edesc.setWordWrap(True)
        el.addWidget(edesc)
        erow = QHBoxLayout()
        eb = QPushButton("导出项目")
        eb.setIcon(icon("save"))
        eb.clicked.connect(self._export_project)
        erow.addWidget(eb)
        ib = QPushButton("导入项目")
        ib.setIcon(icon("folder"))
        ib.clicked.connect(self._import_project)
        erow.addWidget(ib)
        erow.addStretch()
        el.addLayout(erow)
        self.settings_page.layout.addWidget(export_card)
        self.settings_page.layout.addStretch(); self.stack.addWidget(self.settings_page)

    def _card(self) -> QFrame:
        frame = QFrame(); frame.setObjectName("card"); frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred); return frame

    def _usage_card(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)
        title = QLabel("使用方法")
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        steps = [
            ("1", "打开项目目录", "选择你正在开发的项目根目录。每个项目都会使用自己的 .agent 文件夹。"),
            ("2", "首次使用先初始化", "初始化只创建上下文模板，不会清空聊天记录，也不会清空项目代码。"),
            ("3", "复制填充提示词", "把提示词发给当前 Agent，让它扫描原项目并只把结果写进 .agent 和 AGENTS.md。"),
            ("4", "阶段完成点保存进度", "它会保存已编辑的 Markdown，并在后台创建 checkpoint，窗口不会卡住。"),
            ("5", "新对话点复制给 Agent", "把复制出来的恢复指令发给新 Agent，它就会按当前项目上下文继续。"),
        ]
        for number, heading, body in steps:
            row = QHBoxLayout()
            row.setSpacing(12)
            badge = QLabel(number)
            badge.setObjectName("guideNumber")
            badge.setFixedSize(26, 26)
            badge.setAlignment(Qt.AlignCenter)
            row.addWidget(badge, alignment=Qt.AlignTop)
            text = QLabel(f"<b>{heading}</b><br>{body}")
            text.setObjectName("guideText")
            text.setWordWrap(True)
            row.addWidget(text, 1)
            layout.addLayout(row)
        return card

    def _navigate_by_key(self, key: str) -> None:
        keys = [x[0] for x in NAV] + ["checkpoint", "resume", "doctor", "settings"]; self._navigate(keys.index(key))

    def _navigate(self, index: int) -> None:
        # Keep the sidebar highlight in sync when navigation happens in code (the Overview
        # "打开 STATE.md" card button, _resume_page_focus). A real click sets the checked
        # state itself; a programmatic jump used to leave the highlight on the old entry.
        if 0 <= index < len(self.nav_buttons) and not self.nav_buttons[index].isChecked():
            self.nav_buttons[index].setChecked(True)
        if index < len(NAV):
            key, filename, _ = NAV[index]
            if key == "overview":
                widget = self.overview
            elif key == "changes":
                widget = self.changes_page
            else:
                widget = self.doc_pages[filename]
            self.stack.setCurrentWidget(widget)
            if key == "changes":
                self._refresh_changes()
        else:
            self.stack.setCurrentIndex(index - len(NAV) + 1 + len(EDITABLE_FILES))

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("文件"); a = QAction("打开项目", self); a.setShortcut(QKeySequence("Ctrl+O")); a.triggered.connect(self._browse_project); menu.addAction(a); a = QAction("保存当前文件", self); a.setShortcut(QKeySequence("Ctrl+S")); a.triggered.connect(self._save_current); menu.addAction(a); a = QAction("复制填充提示词", self); a.setShortcut(QKeySequence("Ctrl+Shift+I")); a.triggered.connect(self._copy_bootstrap_prompt); menu.addAction(a); a = QAction("复制恢复指令", self); a.setShortcut(QKeySequence("Ctrl+Shift+R")); a.triggered.connect(self._copy_resume); menu.addAction(a); menu.addSeparator(); a = QAction("退出", self); a.triggered.connect(self.close); menu.addAction(a)

    # The base font is set in pt, not px. A px size made Qt call setPointSize(-1) while
    # parsing the stylesheet and printed "QFont::setPointSize: Point size <= 0" on every
    # launch (verified: moving this one rule to pt removes the warning, rendering is
    # unchanged).
    def _apply_theme(self) -> None:
        dark = self.theme_mode == "dark" or (self.theme_mode == "system" and self.palette().window().color().lightness() < 128)
        c = {"bg": "#1C1C1E" if dark else "#F5F5F7", "side": "#2C2C2E" if dark else "#F2F2F7", "card": "#2C2C2E" if dark else "#FFFFFF", "text": "#F5F5F7" if dark else "#1D1D1F", "muted": "#98989D" if dark else "#6E6E73", "line": "#48484A" if dark else "#D2D2D7", "accent": "#5B9EF4" if dark else "#2775D3", "scroll": "rgba(255,255,255,0.24)" if dark else "rgba(0,0,0,0.22)", "scroll_hover": "rgba(255,255,255,0.38)" if dark else "rgba(0,0,0,0.35)", "accent_soft": "rgba(91,158,244,0.20)" if dark else "rgba(39,117,211,0.10)", "diff_add": "#1E3A2B" if dark else "#E6F4EA", "diff_del": "#4A1F1F" if dark else "#FCE8E6"}
        self.setStyleSheet(f"""
        QMainWindow, QWidget {{ background:{c['bg']}; color:{c['text']}; font-family:'Segoe UI'; font-size:10pt; }}
        QMenuBar, QStatusBar {{ background:{c['bg']}; color:{c['text']}; border:0; }} QMenuBar::item:selected {{ background:{c['side']}; }}
        QFrame#sidebar {{ background:{c['side']}; border-right:1px solid {c['line']}; }} QFrame#topbar {{ background:{c['bg']}; border-bottom:1px solid {c['line']}; }}
        QLabel#brandMark {{ background:transparent; padding:0; }} QLabel#brandName {{ font-weight:650; font-size:14px; }} QLabel#eyebrow {{ color:{c['muted']}; font-size:10px; font-weight:700; }} QLabel#sidebarProject, QLabel#pageSubtitle, QLabel#muted {{ color:{c['muted']}; }}
        QToolButton#navButton {{ text-align:left; border:0; border-radius:8px; padding:9px 10px; color:{c['muted']}; }} QToolButton#navButton:hover {{ background:{c['line']}; color:{c['text']}; }} QToolButton#navButton:checked {{ background:{c['card']}; color:{c['accent']}; font-weight:600; }}
        QLabel#pageTitle {{ font-size:28px; font-weight:650; }} QLabel#cardTitle {{ font-size:16px; font-weight:650; }}
        QLabel#guideNumber {{ background:{c['accent']}; color:white; border-radius:13px; font-size:12px; font-weight:700; }}
        QLabel#guideText {{ color:{c['text']}; line-height:135%; }}
        QLabel#agentBanner {{ background:{c['accent_soft']}; color:{c['text']}; border-radius:8px; padding:7px 10px; font-weight:600; }}
        QToolButton#bannerClose {{ border:0; background:transparent; color:{c['muted']}; font-size:15px; padding:2px 8px; }}
        QToolButton#bannerClose:hover {{ color:{c['text']}; }}
        QScrollArea#overviewScroll {{ background:transparent; border:0; }}
        QFrame#card QScrollArea {{ background:transparent; border:0; }}
        QFrame#card {{ background:{c['card']}; border:1px solid {c['line']}; border-radius:12px; }} QLineEdit, QPlainTextEdit, QListWidget {{ background:{c['card']}; color:{c['text']}; border:1px solid {c['line']}; border-radius:8px; padding:8px; }}
        QComboBox {{ background:{c['card']}; color:{c['text']}; border:1px solid {c['line']}; border-radius:8px; padding:8px 32px 8px 12px; min-height:18px; }}
        QComboBox:hover {{ border-color:{c['accent']}; }}
        QComboBox::drop-down {{ border:0; width:28px; }}
        QComboBox::down-arrow {{ image:none; border-left:4px solid transparent; border-right:4px solid transparent; border-top:5px solid {c['muted']}; margin-right:10px; }}
        QPushButton {{ background:{c['card']}; color:{c['text']}; border:1px solid {c['line']}; border-radius:8px; padding:8px 14px; min-height:18px; }} QPushButton:hover {{ border-color:{c['accent']}; }} QPushButton#primary {{ background:{c['accent']}; color:white; border:0; }} QPushButton#primary:disabled {{ background:{c['accent']}; color:white; }}
        QRadioButton {{ spacing:8px; padding:4px; }} QListWidget::item {{ padding:10px; border-bottom:1px solid {c['line']}; }}
        QScrollBar:vertical {{ background:transparent; width:9px; margin:2px; border-radius:4px; }}
        QScrollBar::handle:vertical {{ background:{c['scroll']}; min-height:32px; border-radius:3px; }}
        QScrollBar::handle:vertical:hover {{ background:{c['scroll_hover']}; }}
        QScrollBar::handle:vertical:pressed {{ background:{c['accent']}; }}
        QScrollBar:horizontal {{ background:transparent; height:9px; margin:2px; border-radius:4px; }}
        QScrollBar::handle:horizontal {{ background:{c['scroll']}; min-width:32px; border-radius:3px; }}
        QScrollBar::handle:horizontal:hover {{ background:{c['scroll_hover']}; }}
        QScrollBar::handle:horizontal:pressed {{ background:{c['accent']}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background:transparent; }}

        """)
        self._palette = c
        self._apply_diff_colors()

    def _browse_project(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择项目目录", str(self.project_path))
        if selected: self.path_edit.setText(selected); self._open_project()

    def _open_project(self) -> None:
        raw = self.path_edit.text().strip()
        if not raw: self._show_error(ContextError("项目目录不能为空。")); return
        self._set_project_path(resolve_project_path(raw), persist=True)

    def _set_project_path(self, path: Path, persist: bool = True) -> None:
        requested_path = path
        discovered_path = find_initialized_project_path(path)
        if discovered_path is not None:
            path = discovered_path
        self.project_path = path
        self._watch_timer.stop()
        self._pending_external_changes = []
        self._project_load_message = ""
        if persist:
            self.settings.setValue("project_path", str(path)); self._remember_project(path); self.settings.sync()
        self.path_edit.setText(str(path)); self.project_name.setText(path.name or str(path)); self.file_paths = context_file_paths(path)
        if discovered_path is not None and discovered_path != requested_path:
            self._toast(f"已定位到项目根目录: {path}")
        if not path.exists() or not path.is_dir(): self.current_status = None; self._clear_views(); self._toast("项目目录不存在"); return
        if not (path / ".agent").is_dir():
            self.current_status = None
            self._project_load_message = "当前目录及其父目录都没有找到 .agent 文件夹。"
            self._clear_views()
            self._toast("未找到 .agent 文件夹，请确认选择的是项目目录")
            return
        try:
            self.current_status = get_status(path)
        except ContextError as exc:
            # Project is initialized but STATE.md may be missing required sections;
            # still load editors so the user can fix the file instead of seeing a false "not initialized" prompt.
            self.current_status = None
            self._project_load_message = f"已检测到 .agent，但 STATE.md 需要修复：{exc.reason or exc.message}"
            self._load_editors_only()
            self._toast(f"STATE.md 需要修复: {exc.reason or exc.message}")
            self._watch_timer.start()
            return
        self._refresh_context()
        self._watch_timer.start()

    def _export_project(self) -> None:
        try:
            output = export_project(self.project_path)
            QMessageBox.information(self, "导出成功", f"已导出到:\n{output}")
        except (ContextError, OSError) as exc:
            self._show_error(exc)

    def _import_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择导出文件", "", "Agent Context Transfer (*.agentctx.json)")
        if not path:
            return
        target = QFileDialog.getExistingDirectory(self, "选择目标项目目录")
        if not target:
            return
        try:
            from agent_context.transfer import import_project
            report = import_project(Path(path), Path(target))
            lines = [f"已导入到:\n{target}", "", f"新增 {len(report.created)} 项，覆盖 {len(report.overwritten)} 项，未变化 {len(report.unchanged)} 项"]
            if report.kept:
                lines.append("保留原有文件（未被导入覆盖）：" + "、".join(report.kept))
            if report.backup_dir is not None:
                lines.append(f"被覆盖的旧文件已备份到：{report.backup_dir}")
            QMessageBox.information(self, "导入成功", "\n".join(lines))
        except (ContextError, OSError) as exc:
            self._show_error(exc)

    def _refresh_recent_projects(self) -> None:
        paths = self.settings.value("recent_projects", [], type=list) or []
        current = str(self.project_path)
        ordered = [current] + [str(item) for item in paths if str(item) != current]
        self.recent_combo.blockSignals(True); self.recent_combo.clear()
        self.recent_combo.addItem("最近项目", "")
        for item in ordered[:8]: self.recent_combo.addItem(Path(item).name or item, item)
        self.recent_combo.setCurrentIndex(0); self.recent_combo.blockSignals(False)

    def _remember_project(self, path: Path) -> None:
        current = str(path); paths = self.settings.value("recent_projects", [], type=list) or []
        ordered = [current] + [str(item) for item in paths if str(item) != current]
        self.settings.setValue("recent_projects", ordered[:8]); self._refresh_recent_projects()

    def _recent_project_selected(self, index: int) -> None:
        if index <= 0: return
        raw = self.recent_combo.itemData(index)
        if raw: self.path_edit.setText(str(raw)); self._open_project()

    def _snapshot_file_mtimes(self) -> None:
        self._file_mtimes = {}
        for filename, path in self.file_paths.items():
            try:
                self._file_mtimes[filename] = path.stat().st_mtime
            except OSError:
                self._file_mtimes[filename] = 0

    def _detect_external_changes(self) -> list[str]:
        changed = []
        for filename, path in self.file_paths.items():
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if filename in self._file_mtimes and mtime != self._file_mtimes[filename]:
                changed.append(filename)
        return changed

    def _latest_activity(self) -> tuple[str, float]:
        best_name, best_mtime = "", 0.0
        for filename, path in self.file_paths.items():
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > best_mtime:
                best_name, best_mtime = filename, mtime
        return best_name, best_mtime

    def _watch_check(self) -> None:
        if not (self.project_path / ".agent").is_dir() or not hasattr(self, "_file_mtimes"):
            return
        if self.checkpoint_thread is not None:
            return
        changed = self._detect_external_changes()
        if not changed:
            return
        self._pending_external_changes = list(dict.fromkeys(changed))
        try:
            self.current_status = get_status(self.project_path)
        except Exception:
            self.current_status = None
        has_unsaved = any(editor.document().isModified() for editor in self.editors.values())
        if not has_unsaved:
            # Snapshot what the agent replaced, then the new content: the diff between
            # those two versions is exactly what changed outside this window.
            for filename, editor in self.editors.items():
                record_version(self.project_path, filename, text=editor.toPlainText(), source="external")
            for filename, editor in self.editors.items():
                editor.setEnabled(True)
                editor.setPlainText(read_utf8(self.file_paths[filename]))
                editor.document().setModified(False)
                record_version(self.project_path, filename, source="external")
            try:
                self._current_token_stats = context_token_stats(self.project_path)
            except Exception:
                pass
            self._snapshot_file_mtimes()
            self._resume()
        self._update_overview()
        suffix = "" if has_unsaved else "，内容已自动刷新"
        self.statusBar().showMessage(f"Agent updated: {chr(0x3001).join(self._pending_external_changes)}{suffix}")

    def _dismiss_external_changes(self) -> None:
        self._pending_external_changes = []
        self._update_overview()

    def _apply_pending_external_changes(self) -> None:
        self._pending_external_changes = []
        self._refresh_context()

    def _refresh_context(self) -> None:
        try:
            external_changed = self._detect_external_changes() if hasattr(self, "_file_mtimes") else []
            # Re-read status so a previously failed load (status=None with a stale
            # error message) recovers once the .agent folder is usable, e.g. right
            # after the user initializes the project.
            if (self.project_path / ".agent").is_dir():
                try:
                    self.current_status = get_status(self.project_path)
                    self._project_load_message = ""
                except ContextError as exc:
                    self.current_status = None
                    self._project_load_message = f"已检测到 .agent，但 STATE.md 需要修复：{exc.reason or exc.message}"
            try:
                self._current_token_stats = context_token_stats(self.project_path)
                pass
            except Exception:
                pass
            # Never overwrite unsaved edits. Reloading every editor unconditionally
            # used to silently discard whatever the user had typed but not saved
            # (verified: text was replaced and the modified flag cleared).
            skipped: list[str] = []
            for filename, editor in self.editors.items():
                if editor.document().isModified():
                    skipped.append(filename)
                    continue
                editor.setEnabled(True)
                editor.setPlainText(read_utf8(self.file_paths[filename]))
                editor.document().setModified(False)
            self._snapshot_file_mtimes()
            self._update_overview(); self._refresh_archives(); self._resume(); self._refresh_changes()
            if skipped:
                names = "、".join(skipped)
                self._toast(f"已保留未保存的修改，未从磁盘重载: {names}")
            elif external_changed:
                names = ", ".join(external_changed)
                self._toast(f"检测到外部更新: {names}")
            else:
                self._toast("项目已加载")
        except (ContextError, OSError) as exc: self._show_error(exc)

    def _load_editors_only(self) -> None:
        """Load file contents into editors without requiring a full status snapshot."""
        for filename, editor in self.editors.items():
            try:
                editor.setEnabled(True)
                editor.setPlainText(read_utf8(self.file_paths[filename]))
                editor.document().setModified(False)
            except (ContextError, OSError):
                editor.clear(); editor.setEnabled(False)
        self._snapshot_file_mtimes()
        self._update_overview()
        self._refresh_changes()
        self.resume_view.clear()

    def _clear_views(self) -> None:
        for editor in self.editors.values(): editor.clear(); editor.setEnabled(False)
        self._watch_timer.stop()
        # The overview layout is emptied, so drop the cache key first: an unchanged
        # project would otherwise skip the rebuild and leave the page blank.
        self._overview_key_cache = None
        self._recent_changes = []
        self._changes_view_kinds = None
        if hasattr(self, "changes_view"):
            self.changes_view.clear(); self.changes_view.setExtraSelections([])
            self.changes_summary.setText("")
        self.resume_view.clear(); self.doctor_list.clear(); self._update_overview()

    def _clear_overview_layout(self) -> None:
        """Remove old overview widgets before rebuilding the page after a refresh."""
        while self.overview_grid.count():
            item = self.overview_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout is not None:
                while child_layout.count():
                    child_item = child_layout.takeAt(0)
                    child_widget = child_item.widget()
                    if child_widget is not None:
                        child_widget.hide()
                        child_widget.setParent(None)
                        child_widget.deleteLater()
                child_layout.deleteLater()

    def _recent_change_summary(self) -> list[tuple]:
        try:
            self._recent_changes = recent_changes(self.project_path)
        except (ContextError, OSError):
            self._recent_changes = []
        return [(c.filename, c.added, c.removed, c.at, c.versions) for c in self._recent_changes]

    def _overview_key(self) -> tuple:
        """Everything _update_overview renders; an unchanged key means no rebuild."""
        status = self.current_status
        stats = getattr(self, "_current_token_stats", None)
        return (
            str(self.project_path), self.theme_mode, tuple(self._pending_external_changes),
            self._project_load_message,
            None if status is None else (
                status.phase, status.task, status.p0_count, status.p1_count, status.p2_count,
                status.git_info.repository_detected, status.last_checkpoint,
                status.context_files.get("STATE.md"),
            ),
            None if stats is None else (
                stats.total_chars, len(stats.files), stats.archive_files, stats.archive_chars,
            ),
            self._latest_activity(),
            tuple(self._recent_change_summary()),
        )

    def _update_overview(self, force: bool = False) -> None:
        key = self._overview_key()
        if not force and key == self._overview_key_cache:
            return
        self._overview_key_cache = key
        self._clear_overview_layout()
        self.checkpoint_buttons = []
        status = self.current_status
        if not status:
            initialized = (self.project_path / ".agent").is_dir()
            empty = self._card()
            l = QVBoxLayout(empty)
            l.setContentsMargins(24, 24, 24, 24)
            h = QLabel("项目已加载" if initialized else "还没有打开项目")
            h.setObjectName("cardTitle")
            l.addWidget(h)
            if initialized:
                intro_text = self._project_load_message or "已检测到 .agent 文件夹，但项目状态暂时无法读取。"
                intro = QLabel(intro_text)
                intro.setWordWrap(True)
                l.addWidget(intro)
                path_label = QLabel(f"项目目录  {self.project_path}")
                path_label.setObjectName("pageSubtitle")
                path_label.setWordWrap(True)
                l.addWidget(path_label)
                empty_actions = QHBoxLayout()
                state_button = QPushButton("打开 STATE.md")
                state_button.setIcon(icon("arrow"))
                state_button.clicked.connect(lambda: self._navigate_by_key("state"))
                empty_actions.addWidget(state_button)
                repair_button = QPushButton("修复 STATE.md 结构")
                repair_button.setIcon(icon("doctor"))
                repair_button.setToolTip("补齐缺失章节并按协议重排；同名章节会合并，不会丢失内容")
                repair_button.clicked.connect(self._repair_context)
                empty_actions.addWidget(repair_button)
                refresh_button = QPushButton("重新读取")
                refresh_button.setIcon(icon("refresh"))
                refresh_button.clicked.connect(self._refresh_context)
                empty_actions.addWidget(refresh_button)
                empty_actions.addStretch()
                l.addLayout(empty_actions)
            else:
                intro = QLabel("选择一个项目目录，或先初始化项目后再复制填充提示词，让 Agent 把原项目资料写入上下文档案。")
                intro.setWordWrap(True)
                l.addWidget(intro)
                empty_actions = QHBoxLayout()
                b = QPushButton("初始化项目")
                b.setIcon(icon("folder"))
                b.clicked.connect(self._init_project)
                empty_actions.addWidget(b)
                bp = QPushButton("复制填充提示词")
                bp.setIcon(icon("copy"))
                bp.setToolTip("复制让 Agent 扫描项目并填充 .agent 文件的提示词")
                bp.clicked.connect(self._copy_bootstrap_prompt)
                empty_actions.addWidget(bp)
                empty_actions.addStretch()
                l.addLayout(empty_actions)
            self.overview_grid.addWidget(empty)
            self.overview_grid.addWidget(self._usage_card())
            self.overview_grid.addStretch()
            return
        hero = self._card()
        hero_outer = QVBoxLayout(hero)
        hero_outer.setContentsMargins(0,0,0,0)
        if self._pending_external_changes:
            names = "、".join(dict.fromkeys(self._pending_external_changes))
            banner_row = QHBoxLayout()
            banner_row.setContentsMargins(12,12,12,0)
            banner_row.setSpacing(6)
            banner = QLabel(f"⟳ Agent 更新了 {names}")
            banner.setObjectName("agentBanner")
            refresh_btn = QPushButton("刷新")
            refresh_btn.setIcon(icon("refresh"))
            refresh_btn.setToolTip("重新读取被 Agent 更新的上下文文件")
            refresh_btn.clicked.connect(self._apply_pending_external_changes)
            close_btn = QToolButton()
            close_btn.setText("×")
            close_btn.setObjectName("bannerClose")
            close_btn.setToolTip("忽略本次更新提醒")
            close_btn.clicked.connect(self._dismiss_external_changes)
            banner_row.addWidget(banner, 1)
            banner_row.addWidget(refresh_btn)
            banner_row.addWidget(close_btn)
            hero_outer.addLayout(banner_row)
        hero_scroll = QScrollArea()
        hero_scroll.setWidgetResizable(True)
        hero_scroll.setFrameShape(QFrame.NoFrame)
        hero_scroll.setMaximumHeight(160); hero_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); hero_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded); hero_scroll.viewport().setStyleSheet("background:transparent;")
        hero_content = QWidget()
        hl = QVBoxLayout(hero_content)
        hl.setContentsMargins(20,16,20,16)
        hero_content.setMinimumWidth(600)
        hh = QLabel(status.project_path.name)
        hh.setObjectName("cardTitle")
        hl.addWidget(hh)
        hl.addWidget(QLabel(f"当前阶段  {status.phase}"))
        task = QLabel(f"当前任务  {status.task}")
        task.setObjectName("pageSubtitle")
        task.setWordWrap(True)
        hl.addWidget(task)
        latest_name, latest_mtime = self._latest_activity()
        latest_text = f"最近更新  {latest_name} · {relative_time(latest_mtime)}" if latest_name else "最近更新  暂无活动记录"
        latest_label = QLabel(latest_text)
        latest_label.setObjectName("pageSubtitle")
        hl.addWidget(latest_label)
        hl.addStretch()
        hero_scroll.setWidget(hero_content)
        hero_outer.addWidget(hero_scroll)
        self.overview_grid.addWidget(hero)
        self.overview_grid.addWidget(self._usage_card())

        stats = QHBoxLayout()
        for title, value in [("待办 P0", status.p0_count), ("待办 P1", status.p1_count), ("待办 P2", status.p2_count), ("Git", "已连接" if status.git_info.repository_detected else "未连接")]:
            card = self._card(); cl = QVBoxLayout(card); cl.setContentsMargins(14,12,14,12); cl.addWidget(QLabel(title)); v = QLabel(str(value)); v.setObjectName("cardTitle"); cl.addWidget(v); stats.addWidget(card)
        activity_name, activity_mtime = self._latest_activity()
        activity_card = self._card()
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(14,12,14,12)
        activity_layout.addWidget(QLabel("最后活动"))
        activity_value = QLabel(relative_time(activity_mtime) if activity_name else "—")
        activity_value.setObjectName("cardTitle")
        file_times = {}
        for filename, path in self.file_paths.items():
            try:
                file_times[filename] = path.stat().st_mtime
            except OSError:
                continue
        if file_times:
            activity_value.setToolTip("\n".join(
                f"{name} · {relative_time(mtime)}"
                for name, mtime in sorted(file_times.items(), key=lambda item: item[1], reverse=True)
            ))
        activity_layout.addWidget(activity_value)
        stats.addWidget(activity_card)
        self.overview_grid.addLayout(stats)
        changes = getattr(self, "_recent_changes", [])
        if changes:
            change_card = self._card()
            change_layout = QVBoxLayout(change_card)
            change_layout.setContentsMargins(16, 14, 16, 14)
            change_layout.setSpacing(6)
            change_title = QLabel("最近变更")
            change_title.setObjectName("cardTitle")
            change_layout.addWidget(change_title)
            rows = []
            for change in changes:
                if change.versions == 0:
                    rows.append(f"{change.filename}    暂无历史版本")
                elif change.added or change.removed:
                    rows.append(f"{change.filename}    +{change.added} 行 / -{change.removed} 行    {change.at}")
                else:
                    rows.append(f"{change.filename}    无变化    {change.at}")
            change_body = QLabel("\n".join(rows))
            change_body.setObjectName("pageSubtitle")
            change_body.setWordWrap(True)
            change_layout.addWidget(change_body)
            change_row = QHBoxLayout()
            change_btn = QPushButton("查看变更")
            change_btn.setIcon(icon("arrow"))
            change_btn.setToolTip("打开 Changes 页查看每一行的新增与删除")
            change_btn.clicked.connect(lambda: self._navigate_by_key("changes"))
            change_row.addWidget(change_btn); change_row.addStretch()
            change_layout.addLayout(change_row)
            self.overview_grid.addWidget(change_card)
        if hasattr(self, "_current_token_stats"):
            ts = self._current_token_stats
            tok = self._card()
            tl = QVBoxLayout(tok)
            tl.setContentsMargins(14,12,14,12)
            archive_note = f"  |  archive {ts.archive_files} 个文件 / {ts.archive_chars:,} chars（resume 不读取）" if ts.archive_files else ""
            t1 = QLabel(f"上下文档案  {ts.estimated_tokens:,} tokens / {ts.total_chars:,} chars / {len(ts.files)} files{archive_note}")
            t1.setObjectName("pageSubtitle")
            t1.setWordWrap(True)
            tl.addWidget(t1)
            self.overview_grid.addWidget(tok); actions = QHBoxLayout(); actions.setSpacing(12); bp = QPushButton("复制填充提示词"); bp.setMinimumWidth(146); bp.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed); bp.setIcon(icon("copy")); bp.setToolTip("复制让当前 Agent 扫描项目并填充上下文文件的提示词"); bp.clicked.connect(self._copy_bootstrap_prompt); actions.addWidget(bp); cp = QPushButton("保存进度"); cp.setObjectName("primary"); cp.setMinimumWidth(132); cp.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed); cp.setIcon(icon("checkpoint", "#FFFFFF")); cp.setToolTip("保存所有上下文文件并创建 Checkpoint"); cp.clicked.connect(self._checkpoint); self.checkpoint_buttons.append(cp); actions.addWidget(cp); rs = QPushButton("复制给 Agent"); rs.setMinimumWidth(128); rs.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed); rs.setIcon(icon("copy")); rs.setToolTip("复制可直接发给新 Agent 的恢复指令"); rs.clicked.connect(self._copy_resume); actions.addWidget(rs); actions.addStretch(); self.overview_grid.addLayout(actions); self.overview_grid.addStretch()

    def _resume_page_focus(self) -> None: self._navigate_by_key("resume")
    def _save_current(self) -> None:
        widget = self.stack.currentWidget(); filename = next((n for n,p in self.doc_pages.items() if p is widget), None)
        if not filename: return
        editor = self.editors[filename]
        try:
            write_utf8(self.file_paths[filename], editor.toPlainText())
            editor.document().setModified(False)
            record_version(self.project_path, filename, source="save")
            self._snapshot_file_mtimes()
            self._apply_editor_marks(filename); self._refresh_changes(); self._update_overview(force=True)
            self._toast(f"已保存 {filename}")
        except (ContextError, OSError) as exc: self._show_error(exc)

    def _save_all_context(self) -> None:
        saved: list[str] = []
        for filename, editor in self.editors.items():
            if editor.document().isModified():
                write_utf8(self.file_paths[filename], editor.toPlainText())
                editor.document().setModified(False)
                record_version(self.project_path, filename, source="save")
                saved.append(filename)
        self._snapshot_file_mtimes()
        if saved:
            self._apply_editor_marks(); self._refresh_changes(); self._update_overview(force=True)

    def _init_project(self) -> None:
        try:
            result = init_project(self.project_path)
            # init succeeded, so any "no .agent folder" / "STATE.md needs repair"
            # message from an earlier failed load is now stale; drop it and let
            # _refresh_context() rebuild both the editors and the overview.
            self._project_load_message = ""
            self.current_status = get_status(self.project_path)
            self.file_paths = context_file_paths(self.project_path)
            self._refresh_context()
            QMessageBox.information(self, "初始化完成", f"已创建 {len(result.created)} 项文件或目录。")
        except (ContextError, OSError) as exc: self._show_error(exc)

    def _checkpoint(self) -> None:
        if self.checkpoint_thread is not None: return
        try: self._save_all_context()
        except (ContextError, OSError) as exc: self._show_error(exc); return
        self._set_checkpoint_busy(True); self._toast("正在保存进度，界面仍可操作")
        self.checkpoint_thread = QThread(self); self.checkpoint_worker = CheckpointWorker(self.project_path)
        self.checkpoint_worker.moveToThread(self.checkpoint_thread); self.checkpoint_thread.started.connect(self.checkpoint_worker.run)
        self.checkpoint_worker.finished.connect(self._checkpoint_finished); self.checkpoint_worker.failed.connect(self._checkpoint_failed)
        self.checkpoint_worker.finished.connect(self.checkpoint_thread.quit); self.checkpoint_worker.failed.connect(self.checkpoint_thread.quit)
        self.checkpoint_thread.finished.connect(self._checkpoint_thread_finished); self.checkpoint_thread.start()

    def _set_checkpoint_busy(self, busy: bool) -> None:
        for button in self.findChildren(QPushButton):
            if button.text().startswith(("创建 Checkpoint", "保存进度", "正在创建", "正在保存")):
                button.setEnabled(not busy); button.setText("正在保存..." if busy else ("保存进度" if button.minimumWidth() <= 140 else "创建 Checkpoint"))

    @Slot(object)
    def _checkpoint_finished(self, summary: object) -> None:
        self._pending_external_changes = []
        archive_path = getattr(summary, "archive_path", None)
        label = f"已保存  {archive_path.name}" if archive_path is not None else "已保存（配置关闭了 archive_enabled，未写归档）"
        self._refresh_context(); self.checkpoint_result.setText(label); self._toast("Checkpoint 已保存")

    @Slot(object)
    def _checkpoint_failed(self, error: object) -> None:
        self._show_error(error)

    def _checkpoint_thread_finished(self) -> None:
        if self.checkpoint_worker is not None: self.checkpoint_worker.deleteLater()
        if self.checkpoint_thread is not None: self.checkpoint_thread.deleteLater()
        self.checkpoint_worker = None; self.checkpoint_thread = None; self._set_checkpoint_busy(False)

    def _resume(self) -> None:
        try: self.resume_view.setPlainText(build_agent_prompt(self.project_path))
        except (ContextError, OSError): self.resume_view.clear()
    def _copy_resume(self) -> None:
        if self.resume_view.toPlainText(): QApplication.clipboard().setText(self.resume_view.toPlainText()); self._toast("恢复上下文已复制")

    def _copy_bootstrap_prompt(self) -> None:
        QApplication.clipboard().setText(build_context_bootstrap_prompt(self.project_path))
        self._toast("填充提示词已复制")

    def _repair_context(self) -> None:
        """Rewrite STATE.md/TODO.md into the protocol structure without losing content."""
        try:
            report = repair_project(self.project_path)
        except (ContextError, OSError) as exc:
            self._show_error(exc); return
        details: list[str] = []
        if report.state_missing_required:
            details.append("缺失必需章节：" + "、".join(report.state_missing_required))
        if report.state_missing_optional:
            details.append("缺失可选章节：" + "、".join(report.state_missing_optional))
        if report.state_duplicate_sections:
            details.append("重复章节（已合并保留全部内容）：" + "、".join(report.state_duplicate_sections))
        if report.todo_heading_added:
            details.append("TODO.md 已补回 `# TODO` 标题")
        if report.state_changed:
            details.append("STATE.md 已按协议章节顺序重写")
        self._refresh_context(); self._doctor()
        if details:
            self._toast("结构修复完成")
            QMessageBox.information(self, "结构修复完成", "\n".join(details))
        else:
            self._toast("无需修复，两个文件都已符合协议")

    def _doctor(self) -> None:
        self.doctor_list.clear()
        try:
            for check in run_doctor(self.project_path):
                item = QListWidgetItem(("✓  " if check.ok else "!  ") + f"{check.name}   {check.detail}"); item.setIcon(icon("check" if check.ok else "warning")); self.doctor_list.addItem(item)
        except (ContextError, OSError) as exc: self._show_error(exc)

    def _refresh_archives(self) -> None:
        self.archive_items = []
        try: self.archive_items = list_archives(self.project_path)
        except (ContextError, OSError): pass
    def _update_dirty_label(self) -> None:
        for editor in self.editors.values(): editor.dirty_label.setText("未保存修改" if editor.document().isModified() else "")
    def _open_in_editor(self, filename: str) -> None:
        """Open a context file with the configured editor, or the OS default."""
        path = self.file_paths.get(filename)
        if path is None or not path.exists():
            self._toast(f"{filename} 还没有保存到磁盘")
            return
        editor = load_config().get("default_editor")
        try:
            if editor:
                subprocess.Popen([str(editor), str(path)])
            elif hasattr(os, "startfile"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            self._show_error(exc)

    def _theme_changed(self, checked: bool) -> None:
        if checked:
            self.theme_mode = self.sender().property("themeMode"); self._apply_theme(); self._update_overview(force=True)
    def _toast(self, message: str) -> None:
        self.statusBar().showMessage(message); QTimer.singleShot(3200, lambda: self.statusBar().clearMessage())
    def _show_error(self, error: Exception) -> None:
        details = error.message if isinstance(error, ContextError) else str(error)
        if isinstance(error, ContextError) and error.reason: details += f"\n\n原因：{error.reason}"
        QMessageBox.critical(self, "操作失败", details)


def _register_system_fonts() -> None:
    # On Windows builds older than 10 1903, Qt's DirectWrite/GDI font backend
    # can fail to enumerate system fonts (every glyph renders as a tofu box).
    # Manually registering the font files works around that; addApplicationFont
    # returns -1 per file on failure, so this degrades to a no-op elsewhere.
    from PySide6.QtGui import QFontDatabase
    font_dirs = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
    for font_dir in font_dirs:
        if not font_dir.is_dir():
            continue
        for pattern in ("*.ttf", "*.ttc", "*.otf"):
            for font_path in font_dir.glob(pattern):
                QFontDatabase.addApplicationFont(str(font_path))


def main() -> None:
    set_windows_app_id(); app = QApplication(sys.argv); app.setApplicationName("Agent Context Manager"); app.setOrganizationName("Agent Context Manager"); app.setWindowIcon(app_icon())
    _register_system_fonts()
    # The native "windowsvista" style renders half-broken on pre-1903 systems
    # (classic-looking comboboxes, flat pushbuttons); Fusion is drawn by Qt
    # itself and looks the same everywhere.
    from PySide6.QtWidgets import QStyleFactory
    app.setStyle(QStyleFactory.create("Fusion"))
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None); window.show(); raise SystemExit(app.exec())


if __name__ == "__main__": main()
