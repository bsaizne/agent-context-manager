# Agent Project Instructions

## 这是什么项目

Agent Context Manager：本地优先的 Python 工具（CLI + PySide6 桌面 GUI），把「继续工作所需的最小项目记忆」写进**任意项目**自己的 `.agent/` 目录，让 AI 编程对话可以跨会话交接，而不必保留聊天记录。

- 仓库：https://github.com/bsaizne/agent-context-manager
- 作者 / 版权：bsaizne，MIT License
- 当前版本：0.8.0（`pyproject.toml`、`src/agent_context/__init__.py`、两个 PyInstaller spec、发布包名四处必须一致）

## Context Management

Before starting work:

1. Read `.agent/STATE.md`.
2. Read `.agent/TODO.md`.
3. Read `.agent/INDEX.md` only when necessary.
4. Do not read `.agent/archive/` unless explicitly required.
5. Do not read the entire project automatically.

## 硬性约束（每一条都是踩过的坑，别重犯）

- **只允许写 `<project>/.agent/`**（外加 `init` 时创建的那一个 `AGENTS.md`）。这是项目的核心承诺，改代码也不能破坏它。
- **Python 进程无法写 C 盘主目录**：`C:\Users\Bsaizne\Documents\Codex\2026-08-23\files-mentioned-by-the-user-agent\outputs\agent-context-manager` 下，Python 的 `os.makedirs` / `write_text` 会静默失败（退出码 1、无 traceback）。要用 pwsh / 文件工具写，或在 D 盘开发副本改完再同步。
- **Windows 打包必须是 onedir**（两个 spec 都是 `exclude_binaries=True` + `COLLECT`），不要改回 onefile：本机 `%TEMP%` 已损坏 —— 里面有 13 个连所有者都打不开的 `_MEI*` 残留目录，且 Python 的 `mkdtemp` 在该 TEMP 下会挂死；onefile 启动会直接报 `Could not create temporary directory!`。
- **构建必须绕过执行策略**：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Python <venv python>`（本机 `ExecutionPolicy=Restricted`，直接跑 `.ps1` 会被拒）。
- **跑测试前把 `TMP` / `TEMP` 指到可写目录**（例如 `D:\deepseek harnees\acm-dev\.tmp`），否则依赖 `tempfile` 的测试会整批假失败。
- **版本号四处一致**：`pyproject.toml`、`__version__`、两个 spec 的 `EXE name`、发布包名。`tests/test_version_consistency.py` 会校验，别放宽测试，改版本号。
- **作者署名统一 `bsaizne`**：`LICENSE` 版权行、`pyproject.toml` 的 `authors`、`README` 作者段、`agent_context.__author__`。不要改回 “Contributors”。
- **README 主文件是简体中文**，英文在 `README.en.md`，两者顶部互链；新增/修改文档时保持这个结构。
- **发布目录 `D:\vibe code`：每次小版本自动 +1**（当前 `Agent Context Manager v0.8\`），CLI exe 不放进发布目录。
- **Git**：仓库主目录在 C 盘（需要 `git config --global --add safe.directory <该目录>`，因为目录所有者是 `CodexSandboxOffline`）；remote 走 SSH（key 已认证为 bsaizne），推送无需 token。

## Commands

```powershell
# 测试（在开发副本里，用它的 venv）
cd "D:\deepseek harnees\acm-dev\agent-context-manager"
$env:TMP="$PWD\..\.tmp"; $env:TEMP=$env:TMP
D:\deepseek harnees\acm-dev\.venv\Scripts\python.exe -m pytest -q

# 打包（onedir）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Python D:\deepseek harnees\acm-dev\.venv\Scripts\python.exe

# 用项目自己的能力维护自己的档案
agent-context status / doctor / repair / checkpoint / resume
```

## Working Rules

- Treat source code as the source of truth.
- Do not copy large code blocks into context documents.
- Do not rewrite completed work without a reason.
- Respect existing architectural decisions (`.agent/DECISIONS.md`).
- 每个 bug 修复都要补一个回归测试，并让测试能说明「它本来能抓住什么」。
- 注释解释 **why**：不解释原因的工作区会被下一个人删掉。
- Update project state after major milestones.

## Checkpoint

当对话变长或要换 Agent：

```powershell
agent-context checkpoint
```

它只在 `.agent/` 内写：刷新 `STATE.md` 的 Last Updated、补回缺失章节、补回缺失的 `# TODO` 标题、往 `CHANGELOG.md` 追加一条、在 `.agent/archive/` 存快照、在 `.agent/versions/` 存内容快照。

它**不会**替你重写 TODO 项、`DECISIONS.md` 或 `INDEX.md`。

## Resume

新会话开始时：

```powershell
agent-context resume
```

只加载继续工作所需的最小信息；不要默认把整个项目读一遍。
