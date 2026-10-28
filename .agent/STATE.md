# PROJECT STATE

## Project

Agent Context Manager（Python 3.11+，CLI + PySide6 桌面 GUI）。本地优先、无服务器/无数据库/无网络调用的项目上下文交接工具：在每个项目自己的 `.agent/` 下用 Markdown 保存最小交接记忆。仓库 https://github.com/bsaizne/agent-context-manager ，作者 bsaizne，MIT。

本目录是主仓库（D 盘，含完整 `.git` 与 origin）；C 盘 `outputs/agent-context-manager` 是无 `.git` 的镜像，2026-10-28 已同步到 0.9.0。

## Current Phase

v0.9.0 已完成、提交并推送：功能提交 `4ba0200`、档案刷新 `3a53e3e` 均在 `origin/main`，工作区干净。本地发布包在 `D:\vibe code\Agent Context Manager`（2026-10-27）；GitHub Release v0.9.0 是否已发布待确认。

## Current Task

F1：L2 逐行溯源（P1）——在 `versions.py` 增加 blame（遍历版本链，标出每行首次出现的时间），GUI 在 Changes 页展示。0.9.0 的 CHANGELOG 未包含此项。

## Completed

- 上下文协议（STATE/TODO/INDEX/DECISIONS/CHANGELOG + archive）与 CLI 全部 9 个命令：init / status / checkpoint / resume / doctor / repair / archive / config / version。
- 结构修复不丢内容：`repair` 合并 STATE 与 TODO 的重复章节，`checkpoint` 可自修复缺失章节与缺失的 `# TODO` 标题。
- 导入安全：拒绝路径穿越与绝对路径、覆盖前备份、保留手写 `AGENTS.md`、返回 `ImportReport`。
- 变更历史（L1）：`.agent/versions/` 内容快照 + GUI `Changes` 页 + 编辑器未保存新增行绿底 + 概览「最近变更」。
- 0.8.0：版本统一、icons 致命绘制缺陷修复、开源配套与 Release。
- 0.8.1（2026-10-25）：侧栏工具页 off-by-one 修复（`_page_for_key` 显式映射）；Changes 控制行改两行布局；回归测试 `tests/test_gui_pages.py`。
- 0.9.0（2026-10-27）：handoff prompt 可配置（`agent_prompt_template`，支持 `{project}` / `{resume}`，缺 `{resume}` 时自动追加）；combobox 下拉主题跟随应用主题；回归测试覆盖 resume/config/gui_pages。
- 2026-10-28：0.9.0 源码提交为 `4ba0200` 并推送到 `origin/main`，推送后远端 sha 与本地 HEAD 一致。
- 2026-10-28：C 盘镜像从本仓库同步 14 个文件到 0.9.0（逐个 sha256 校验一致），见 DECISIONS D9。
- 2026-10-28 实测测试基线：15 个测试文件、68 个用例 + 45 个 subTest 全绿（3.23s，离屏 Qt）。

## Current Problem

1. 本机 `%TEMP%` 损坏：13 个不可访问的 `_MEI*` 残留，Python `mkdtemp` 会挂死；修它需要管理员权限。
2. GitHub Release v0.9.0 的状态未确认（本地包已存在）。
3. C 盘镜像是无 `.git` 的副本，代码改动若只在那里做不会进入版本历史（D9 的对策是改动回主仓库再做同步）。

## Current Implementation

- `src/agent_context/` 18 个模块：gui 1288 行、versions 347、cli 326、state 324、templates 229、transfer 217、checkpoint 208、utils 182、doctor 173、icons 146、project 118、resume 96、git 89、config 47、status 46、archive 38。
- 存储：`<project>/.agent/` 5 个 Markdown + `archive/`（checkpoint 快照）+ `versions/`（内容快照，默认每文件 30 份 + 每天首份）。
- GUI：Overview + 5 个可编辑文档（STATE/TODO/INDEX/DECISIONS/CHANGELOG）+ Changes + Checkpoint + Resume + Doctor + Settings；侧栏仍只有 4 个文档入口，INDEX 无入口。
- 配置默认值（`templates.DEFAULT_CONFIG`）：`archive_enabled=True`、`max_state_lines=120`、`max_todo_lines=100`、`default_editor=None`、`version_history_limit=30`、`agent_prompt_template=<默认模板>`。
- 打包：两个 spec 均 onedir（`exclude_binaries=True` + `COLLECT`）；`scripts/build-windows.ps1` 从 spec 解析产物名，同时接受 onedir / onefile 路径。
- 测试：15 文件 / 68 用例 / 45 subTest；`test_gui_pages.py` 覆盖侧栏导航与 Changes 控件布局；`test_version_consistency.py` 按 major.minor 比对。

## Current Decision

D1 onedir｜D2 整份快照而非 patch｜D3 导入安全优先｜D4 版本号一致由测试守｜D5 署名 bsaizne｜D6 中文 README 为主｜D7 `versions/` 不导出不计 tokens｜D8 只写 `<project>/.agent/`｜D9 C 盘目录是本仓库的 v0.9.0 镜像（不复制 `.git`，改动回主仓库做）。详见 `.agent/DECISIONS.md`。

## Next Actions

1. 继续 F1：在 `versions.py` 增加 blame，并在 Changes 页展示。
2. 下次发版 v0.10：版本号 +1（pyproject / `__version__` / GUI spec）、onedir 打包、产物放 `D:\vibe code`。
3. 视需要把 `agent_prompt_template` 补进 `docs/ARCHITECTURE.md`（README 已有说明）。
4. 确认 GitHub Release v0.9.0 是否已发布。
5. 之后每次改动主仓库后，按 D9 把 C 盘镜像同步到同一版本。

## Important Constraints

- 本仓库是主仓库，提交/推送在这里做；C 盘镜像没有 `.git`，不要在那里提交。
- 只允许写 `<project>/.agent/`（外加 `init` 时创建的那一个 `AGENTS.md`）；这是产品承诺，改代码也不能破坏。
- 本机 `%TEMP%` 损坏；测试/构建前把 `TMP`/`TEMP` 指向 `D:\deepseek harnees\acm-dev\.tmp`。
- 打包必须 onedir；构建必须 `-ExecutionPolicy Bypass`。
- 版本号一致（pyproject / `__version__` / GUI spec 的 minor / 发布包名）；作者署名 bsaizne；README 中文为主 + `README.en.md`。
- 发布目录 `D:\vibe code\Agent Context Manager` 按小版本 +1，当前已有 v0.9.0。
- 推送时机由用户决定。

## Known Issues

- 本机 `%TEMP%` 损坏，onefile 程序无法启动；所有临时目录依赖需重定向。
- `INDEX.md` 有编辑页但侧栏无入口（0.9.0 仍未加入）；是否刻意待确认。
- `docs/ARCHITECTURE.md` 尚未描述 0.9.0 的 `agent_prompt_template`（README 已写）。
- PySide6 字体目录告警无功能影响。
- C 盘镜像的 `.venv` 已失效；在镜像里跑测试需借用本仓库的 venv + 其 `.tmp`。

## Last Updated

2026-10-28 22:48
