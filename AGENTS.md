# Agent Project Instructions

## 这是什么项目

Agent Context Manager：本地优先的 Python 工具（CLI + PySide6 桌面 GUI），把「继续工作所需的最小项目记忆」写进**任意项目**自己的 `.agent/` 目录，让 AI 编程对话可以跨会话交接，而不必保留聊天记录。

- 仓库：https://github.com/bsaizne/agent-context-manager
- 作者 / 版权：bsaizne，MIT License
- 当前版本：0.9.0（`pyproject.toml`、`src/agent_context/__init__.py`、GUI spec 的 minor、发布包名必须一致）

## Context Management

Before starting work:

1. Read `.agent/STATE.md`.
2. Read `.agent/TODO.md`.
3. Read `.agent/INDEX.md` only when necessary.
4. Do not read `.agent/archive/` unless explicitly required.
5. Do not read the entire project automatically.

## 硬性约束（每一条都是踩过的坑，别重犯）

- **只允许写 `<project>/.agent/`**（外加 `init` 时创建的那一个 `AGENTS.md`）。这是项目的核心承诺，改代码也不能破坏它。
- **Python 进程无法写 C 盘旧目录**：`C:\Users\Bsaizne\Documents\Codex\2026-08-23\files-mentioned-by-the-user-agent\outputs\agent-context-manager` 下，Python 的 `os.makedirs` / `write_text` 会静默失败（退出码 1、无 traceback）。代码改动在本 D 盘主仓库做，再同步到 C 盘镜像（用 bash / pwsh / 文件工具写）。
- **Windows 打包必须是 onedir**（两个 spec 都是 `exclude_binaries=True` + `COLLECT`），不要改回 onefile：本机 `%TEMP%` 已损坏 —— 里面有 13 个连所有者都打不开的 `_MEI*` 残留目录，且 Python 的 `mkdtemp` 在该 TEMP 下会挂死；onefile 启动会直接报 `Could not create temporary directory!`。
- **构建必须绕过执行策略**：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Python <venv python>`（本机 `ExecutionPolicy=Restricted`，直接跑 `.ps1` 会被拒）。
- **跑测试前把 `TMP` / `TEMP` 指到可写目录**（例如 `D:\deepseek harnees\acm-dev\.tmp`），否则依赖 `tempfile` 的测试会整批假失败。
- **版本号一致**：`pyproject.toml`、`__version__`、GUI spec 的 `EXE name`（只带 minor，如 `v0.9`）、发布包名。`tests/test_version_consistency.py` 按 major.minor 前缀比对，别放宽测试；CLI spec 的名称不带版本号。
- **作者署名统一 `bsaizne`**：`LICENSE` 版权行、`pyproject.toml` 的 `authors`、`README` 作者段、`agent_context.__author__`。不要改回 “Contributors”。
- **README 主文件是简体中文**，英文在 `README.en.md`，两者顶部互链；新增/修改文档时保持这个结构。
- **发布目录 `D:\vibe code\Agent Context Manager`：每次小版本自动 +1**（当前 `Agent Context Manager v0.9.0\`，2026-10-28 核实；目录同时保留历史版本 zip），CLI exe 不放进发布目录。
- **Git**：主仓库就是本工作区（D 盘，2026-10-27 从 C 盘整体迁入，含完整历史和 origin，迁移后 fsck 通过）。C 盘 `outputs/agent-context-manager` 是无 `.git` 的镜像，2026-10-28 已按用户要求同步到 0.9.0；代码改动在这里做，再同步过去。remote 走 SSH（key 已认证为 bsaizne），推送无需 token。

## 目录地图

- `src/agent_context/`：唯一业务层（18 个模块）。`cli.py` / `gui.py` 是外壳，逻辑在其余模块；`gui.py` 约 1288 行。
- `tests/`：15 个测试文件，68 个用例 + 45 个 subTest（2026-10-28 实测全绿）。
- `docs/`：`ARCHITECTURE.md`（边界与流程）、`PROTOCOL.md`（`.agent/` 写作协议）、`FUTURE.md`（明确不做的事）。
- `scripts/`：`build-windows.ps1`（打包）、`install-windows-shortcut.ps1`（快捷方式）。
- `agent-context.spec` / `agent-context-gui.spec`：PyInstaller onedir 配置，不要改回 onefile。
- `packaging/`：两个 PyInstaller 入口 stub；`assets/`：图标与品牌图。
- `.github/workflows/tests.yml`：Windows 三个版本跑全量（含离屏 GUI），Linux 只跑 CLI。
- `dist/`、`build/`、`work/`：构建产物/临时目录（`dist`、`build` 已 gitignore）。
- `.agent/archive/`、`.agent/versions/`：checkpoint 与内容快照，已 gitignore，不要手改。

## Commands

```powershell
# 测试（本仓库）
cd "D:\deepseek harnees\acm-dev\agent-context-manager"
$env:TMP="$PWD\..\.tmp"; $env:TEMP=$env:TMP
D:\deepseek harnees\acm-dev\.venv\Scripts\python.exe -m pytest -q

# 打包（onedir）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -Python D:\deepseek harnees\acm-dev\.venv\Scripts\python.exe

# 用项目自己的能力维护自己的档案
agent-context status / doctor / repair / checkpoint / resume
```

## 环境事实（2026-10-28 实测）

- 本仓库是主仓库，有完整 `.git` 和 origin；C 盘镜像没有 `.git`，不要在那里提交。
- 本机 `%TEMP%` 损坏，测试/构建前必须把 `TMP`/`TEMP` 指向 `D:\deepseek harnees\acm-dev\.tmp`。
- 运行中的 `Agent Context Manager v0.9.0` GUI 可能监听项目 `.agent/`，外部修改会触发 `external` 快照；这是工具行为，不要手删。
- C 盘镜像的 `.venv` 已失效；如需在镜像里跑测试，用本仓库的 venv，并加 `-p no:cacheprovider`、`PYTHONDONTWRITEBYTECODE=1`。

## Working Rules

- Treat source code as the source of truth.
- 更新上下文档案时保留已有真实内容，只改过期部分；无法确认的信息写「待确认」，不要用模板或泛泛总结覆盖。
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
