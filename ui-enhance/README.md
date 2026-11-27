# ui-enhance · 深度美化层（2026-11-27）

本站点的 UI 增强层：玻璃导航 / 渐变 Hero / 统计数字渐变 / 卡片 hover / **三态深色切换**（light/dark/system，`assets/theme.js`，localStorage 记忆，sw.js v47）。

**上游站点仓 11-25 已迁私有**，本增强做在公开镜像快照上。合入你的站点仓：

1. `git fetch` 本仓 main；
2. 应用 `beautify-patch-for-upstream.txt`（11 个文件 diff；`assets/theme.js` 为新增文件，全文在 patch 末尾）；
3. 或整体替换 11 个文件（清单见 patch 头注释）。

全部改动 append-only（site.css 只追加、html 只插 1 行 script、sw.js 加 1 行+版本号），不碰原逻辑，可无损回退。CC BY-NC 4.0 兼容（同授权沿用）。
