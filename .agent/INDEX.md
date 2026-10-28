# PROJECT INDEX

## 快速导航

| 想找什么 | 去哪里 |
| --- | --- |
| 业务逻辑 | `src/agent_context/`（18 个模块，见下表） |
| CLI 入口 | `src/agent_context/cli.py` → `pyproject.toml` 的 `agent-context` |
| GUI 入口 | `src/agent_context/gui.py` → `pyproject.toml` 的 `agent-context-gui` |
| 测试 | `tests/`（15 文件 / 68 用例 + 45 subTest，2026-10-28 全绿） |
| 架构与边界 | `docs/ARCHITECTURE.md` |
| `.agent/` 写作协议 | `docs/PROTOCOL.md` |
| 明确不做的事 | `docs/FUTURE.md` |
| 打包 | `agent-context.spec`、`agent-context-gui.spec`、`scripts/build-windows.ps1` |
| CI | `.github/workflows/tests.yml` |
| 当前状态/下一步 | `.agent/STATE.md`、`.agent/TODO.md` |

## Module

### Name

agent_context（核心包，CLI 与 GUI 共用）

### Path

src/agent_context/

### Description

全部业务逻辑。CLI（Typer/Rich，带 argparse 兜底）与 PySide6 桌面 GUI 都只是这层的外壳。

### Related Documentation

- docs/ARCHITECTURE.md（边界、数据模型、checkpoint/resume 流程、变更历史、导入安全、token 统计）
- docs/PROTOCOL.md（`.agent/` 各文件的写作协议）
- docs/FUTURE.md（V3 想法与当前定位）
- README.md（简体中文，主入口）/ README.en.md（英文）
- CHANGELOG.md（发布级变更史，已到 0.9.0）

---

## 模块清单

| 文件 | 职责 | 关键点 |
| --- | --- | --- |
| `cli.py` | 9 个子命令（init/status/checkpoint/resume/doctor/repair/archive/config/version） | cp936 控制台编不出 `✓` 时自动降级为纯文本 |
| `gui.py` | PySide6 主窗口：Overview、5 个可编辑文档、Changes、Checkpoint、Resume、Doctor、Settings | 侧栏自 v0.8.1 用 `_page_for_key` 显式映射；Settings 可编辑 handoff prompt 模板 |
| `state.py` | STATE/TODO 解析与校验、结构修复 | `auto_repair_state` 合并重复章节；`merge_duplicate_sections` 按优先级合并 TODO |
| `checkpoint.py` | 刷新 Last Updated、写归档、追加 CHANGELOG、前后各存版本快照 | 先修复再校验，避免半写盘 |
| `versions.py` | 变更历史（L1）：快照、索引、裁剪、行级 diff、概览摘要 | 内容 sha256 去重；保留最近 N 份 + 每天首份 |
| `transfer.py` | `.agentctx.json` 导出/导入、token 估算 | 拒绝路径穿越；覆盖前备份；保留手写 AGENTS.md |
| `doctor.py` | 健康检查（结构、编码、Git、体量告警） | `max_state_lines` / `max_todo_lines` 真正接线 |
| `project.py` | 路径解析、`init`、向上查找 `.agent/` | `AGENTS.md` 已存在时绝不覆盖 |
| `templates.py` | 5 个上下文文件 + `AGENTS.md` 模板、`DEFAULT_CONFIG`、默认 handoff prompt | 模板措辞必须与实现一致 |
| `resume.py` | 最小恢复文本 + `render_agent_prompt()` | 从 `agent_prompt_template` 渲染；缺 `{resume}` 时自动追加 |
| `icons.py` | 24×24 矢量图标 | `icon()` 用 try/finally 关闭 painter，未知名字降级为圆圈而不是崩溃 |
| `utils.py` | 原子写、UTF-8 读写、章节提取、时间戳、`unique_path` | 原子替换；秒级时间戳 + 冲突后缀 |
| `git.py` | `git status --short` / `log -5 --oneline` | 15s 超时、Windows 隐藏控制台、无 Git 时优雅降级 |
| `archive.py` / `status.py` / `config.py` | 归档列举读取 / 状态汇总 / 用户配置 | `resume` 只读 STATE + TODO；配置在 `~/.agent-context/config.json` |

## Important Files

### File

tests/（15 个测试文件，68 个用例 + 45 个子测试）

### Purpose

回归网。重点：`test_repair.py`（结构修复不丢内容）、`test_versions.py`（变更历史）、`test_transfer_safety.py`（导入安全）、`test_version_consistency.py`（版本号 major.minor 一致）、`test_gui_bootstrap_prompt.py`（图标）、`test_gui_pages.py`（侧栏导航与 Changes 控件布局）、`test_resume.py` / `test_config.py`（0.9.0 prompt 模板）。

### File

agent-context.spec / agent-context-gui.spec

### Purpose

PyInstaller **onedir** 配置（`exclude_binaries=True` + `COLLECT`）。不要改回 onefile —— 原因写在 `.agent/DECISIONS.md` 的 D1。GUI 产物名带 minor 版本（当前 `Agent Context Manager v0.9.0`）。

### File

scripts/build-windows.ps1

### Purpose

构建两个产物；从 spec 解析产物名，同时接受 `dist\<name>\<name>.exe`（onedir）与 `dist\<name>.exe`（onefile）。本机要用 `-ExecutionPolicy Bypass` 调用。

### File

.github/workflows/tests.yml

### Purpose

CI 共 6 个 job：Windows 3.11/3.12/3.13 跑全量（`QT_QPA_PLATFORM=offscreen`，含 GUI 测试）；Linux 三个版本只跑 CLI（`--ignore=tests/test_gui_bootstrap_prompt.py`，避免缺 X/OpenGL 栈）。

## 仓库结构（2026-10-28 核实）

| 路径 | 用途 |
| --- | --- |
| `src/agent_context/` | 唯一业务层，18 个模块 |
| `tests/` | 15 个测试文件 |
| `docs/` | ARCHITECTURE / PROTOCOL / FUTURE |
| `scripts/` | build-windows.ps1、install-windows-shortcut.ps1 |
| `packaging/` | 两个 PyInstaller 入口 stub |
| `assets/` | branding.ico / branding.svg / branding-preview.png |
| `.github/workflows/` | tests.yml |
| `dist/`、`build/`、`work/` | 构建产物/临时目录（`dist`、`build` 已 gitignore） |
| `.agent/` | 本档案；`archive/` 与 `versions/` 已 gitignore |

## 当前仓库状态

- 主仓库：`4ba0200` 已推送到 `origin/main`，工作区干净。
- 本地发布包：`D:\vibe code\Agent Context Manager\Agent Context Manager v0.9.0\`。
- C 盘镜像 `outputs/agent-context-manager` 已同步到 0.9.0，无 `.git`；改动回本仓库做。
