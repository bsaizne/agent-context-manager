# TODO

## P0 — 当前

- [ ] 无。v0.8.0 已发布在 GitHub，CI 全绿；没有必须立刻做的事。

## P1 — 下一步

- [ ] L2 逐行溯源：在 `versions.py` 增加 blame（遍历版本链，标出每行首次出现的时间），GUI 的 Changes 页展示。
- [ ] 下次小版本（v0.9）：四处版本号 +1（pyproject / `__version__` / 两个 spec）、onedir 打包、产物放 `D:\vibe code`、用 `gh_release.py` 发 GitHub Release。
- [ ] 视需要补中文版 CHANGELOG / CONTRIBUTING（用户当前表示不需要）。

## P2 — 以后

- [ ] GUI 支持非 Windows 平台（当前 GUI 仅 Windows；CLI 已支持 macOS / Linux）。
- [ ] 大差异时给 Changes 页加上下文折叠（只显示改动附近 N 行）。
- [ ] 在 macOS / Linux 上验证 GUI 打包链路。

## Blocked

- [ ] 修复本机 `%TEMP%`（需要管理员权限执行 takeown + icacls，并清理 13 个不可访问的 `_MEI*`）。不阻塞 onedir 产物，但会让所有 onefile 程序在这台机器上启动失败。
