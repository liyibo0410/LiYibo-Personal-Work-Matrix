# portfolio（对外静态作品集站）· 证据索引

| 证据文件 | 证明的功能 | 结果 |
|---|---|---|
| `live-before-20261014.png` | **修复前**公网站点的真实渲染：`https://cloudpivot-portfolio-b6qrn9o3mtx.qoder.zone/` 是旧深色版，且带 `+25.7% / +24.5% Answer Relevancy/Correctness 提升`（D5-B01 返工已推翻的结论）、GitHub 与「下载简历」都是死链 `#`、作者写成「2026 届」 | ✅ Edge 无头真实截图（问题取证） |
| `static-site-top.png` | **重建后**站点的真实渲染：浅色 + 单一品牌蓝、十大模块卡带实测指标与 Mock 边界、统计条 556/10/4/6、真实截图已加载 | ✅ Edge 无头真实截图 + DOM 探针 |

## 重建做了什么（2026-10-14）

- `01-portfolio/index.html` 重写为与外壳作品集首页同口径：hero → 统计条 → 十大模块卡（截图 + 技术栈 +
  实测指标 + **Mock 边界**）→ 数据流闭环 + 6 条 ADR → 可复核评测（含 P04 Ragas 本地/云端对照表）→
  真实/模拟边界 → 关于作者。
- 去掉 Tailwind CDN 与 `../shared/*.js` 依赖，只用 ui-kit 的令牌与组件类（ADR-0005 单一真源）。
- 新增 `_tools/build_portfolio.py`：把 `@import` 的 `tokens.css` / `components.css` **递归内联**成
  自包含产物 `01-portfolio/dist/index.html`（49.4 KB）。原因：站点独立发布时 `../shared/` 不存在 ——
  实测旧发布页 `GET /shared/ui-kit/tokens.css` → **404**，访客打开就是裸样式。
- 十张模块截图为**当前代码真实渲染**（浅色态、经统一外壳挂载），落在 `01-portfolio/dist/img/p01..p10.png`，
  由 `_tools/shot.py --shell-login` 无头 Edge 采集。

## 数字口径

- **556** = 十模块 pytest 实跑通过数（P01 62 · P02 162 · P03 61 · P04 23 · P05 46 · P06 44 ·
  **P07 68** · P08 30 · P09 34 · P10 26，采集 2026-10-12 ~ 10-14）。
  README 第五节的表仍写 P07 18 / 合计 506 —— 那是 P07 于 10-14 重做**之前**的数，
  新数见 `_evidence/p07-ai-asset-center/pytest-20261014.log`。**README 待同步**，本页不沿用旧值。
- 删掉了旧页的 `+25.7% / +24.5% 提升`（该对比建立在断崖量纲缺陷之上，方向都可能是反的）与
  `180 Ragas 评测指标`、`99+ 令牌` 这类无法复核的表述；改为直接给 Ragas 原始数值表。
- 「200+ 店铺 / 50万 日均会话」这类**虚构公司设定**不再当指标展示，并在页尾明确标注它是业务建模设定。

## 诚实边界

- **尚未发布**：`dist/index.html` 只在本地 `python -m http.server` 下验证过渲染与图片解析，
  公网仍是旧的深色版。发布是对外动作，等使用者确认后才做。
- 页面明确写了「十个模块跑在本机、未做公网部署」，不放会 502 的假演示链接。
- P07 的截图来自并行会话 10-14 的重做版本；若该模块继续变动，截图需重取（`_tools/shot.py` 一条命令）。
