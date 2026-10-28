# TODO

## P0 — 当前

- [ ] 无。v0.9.0 与档案刷新均已提交并推送（`4ba0200`、`3a53e3e`），工作区干净。

## P1 — 下一步

- [ ] F1：L2 逐行溯源（blame）。在 `versions.py` 增加 blame，并在 Changes 页展示。
- [ ] 把 `agent_prompt_template` 补进 `docs/ARCHITECTURE.md`（README 已有说明）。
- [ ] 确认 GitHub Release v0.9.0 是否已发布（本地包已在 `D:\vibe code`）。
- [ ] 下次发版 v0.10：版本号 +1（pyproject / `__version__` / GUI spec）、onedir 打包、产物放 `D:\vibe code`。
- [ ] 每次主仓库改动完成后，按 D9 同步 C 盘镜像并更新其 `.agent` 档案。

## P2 — 以后

- [ ] GUI 支持非 Windows 平台（当前 GUI 仅 Windows；CLI 已支持 macOS / Linux）。
- [ ] 大差异时给 Changes 页加上下文折叠（只显示改动附近 N 行）。
- [ ] 在 macOS / Linux 上验证 GUI 打包链路。
- [ ] 视需要补中文版 CHANGELOG / CONTRIBUTING（用户当前表示不需要）。

## Blocked

- [ ] 修复本机 `%TEMP%`（需要管理员权限执行 takeown + icacls，并清理 13 个不可访问的 `_MEI*`）。
