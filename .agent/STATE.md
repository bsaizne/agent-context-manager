# PROJECT STATE

## Project

Agent Context Manager（Python 3.11+，CLI + PySide6 6.12 桌面 GUI）。本地优先、无服务器/无数据库/无网络调用的项目上下文交接工具：在每个项目自己的 `.agent/` 下用 Markdown 保存最小交接记忆。仓库 https://github.com/bsaizne/agent-context-manager ，作者 bsaizne，MIT。

## Current Phase

v0.8.0 已开源发布（GitHub public，CI 全绿，Release v0.8.0 已带 onedir 包）。处于「公开维护 + 按需迭代」阶段。

## Current Task

F1：L2 逐行溯源（P1）。

## Completed

- 上下文协议（STATE/TODO/INDEX/DECISIONS/CHANGELOG + archive）与 CLI 全部命令：init / status / checkpoint / resume / doctor / repair / archive / config / version。
- 结构修复不丢内容：`repair` 合并 STATE 与 TODO 的重复章节，`checkpoint` 可自修复缺失章节与缺失的 `# TODO` 标题。
- 导入安全：拒绝路径穿越与绝对路径、覆盖前备份到 `.agent/archive/import-backup-<时间戳>/`、保留手写 `AGENTS.md`、返回 `ImportReport`。
- 变更历史（L1）：`.agent/versions/` 内容快照 + GUI `Changes` 页（新增绿底/删除红底）+ 编辑器未保存新增行绿底 + 概览「最近变更」卡片。
- 修掉 icons.py 两个会让进程直接退出的缺陷（不存在的 drawCircle、drawPolygon 传元组）。
- 版本号四处统一 0.8.0；GitHub Actions 6 个 job（Windows 3.11/3.12/3.13 含 GUI + Linux CLI 三个版本）全绿。
- 开源配套：中文 README + README.en.md、CHANGELOG、CONTRIBUTING、.gitattributes、CI workflow、About 描述与 topics、Release v0.8.0 与附件。
- 已合并远程 PR #1 的 GUI 修复（13f5f7d）：`init` 成功后清除陈旧的加载错误提示、`_refresh_context` 重新读取 status、补齐 QComboBox 下拉样式；D 盘开发副本已同步该修复。

## Current Problem

本机 `%TEMP%`（C:\Users\Bsaizne\AppData\Local\Temp）损坏：13 个连所有者都无法访问的 `_MEI*` 残留，且 Python `mkdtemp` 在其中会挂死。因此 onefile 打包产物在本机无法启动，必须 onedir；同时所有跑测试/构建的命令都要先把 TMP/TEMP 指到可写目录。修 TEMP 需要管理员权限（takeown + icacls），当前未处理。

## Current Implementation

- `src/agent_context/`：cli.py、gui.py（约 1100 行，PySide6）、state.py、checkpoint.py、versions.py（变更历史）、transfer.py（导出/导入）、doctor.py、project.py、templates.py、utils.py、git.py、archive.py、resume.py、status.py、config.py、icons.py。
- 存储：`<project>/.agent/` 下 5 个 Markdown + `archive/`（checkpoint 快照）+ `versions/`（内容快照，自动裁剪 30 份 + 每天首份）。
- 打包：`agent-context.spec` / `agent-context-gui.spec` 均为 onedir（exclude_binaries + COLLECT）；`scripts/build-windows.ps1` 从 spec 解析产物名并同时接受 onedir / onefile 路径。

## Current Decision

D1 打包用 onedir（onefile 依赖可写 %TEMP%）｜D2 变更历史存整份快照而非 patch｜D3 导入安全优先于便利｜D4 版本号四处一致由测试守住｜D5 作者署名 bsaizne。详见 `.agent/DECISIONS.md`。

## Next Actions

1. L2 逐行溯源：在 `versions.py` 增加 blame（遍历版本链，标出每行首次出现的时间），GUI 在 Changes 页展示。
2. 视需要补中文 CHANGELOG / CONTRIBUTING（用户表示暂不需要）。
3. 下次发版：版本号 +1（v0.9），打包 onedir，放 `D:\vibe code`，用 `D:\vibe code\gh_release.py` 发 Release（需要临时 token，用完删除 `.ghtoken` 并提醒撤销）。

## Important Constraints

- 只写 `<project>/.agent/`，绝不改业务代码。
- Python 进程无法写 C 盘主目录（用 pwsh/文件工具，或在 D 盘副本改完同步）。
- 打包必须 onedir；构建必须 `-ExecutionPolicy Bypass`；测试前把 TMP/TEMP 指到可写目录。
- 版本号四处一致、作者署名 bsaizne、README 中文为主 + README.en.md。
- 发布目录 `D:\vibe code` 命名按小版本 +1。

## Known Issues

- 本机 %TEMP% 损坏（见 Current Problem），影响所有 onefile 程序与部分临时目录依赖。
- 同一秒内两次快照的顺序此前依赖 digest，已改为按 index 记录顺序；`versions.py` 里保留注释说明。
- GUI 的 PySide6 字体目录告警（`QFontDatabase: Cannot find font directory`）是 PySide6 wheel 不带字体导致，无功能影响。

## Last Updated

2026-10-25 14:03
