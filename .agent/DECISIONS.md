# DECISIONS

## D1 Windows 打包用 onedir，不用 onefile

- **Decision**：两个 spec 都产出目录（`exclude_binaries=True` + `COLLECT`），发布包是整目录 zip。
- **Reason**：onefile 每次启动都要把自己解压到 `%TEMP%`。本机 `%TEMP%` 已损坏（13 个连所有者都打不开的 `_MEI*` 残留；Python 的 `mkdtemp` 在该 TEMP 下会挂死），onefile 会在应用代码运行前就报 `Could not create temporary directory!`。onedir 直接从自己的目录加载 DLL，不需要可写 `%TEMP%`。
- **Alternatives**：启动器 `.cmd` 先设 TEMP 再启动（实测仍失败）；修 `%TEMP%` ACL（需要管理员权限）。
- **Rejected**：继续 onefile 并要求用户修系统 TEMP —— 对使用者不友好，且这类环境问题很常见。

## D2 变更历史存整份内容快照，而不是 patch

- **Decision**：`.agent/versions/<文件名>/<时间戳>-<digest>.md` 每份是完整文件；索引记录时间、来源、行数、digest。
- **Reason**：上下文文件只有几 KB，整份存储永不「打错补丁」；patch 链一旦有一环坏掉，整条历史就废了。
- **Alternatives**：统一 diff 累积、git 内部对象。
- **Rejected**：patch 链（脆弱）；依赖 git（项目承诺无 git 也能用）。

## D3 导入安全优先于便利

- **Decision**：`import_project` 拒绝绝对路径与 `..`；覆盖前把旧文件备份到 `.agent/archive/import-backup-<时间戳>/`；已存在的手写 `AGENTS.md` 一律保留；返回 `ImportReport`。
- **Reason**：迁移文件是外部输入，路径穿越可写出项目外；静默覆盖会吞掉用户手写内容。两者都是不可接受的数据损失。
- **Alternatives**：全部覆盖（原行为）；只提示不备份。
- **Rejected**：静默覆盖（真实事故）；无备份的覆盖。

## D4 版本号四处一致，由测试强制

- **Decision**：`pyproject.toml`、`agent_context.__version__`、两个 spec 的 `EXE name`、发布包名必须一致；`tests/test_version_consistency.py` 校验前两者与 spec 的 minor 版本。
- **Reason**：曾出现 `0.1.0` / `0.5` 混用，发布物名字与实际代码不一致。
- **Alternatives**：只在一处维护版本号（需要构建时注入）。
- **Rejected**：放宽测试让版本号漂移。

## D5 作者署名统一 bsaizne

- **Decision**：`LICENSE` 版权行、`pyproject.toml` 的 `authors`、README 作者段、`agent_context.__author__` 全部写 `bsaizne`。
- **Reason**：作者本人的明确要求；开源项目里署名必须准确。
- **Alternatives**：`Agent Context Manager Contributors`（原模板）。
- **Rejected**：泛化占位符（丢失真实作者）。

## D6 README 以简体中文为主，英文保留为 README.en.md

- **Decision**：`README.md` 中文，`README.en.md` 英文，两文件顶部互链。
- **Reason**：项目作者与主要使用者是中文用户；同时不放弃英文读者的可发现性。
- **Alternatives**：只保留英文（原状，作者不满意）；只保留中文（丢失国际读者）。
- **Rejected**：单一语言。

## D7 `.agent/versions/` 不进入导出，也不计入「上下文档案 tokens」

- **Decision**：`export_project` 跳过 `versions/`；`context_token_stats` 只统计 resume 真正读取的文件，archive/versions 单独计数。
- **Reason**：两者都会随使用无限增长，而 `resume` 从不读取它们；算进「上下文规模」会让这个数字失真。
- **Alternatives**：全部导出/统计。
- **Rejected**：把历史混进「新 Agent 实际加载量」。

## D8 只写 `<project>/.agent/`

- **Decision**：任何命令都不写业务代码；`init` 只额外创建一个 `AGENTS.md`（且已存在时不覆盖）。
- **Reason**：这个工具的价值是「可以放心在别人的项目里跑」，越界写入会直接毁掉信任。
- **Alternatives**：允许写项目根的 `README`/`AGENTS.md` 之外的规则文件。
- **Rejected**：任何形式的业务代码改动。
