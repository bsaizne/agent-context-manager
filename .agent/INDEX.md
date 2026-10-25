# PROJECT INDEX

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
- README.md（简体中文，主入口）/ README.en.md（英文）
- CHANGELOG.md（发布级变更史）

---

## 模块清单

| 文件 | 职责 | 关键点 |
| --- | --- | --- |
| `cli.py` | 9 个子命令（init/status/checkpoint/resume/doctor/repair/archive/config/version） | cp936 控制台编不出 `✓` 时自动降级为纯文本 |
| `gui.py` | PySide6 主窗口：概览、5 个编辑页、Changes、Checkpoint、Resume、Doctor、Settings | Markdown 高亮、外部变更监听（重载前先存快照）、概览缓存、红绿 diff 染色 |
| `state.py` | STATE/TODO 解析与校验、结构修复 | `auto_repair_state` 合并重复章节；`merge_duplicate_sections` 按优先级合并 TODO |
| `checkpoint.py` | 刷新 Last Updated、写归档、追加 CHANGELOG、前后各存版本快照 | 先修复再校验，避免半写盘 |
| `versions.py` | 变更历史（L1）：快照、索引、裁剪、行级 diff、概览摘要 | 内容 sha256 去重；保留最近 N 份 + 每天首份 |
| `transfer.py` | `.agentctx.json` 导出/导入、token 估算 | 拒绝路径穿越；覆盖前备份；保留手写 AGENTS.md |
| `doctor.py` | 健康检查（11 项 + 体量告警） | `max_state_lines` / `max_todo_lines` 真正接线 |
| `project.py` | 路径解析、`init`、向上查找 `.agent/` | `AGENTS.md` 已存在时绝不覆盖 |
| `templates.py` | 5 个上下文文件 + `AGENTS.md` 模板、`DEFAULT_CONFIG` | 模板措辞必须与实现一致 |
| `icons.py` | 24×24 矢量图标 | `icon()` 用 try/finally 关闭 painter，未知名字降级为圆圈而不是崩溃 |
| `utils.py` | 原子写、UTF-8 读写、章节提取、时间戳、`unique_path` | 原子替换；秒级时间戳 + 冲突后缀 |
| `git.py` | `git status --short` / `log -5 --oneline` | 15s 超时、Windows 隐藏控制台、无 Git 时优雅降级 |
| `archive.py` / `status.py` / `resume.py` / `config.py` | 归档列举读取 / 状态汇总 / 最小恢复文本 / 用户配置 | `resume` 只读 STATE + TODO |

## Important Files

### File

tests/（13 个测试文件，58 个用例 + 20 个子测试）

### Purpose

回归网。重点：`test_repair.py`（结构修复不丢内容）、`test_versions.py`（变更历史）、`test_transfer_safety.py`（导入安全）、`test_version_consistency.py`（四处版本号一致）、`test_gui_bootstrap_prompt.py`（含图标回归）。

### File

agent-context.spec / agent-context-gui.spec

### Purpose

PyInstaller **onedir** 配置（`exclude_binaries=True` + `COLLECT`）。不要改回 onefile —— 原因写在 `.agent/DECISIONS.md` 的 D1。

### File

scripts/build-windows.ps1

### Purpose

构建两个产物；从 spec 解析产物名，同时接受 `dist\<name>\<name>.exe`（onedir）与 `dist\<name>.exe`（onefile）。本机要用 `-ExecutionPolicy Bypass` 调用。

### File

.github/workflows/tests.yml

### Purpose

CI：Windows 3.11/3.12/3.13 跑全量（含离屏 GUI 测试）；Linux 只跑 CLI（忽略 GUI 测试文件，避免缺 X/OpenGL 栈）。
