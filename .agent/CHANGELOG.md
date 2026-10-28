# CHANGELOG

面向发布的历史见仓库根目录的 `CHANGELOG.md`（英文，按 Keep a Changelog + SemVer）。这里记录与「上下文档案」相关的要点与重大转折，便于接手者快速对齐。

## 2026-10-28（0.9.0 提交/推送 + 档案刷新）

### Added

- v0.9.0：可配置 handoff prompt（`agent_prompt_template`，支持 `{project}` / `{resume}`；Settings 可编辑）；combobox 下拉主题跟随应用主题。

### Fixed

- 0.8.1 的侧栏导航 off-by-one 与 Changes 控制行重叠修复随 0.9.0 一并提交；回归测试 `tests/test_gui_pages.py`。

### Released

- 提交 `4ba0200` `feat: add configurable handoff prompt and ship 0.9.0`（17 文件，+544/−60），推送到 `origin/main`；远端 sha 与本地 HEAD 一致。
- 本地 onedir 包：`D:\vibe code\Agent Context Manager\Agent Context Manager v0.9.0\`（2026-10-27）。

### Context

- `.agent/STATE.md` / `TODO.md` / `INDEX.md` 从 0.8.1 刷新到 0.9.0；`DECISIONS.md` 修正 D4（版本一致性按 major.minor）并新增 D9（C 盘目录是 0.9.0 镜像，不复制 `.git`）。
- C 盘镜像已同步 14 个文件到 0.9.0（逐个 sha256 校验一致）。

### Notes

- 本次提交前，0.9.0 源码一直在工作区未提交；误 checkout/clean 会丢失。现已入库并推送。
- 这次档案刷新（5 个 `.agent` 文件）尚未提交，见 TODO P1。
- D 的 `AGENTS.md` 在提交前一并修正（原文仍写 0.8.0 与「C 目录仅作 0.8.0 归档、不再同步」）。

## 2026-10-25

### Added

- 项目自身的 `.agent/` 上下文档案与 `AGENTS.md`（用 `agent-context init` 生成后填入真实内容），用于把项目交接给新的 Agent 会话。

### Notes

- Created `checkpoint-2026-10-25-145719.md` checkpoint (0 modified/untracked file(s)).

- Created `checkpoint-2026-10-25-145626.md` checkpoint (0 modified/untracked file(s)).

- Created `checkpoint-2026-10-25-140340.md` checkpoint (0 modified/untracked file(s)).

- Created `checkpoint-2026-10-25-140133.md` checkpoint (0 modified/untracked file(s)).

- 这是项目第一次 dogfooding：用自己的工具管理自己的交接状态。

## 2026-10-15（开源发布）

### Added

- GitHub 公开仓库 https://github.com/bsaizne/agent-context-manager （MIT，作者 bsaizne）。
- `README.zh-CN` → 现为中文主 README + `README.en.md`；`CHANGELOG.md`、`CONTRIBUTING.md`、`.gitattributes`、`.github/workflows/tests.yml`。
- Release `v0.8.0`，附件 `Agent.Context.Manager.v0.8.zip`（onedir 整包）。

### Fixed

- PowerShell 直连 GitHub API 建 Release 报 422（JSON 编码/Content-Type），改用 Python `urllib` 完成。

## 2026-10-14（0.8.0）

### Added

- 变更历史（L1）：`.agent/versions/` + GUI `Changes` 页（绿/红染色）+ 编辑器未保存新增行绿底 + 概览「最近变更」卡片。
- `version_history_limit` 配置（默认 30 份，另保留每天首份）。

### Fixed

- `icons.py`：未知图标名调用不存在的 `QPainter.drawCircle()`、`warning` 图标给 `drawPolygon()` 传坐标元组 —— 两者都会让进程直接退出（`QPaintDevice: Cannot destroy paint device that is being painted`）。
- 同秒两条快照按 digest 排序导致 diff 方向反转。

### Changed

- 打包 onefile → **onedir**（原因见 `.agent/DECISIONS.md` D1）。
- 版本号统一到 0.8.0（含两个 spec）。

## 2026-10-11（0.5.0）

### Added

- `agent-context version`；`repair` 按优先级合并重复章节；`checkpoint` 自修复缺失的 `# TODO` 标题。
- 导入安全（路径穿越拒绝、覆盖前备份、保留手写 `AGENTS.md`、`ImportReport`）。
- 死配置接线：`archive_enabled` / `max_state_lines` / `max_todo_lines` / `default_editor`。

### Fixed

- 同分钟 checkpoint 归档互相覆盖；token 统计把 archive 算进上下文；GUI 侧栏高亮不同步；QSS 用 px 字号触发 `QFont::setPointSize` 警告。

## 2026-08-23（0.1.0）

### Added

- 初版：`.agent/` Markdown 协议、CLI 全部基础命令、PySide6 GUI、unittest 测试套件。

## 2026-10-25（0.8.1）

### Fixed

- 侧边栏工具页 off-by-one：Checkpoint/Resume/Doctor/Settings 各错开一页；`_navigate()` 改为 key→widget 显式映射，补回归测试 `tests/test_gui_pages.py`。
- Changes 控制行挤压重叠：单行在默认 1200px 宽度就放不下，箭头被压进下拉框边框；改为两行布局 + 自绘 arrow 图标，补回归测试。

### Released

- v0.8.1 打包 onedir 并发布到 `D:\vibe code`（文件夹 + zip）；GitHub Release 未发。
- 版本一致性测试改为按 major.minor 前缀比对，适配补丁版命名（强度不变）。
