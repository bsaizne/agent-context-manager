# Agent Context Manager

**简体中文** | [English](README.en.md)

[![tests](https://github.com/bsaizne/agent-context-manager/actions/workflows/tests.yml/badge.svg)](https://github.com/bsaizne/agent-context-manager/actions/workflows/tests.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)

一个纯本地、基于文件的方式，把一个项目从一段 AI 编程对话交接给下一段 —— 不需要保留聊天记录。

## Agent Context Manager 是什么？

Agent Context Manager 是一个本地 CLI，用来在 AI 编程对话之间交接项目状态。它把「继续工作所需的最小项目记忆」写进每个项目自己的 `.agent/` 目录下的 Markdown 文件。

它不保存完整聊天记录。它保留的是当前状态、任务、决策、变更和导航线索，让新的 Agent 不必把之前的对话重新拼一遍就能接着干。

## 为什么需要它？

长对话迟早会撞上上下文上限。真正有用的交接内容很少是完整转写，而是：当前在做什么、已经做完什么、卡在哪、相关文件在哪、有哪些约束不能违反。

Agent Context Manager 就是把这些信息保持得短、留在本地、并且只属于当前项目。

## 环境要求

- Python 3.11 或更高版本。CLI 只依赖标准库加上 Typer 和 Rich。
- Git 是可选的；检测到 Git 时，checkpoint 会记录 `git status` 和最近的提交。
- Windows 图形界面需要 PySide6 6.7+ 和 Windows 10 1903 或更高版本（Qt 链接系统自带的 ICU，所以 ICU 运行库永远不会被打进产物里）。
- CLI 支持 macOS 和 Linux；图形界面目前仅限 Windows。

## 安装

开发模式安装：

```bash
pip install -e .
```

可选的开发工具：

```bash
pip install -e ".[test,package]"
```

安装完成后：

```bash
agent-context --help
```

## 快速开始

```bash
cd my-project
agent-context init
agent-context status
agent-context resume
```

当对话开始变长时：

```bash
agent-context checkpoint
```

在新的一段 Agent 对话里：

```bash
agent-context resume
```

## 命令

### init

创建 `.agent/` 目录和最初的 Markdown 协议文件：

```bash
agent-context init
agent-context init /path/to/project
```

如果 `AGENTS.md` 已经存在，它不会被覆盖。

### status

显示上下文文件是否存在、当前阶段、当前任务、Git 检测结果、被修改文件数量、最后一次 checkpoint，以及待办数量：

```bash
agent-context status
```

### checkpoint

刷新 `.agent/STATE.md` 的更新时间、记录一份轻量归档、更新 `.agent/CHANGELOG.md`，并在有 Git 时汇总 Git 状态：

```bash
agent-context checkpoint
```

它只会写入 `.agent/` 目录内部。

### resume

打印最小恢复上下文。默认只读取 `.agent/STATE.md` 和 `.agent/TODO.md`：

```bash
agent-context resume
agent-context resume --prompt
```

### doctor

检查 Python 版本、项目结构、上下文文件、`AGENTS.md`、Git 是否可用、UTF-8 编码以及项目隔离：

```bash
agent-context doctor
```

### repair

把 `STATE.md` 和 `TODO.md` 重写成协议结构，**并且不丢内容**。它会补齐缺失的必需/可选章节、合并重复章节（两段内容都会保留并标记），并恢复缺失的顶层 `# TODO` 标题：

```bash
agent-context repair
```

当上下文文件被手工或 Agent 重写，`status` / `resume` / `checkpoint` 开始报 `STATE.md needs attention` 时就用它。它还会补回缺失的顶层 `# TODO` 标题，并合并 `TODO.md` 里重复的 `##` 章节（内容不会丢失）。图形界面的 Doctor 页和概览页的「STATE.md 需要修复」卡片提供同样功能。

### archive

列出归档的 checkpoint，不会恢复或覆盖当前状态：

```bash
agent-context archive
agent-context archive --show 1
```

### config

显示并创建本地用户级配置 `~/.agent-context/config.json`：

```bash
agent-context config
```

测试或沙箱运行时，可以用 `AGENT_CONTEXT_CONFIG_DIR` 把 `config.json` 写到别处。

### version

打印已安装的版本：

```bash
agent-context version
```

## Windows 图形界面

Windows 桌面版使用 PySide6，与 CLI 共用同一套 `.agent/` 文件。

安装图形界面依赖：

```powershell
pip install -e ".[gui]"
```

在项目目录里启动：

```powershell
agent-context-gui
```

或者直接传入项目路径：

```powershell
agent-context-gui "D:\Projects\MyProject"
```

图形界面提供项目选择、初始化、上下文 Markdown 编辑、创建 checkpoint、复制恢复文本、归档预览和健康检查。此外还有：

- **复制填充提示词** —— 复制一段中文提示词，让新的 Agent 知道该读哪些文件、只允许改哪些文件。
- **导出项目 / 导入项目** —— `.agentctx.json` 迁移文件。导入时会把被替换的每个文件备份到 `.agent/archive/import-backup-<时间戳>/`，保留已有的手写 `AGENTS.md`，并拒绝任何试图逃出目标目录的路径。
- **上下文档案 tokens** —— 新 Agent 真正会加载的上下文规模。`.agent/archive/` 会单独列出，因为 `resume` 从不读取它。
- **外部打开** —— 用 `default_editor` 或系统默认程序打开当前上下文文件。
- **Changes / 变更** —— 对比同一个文件任意两个已记录版本：新增行绿色、删除行红色，两侧各带自己的时间。你打字时，编辑器也会把你「新增但尚未保存」的行标绿。

## 项目结构

初始化之后，项目里会多出：

```text
.agent/
├── STATE.md
├── TODO.md
├── INDEX.md
├── DECISIONS.md
├── CHANGELOG.md
├── archive/
└── versions/        # 变更历史快照（自动管理）
AGENTS.md
```

源码布局：

```text
src/agent_context/
├── cli.py
├── config.py
├── project.py
├── state.py
├── checkpoint.py
├── resume.py
├── git.py
├── archive.py
├── doctor.py
├── templates.py
├── transfer.py
├── versions.py
├── icons.py
├── gui.py
└── utils.py
```

## 上下文协议

`STATE.md` 表示项目的当前状态，不是历史日志。每次 checkpoint 都是把它更新到最新，而不是把旧总结往下追加。

`TODO.md` 存放简短的 P0/P1/P2/Blocked 任务列表，不应重复 `STATE.md` 里已有的长篇说明。

`DECISIONS.md` 只记录重要的技术决策。

`CHANGELOG.md` 记录随时间发生的真实变更。

`INDEX.md` 指向相关文件，不要把源码复制进去。

`.agent/archive/` 存放历史 checkpoint 快照；`resume` 默认不读归档。

`.agent/versions/` 为每个上下文文件保存内容快照（包括 Agent 在程序开着的时候做的修改）。图形界面的 `Changes` 页就是拿它做对比；它会被自动裁剪（见 `agent-context config` 里的 `version_history_limit`），并且**绝对不要手工编辑**。`export` 会跳过它，让迁移文件保持小体积。

## 在 Claude 中的用法

### 新项目

```bash
cd my-project
agent-context init
```

告诉 Claude：

```text
Read AGENTS.md and follow the project context protocol.
```

### 工作中

正常干活。当对话变长时：

```bash
agent-context checkpoint
```

### 新对话

```bash
agent-context resume
```

把输出粘贴给 Claude。

## 在 Codex 中的用法

初始化一次：

```bash
agent-context init
```

每开始一个新的 Codex 任务时运行：

```bash
agent-context resume
```

让 Codex 先读 `AGENTS.md`，然后只检查与当前任务相关的文件。

## 在 Cursor 中的用法

初始化项目：

```bash
agent-context init
```

切换 Cursor 聊天窗口时：

```bash
agent-context resume
```

粘贴恢复输出，并告诉 Cursor 不要扫描整个项目，除非确实需要。

## Windows

用 PowerShell 或命令提示符：

```powershell
pip install -e .
agent-context init
agent-context status
```

包含中文、空格和 Unicode 字符的路径都受支持，因为内部使用 `pathlib` 和 UTF-8 读写 Markdown。

## 常见问题

先运行：

```bash
agent-context doctor
```

常见处理方式：

- 缺少 `.agent/`：运行 `agent-context init`。
- Markdown 编码不合法：把文件保存为 UTF-8。
- 没检测到 Git：安装 Git，或者不用 Git 集成继续使用。
- `AGENTS.md` 已存在：工具会按设计跳过，不会覆盖你项目里的说明。
- 报 `STATE.md needs attention` / `missing required sections`：文件被重写时丢了协议章节。运行 `agent-context repair` 补回来（内容会保留）。
- 待办数量显示 `P0: 0`：`TODO.md` 需要 `## P0` / `## P1` / `## P2` / `## Blocked` 标题。`repair` 会补回 `# TODO` 标题，但不会替你编造优先级。
- 永远不要整体重写 `.agent/STATE.md`，也不要删除或重命名它的 `##` 章节。要原地更新章节；整篇重写正是让 `status` / `resume` / `checkpoint` 坏掉的原因。
- `TODO.md` 里出现重复的 `## P0` / `## P1` 块：只有第一块会被读取，剩下的过去会从 `status` 和 `resume` 里静默消失。现在 `repair` 会合并重复内容并保留每一行。
- `TODO.md` 丢了标题时运行 `checkpoint`：标题会自动补回。0.5 之前会在 `STATE.md` 已经被重写之后才中止，结果归档一个都没留下。
- 导入迁移文件：被替换的文件会备份到 `.agent/archive/import-backup-<时间戳>/`，已有的手写 `AGENTS.md` 会被保留而不是覆盖。
- `.agent/versions/` 越来越大：它默认保留每个文件最近 30 个版本，外加每天的第一个版本。如果历史太多，用 `agent-context config` 调低 `version_history_limit`。

## 开发

不装任何外部测试依赖，直接用标准库跑测试：

```bash
python -m unittest discover -s tests
```

装了 pytest 之后：

```bash
pip install -e ".[test,gui]"
pytest
```

图形界面测试会导入 PySide6；缺少 `gui` 依赖时它们会自行跳过。只装 `[test]` 时，pytest 过去会直接中断整个收集过程。

CLI 在检测到 Typer 和 Rich 时使用它们；同时保留了一个小型 argparse/纯文本降级路径，让核心逻辑在没有这些依赖的环境中依然能跑。

## 测试覆盖

测试套件覆盖：

- 初始化以及 `AGENTS.md` 的保留
- UTF-8 状态解析
- checkpoint 归档创建
- 最小化 resume 输出
- 不同 `.agent/` 目录之间的项目隔离
- Git 检测与 `git status --short`
- 变更历史：去重、保留策略、差异分类
- 导入安全：路径逃逸、备份、手写 `AGENTS.md` 保留

## 打包

安装 PyInstaller：

```bash
pip install -e ".[gui,package]"
```

Windows PowerShell：

```powershell
.\scripts\build-windows.ps1
```

如果 Windows 禁止运行本地脚本（提示 running scripts is disabled on this system），用绕过策略执行同一个脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

产物：

```text
dist\agent-context\agent-context.exe                            (CLI)
dist\Agent Context Manager v0.9\Agent Context Manager v0.9.exe  (Windows GUI)
```

Windows 产物是 **onedir** 而不是 onefile：程序需要的东西都放在可执行文件旁边，所以分发时必须带上整个文件夹。这是刻意的选择 —— onefile 版本每次启动都会把自己解压到 `%TEMP%`，而在 `%TEMP%` 已经损坏的机器上（例如存在连打开都失败的 `_MEI` 残留目录），引导器会在任何应用代码运行之前就报 `Could not create temporary directory!`。onedir 版本直接从自己的目录加载 DLL，完全不需要可写的 `%TEMP%`。

Windows 打包是纯本地的，不需要 Node.js、数据库或服务器。

## 更新

拉取或复制更新后的源码，然后重新安装：

```bash
pip install -e .
```

使用打包好的 Windows 程序时，用 `scripts\build-windows.ps1` 重新构建。

## 变更记录与贡献

各版本之间的改动见 [CHANGELOG.md](CHANGELOG.md)。想提交补丁的话，[CONTRIBUTING.md](CONTRIBUTING.md) 说明了环境搭建方式，以及最重要的两条规则：守住 `.agent/` 边界，并给每个修复补一个回归测试。

## 作者

本项目由 **bsaizne** 创建与维护。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
