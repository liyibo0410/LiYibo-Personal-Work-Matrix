# Agent5 · P06 数据中台 + P07 AI 素材中心 —— 按钮功能全量点击测试报告

> 只测不改：本报告仅记录实测，未修改任何代码/配置/服务；所有临时数据用 `tmp_uitest_*` / 「UI测试-可删」命名并已尽量清理（见 §5）。
> 报告：`_evidence/button-sweep-20261015/agent5-p06-p07.md`；截图：同目录 `agent5-*.png`；脚本：`_scripts/`；原始结果 JSON：`agent5-p06-public-results.json`、`agent5-p06-local-results.json`、`agent5-p07-public-results.json`、`agent5-p06-race-experiment.json`、`agent5-p07-422-probe.json`。

## 0. 测试时间与入口 / 方法声明

- **测试时间**：2026-10-15 09:28 – 10:45（本机时钟；期间 **10:39:08 另一窗口对 P06 竞态做了修复、10:40:07 重启服务**，本报告区分「修复前实测」与「修复后复验」）。
- **入口**：
  - P06 公网 `http://39.96.200.45:8090/p06/` ｜ 本地等价 `http://127.0.0.1:8060/`
  - P07 公网 `http://39.96.200.45:8090/p07/` ｜ 本地等价 `http://127.0.0.1:8070/`
- **修复时间线（本窗口实测+复核）**：10:24:29 本窗口跑「修复前」竞态实验（12/12 轮有错，快照见 `agent5-p06-race-experiment-before-fix.json`）→ 10:39:08 另一窗口提交 `app/duckdb_engine.py` 修复（`threading.RLock` 把 execute+fetch 包成原子）→ 10:40:07 P06 重启（新进程）→ 10:40:14 修复方复跑 12 轮 **0 错** → **本窗口 10:45 自验：竞态实验 2×12 轮 0 错 + UI「查看」15/15 全过**。本报告所有「查看」失败均属 10:39 修复前行为。
- **公网链路实测事实（如实归并）**：
  1. 服务器 nginx 按 **Referer** 把根路径 `/api/v1/*` 分流到对应模块（无 Referer 直接 curl → 404；带 `Referer: …/p06/` → 200。P06/P07 页面内 fetch 均为绝对 `/api/v1/*`，靠 Referer 才能落地）。
  2. **时段性抖动**：公网第二轮（09:47–49）批量 502（nginx HTML 上游断）；P07 补充测试 10:29 公网 `page.goto` 60s 超时 → 立刻转本地全过。监督窗口并入数据点：公网 `GET /p06/api/v1/health` 曾一次 15s 超时（curl 000），随后同 URL 5/5 返回 200（0.13–0.17s）；本地同路径恒 200（约 3ms）；同期公网 `/p06/api/v1/dashboard`、`/p09/api/v1/leaderboard` 均 200 —— 与隧道时段性抖动同源，**非应用缺陷**。
  3. 凡公网异常项均已按纪律改本地复测，并在表中注明「公网抖动 / 本地复测」。
- **各模块窗口（本机时钟）**：P06 公网 09:28–09:33 / 09:47–09:49；P06 本地 09:51–10:17（看门狗兜底）→ 10:25–10:39（全量复跑）→ 10:34–10:39（补尾）→ 10:45（修复后复验）；P07 公网 10:14:49–10:17:00；P07 本地补充 10:30；P07 后端 422 探针 10:26。
- **工具声明**：本会话桌面浏览器工具不可用（`browser.disconnected`，多次重试无效），改用 **Playwright 1.64.1 + 系统 Chrome（headless）** 直连页面逐一点击；console 报错、网络 4xx/5xx/超时、API 响应体全量采集。P06/P07 用独立浏览器上下文（不存在 cp_mod 串台问题）。
- 每个 Tab 均打开截图；全流程操作清单见 §1/§2。

## 1. P06 数据中台 · 控件表（按页面）

实际 Tab（6 个）＝ **总览 / 数据表 / 指标 / 质量 / 血缘 / 接入**。**未见「查询」Tab**（任务假设的 7 个 Tab 中此项不存在；SQL 查询只有接口 `POST /api/v1/query`，已用无害载荷直接验证，见下）。页面**没有独立「刷新」按钮**（切 Tab 会重新拉取）。

### 1.1 总览（dashboard）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 总览 | 整页加载 | 打开入口 URL | 首屏渲染、数据加载 | HTTP 200；badge「14 张表 / 3.24万 行」；4 张统计卡；token 样式生效（bg=rgb(245,247,250)） | 正常 | `agent5-01-p06-public-dashboard.png`、`agent5-01-p06-local-dashboard.png` |
| 总览 | 侧栏导航 ×6 | 逐一点击 | 6 个 Tab 均可切换并加载 | 6/6 正常；data-page=[dashboard,tables,metrics,quality,lineage,ingest] | 正常 | 两张 dashboard 截图 + 后述各页截图 |
| 总览 | 核心指标概览卡（7 项） | 读取文本 | GMV/订单/转化率/客单价/退货率/UV/PV 齐全 + 口径标注 | **7 项齐全**（成交总额 3.60万 ▲33.87%｜订单量 133 ▲25.47%｜转化率 0.44% ▲46.67%｜客单价 270.36 ▲6.69%｜退货率 20.30% ▲53.67%｜独立访客数 3.04万 ▼15.17%｜页面浏览量 9.69万 ▼28.12%）；**卡片只有 名称/最新值/趋势，无口径文字**（接口 `metric.description` 有口径但页面未展示） | 部分（无口径标注） | `agent5-01-p06-public-dashboard.png`、`agent5-01-p06-local-dashboard.png` |
| 总览 | 健康环 + 数仓分层 | 读取文本 | 健康分与分层显示 | 健康分 29；分层 ODS 6 / DWD 2 / DWS 2 / ADS 2（14 表时点） | 正常 | 同截图 |
| 总览 | `/api/v1/dashboard` 响应字段 | 审阅响应 | 应有 degraded/mock/口径字段（若存在如实记录） | 字段=`table_count,total_rows,layers,health{score,total_checks,passed,warned,failed},metrics[7 项 code/name/unit/latest/avg/trend]`；**无 metrics_source / degraded / mock 标注字段** | 正常（如实记录） | `agent5-p06-public-results.json` → apiDumps |

### 1.2 数据表（tables）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 数据表 | 进入 Tab | 点击 | 表列表加载 | 15 张表（公网第二轮时点，含他窗口遗留 `ods_dirty_probe`、`qoder_probe_ok` 与我方 2 张 tmp） | 正常 | `agent5-02-p06-public-tables-list.png` |
| 数据表 | 分层筛选 select | 依次选 ODS/DWD/DWS/ADS/全部 | 仅显示对应分层 | 公网：8/3/2/2/15 行，分层唯一对应；本地：7/3/2/2/14 行 | 正常 | `agent5-03-p06-public-tables-filter-ods.png` |
| 数据表 | 「查看」按钮 ×N | 逐行点击→详情→「关闭」 | 每张表都能打开详情并关闭 | **公网第二轮（修复前）7/15**：失败 8 张（`dwd_customer_profile`、`dws_daily_shop`、`ods_products` 为接口假 404；`dwd_order_detail`、`ods_stores`、`ods_traffic`、`qoder_probe_ok`、`tmp_uitest_agent5_csv` 为 502=隧道）；**本地复跑（修复前）：成功 5/14**（失败 9 张：ads_key_metrics、ads_product_ranking、dwd_customer_profile、dws_daily_product、dws_daily_shop、ods_customers、ods_dirty_probe、ods_orders、tmp_uitest_agent5_csv，接口 404/500 与 200 并存）；**修复后 10:45 复验：15/15 全过**（见 §3-D1） | 缺陷（D1 竞态，已修复） | `agent5-04-p06-public-table-detail-first.png`、`agent5-95-p06-postfix-table-detail.png` + JSON |
| 数据表 | 「关闭」按钮 | 每次详情后点击 | 面板收起 | 正常收起（循环内 15+ 次点击均生效） | 正常 | 交互循环记录 |
| 数据表 | 补尾独立复跑（修复前） | 每张表 2 次重试 | —— | 成功 4/14（与上一轮并发进行、负载更高） | 缺陷（D1） | `agent5-p06-local-tail-results.json` |

### 1.3 指标（metrics）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 指标 | 进入 Tab | 点击 | 下拉含 7 指标 | 7 项：成交总额/订单量/转化率/客单价/退货率/独立访客数/页面浏览量 | 正常 | `agent5-05-p06-public-metrics-gmv.png`、`agent5-06-p06-public-metrics-pv-month.png` |
| 指标 | 指标 select ×7 | 逐一选择 | 7 项可选 | 7/7 正常 | 正常 | JSON |
| 指标 | 粒度 select | day/week/month | 切换重查 | 三种粒度均出数（return_rate=week、traffic_pv=month 实测） | 正常 | `agent5-06-p06-public-metrics-pv-month.png`、`agent5-05-p06-local-metrics-pv-month.png` |
| 指标 | 日期输入 ×2 | 用默认 2024-07-01～2024-09-30 | 参与查询 | 正常（非法日期未测，见 §5） | 正常 | JSON |
| 指标 | 「查询」按钮 ×7 | 对每项指标点击查询 | 摘要卡 + 图表 | 7/7 HTTP 200 摘要卡更新；**公网首次查询（gmv）时 canvas=0（echarts 1MB 懒加载未就绪），后续均 canvas=1**；**本地复测：7/7 canvas=1，单项出图 27–206ms**（首查 gmv 206ms） | 部分（公网首查图表迟滞，见 D3；本地无此问题） | JSON + 截图 |
| 指标 | `/metrics/{code}/query` 响应 | 审阅 | —— | 含 `metric.description`（口径）但 UI 不展示 | 说明 | JSON |

### 1.4 质量（quality）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 质量 | 「运行质量检查」按钮 | 点击 | 运行并展示 | 公网：HTTP 200，状态「检查完成 - 140 项」，健康评分 29（通过 127/警告 1/失败 12），明细 140 行，toast 同值；**本地复测：HTTP 200，「检查完成 - 148 项」，健康评分 29（通过 135/警告 1/失败 12），明细 148 行**（项数差异来自表数时点不同） | 正常 | `agent5-07-p06-public-quality-results.png`、`agent5-06-p06-local-quality-results.png` |

### 1.5 血缘（lineage）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 血缘 | 进入 Tab | 点击 | 渲染图谱+明细 | 公网：节点 rect=11、连线 path=11、SVG 高≈718px、明细 11 行；节点文本 ODS/DWD/DWS/ADS/customers/orders/products/stores/traffic/customer profile…可读；本地复测：节点 11/连线 11/明细 11（一致） | 正常 | `agent5-08-p06-public-lineage.png`、`agent5-07-p06-local-lineage.png`（均全页） |
| 血缘 | 图可交互性 | 检查节点事件 | 注：现状为静态渲染 | 节点无 onclick、cursor=auto —— **静态可读图，非可交互**；无工具提示（如实记录，非缺陷） | 正常（现状） | JSON |

### 1.6 接入（ingest）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 接入 | CSV 拖拽区点击 | 点击 | 弹文件选择器 | filechooser 事件触发（本地、补尾两次复验均触发） | 正常 | JSON |
| 接入 | CSV 上传（表名 tmp_uitest_agent5_csv, ODS） | 选文件→自动上传 | 成功入库并记日志 | 公网：✓成功 3 行 4 列；本地：✓成功 3 行 4 列（同名重传替换，内容一致） | 正常 | `agent5-10-p06-public-ingest-csv-done.png` |
| 接入 | JSON 上传（表名 tmp_uitest_agent5_json, DWD） | 同上 | 成功入库 | 公网：✓成功 3 行 4 列；本地：✓成功 3 行 4 列 | 正常 | `agent5-11-p06-public-ingest-json-done.png` |
| 接入 | 表名非法护栏 | 表名=`tmp_uitest_bad name!` 上传 | 拒绝并明确说明 | 拒绝：日志/toast 原文「非法表名：'tmp_uitest_bad name!'。只允许字母、数字与下划线，须以字母或下划线开头，最长 64 字符」；库中未建该表 | 正常（护栏有效） | `agent5-12-p06-public-ingest-invalid-rejected.png` |
| 接入 | 临时表可见性 | 回表列表核对 | 两张 tmp 在列 | 公网第二轮 DOM+API 双核对 `hasCsv=true,hasJson=true,hasBad=false,total=15`；本地：DOM+API 双核对 `hasCsv/hasJson=true,hasBad=false,total=14`（当次时点） | 正常 | `agent5-13-p06-public-tables-tmp-visible.png`、`agent5-12-p06-local-tables-tmp-visible.png` |
| 接入 | （风险观察）同名上传 | 代码级审阅 | —— | 上传实现是 `DROP TABLE IF EXISTS`+`CREATE`：**对已存在表名上传会直接覆盖**（纪律禁止，未实测）；建议上传前加确认或改为插入模式 | 低（潜在） | `app/ingestion.py` |

### 1.7 SQL 查询（无 UI 入口 → 接口直验）
> 页面无「查询」Tab（见 §1 首段）；为避免覆盖/破坏，仅用接口 + 无害载荷验证护栏。
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 查询(API) | `POST /api/v1/query` 合法 SELECT | `SELECT COUNT(*) AS cnt, ROUND(SUM(gmv),2) AS gmv FROM ads_key_metrics` | 返回结果集 | `{cnt:92, gmv:3312522.61}`，count=1，truncated=false | 正常 | JSON |
| 查询(API) | 护栏：多语句夹带 DROP | `SELECT 1; DROP TABLE tmp_uitest_guard_probe` | 拦截+说明 | HTTP 400「不允许多条语句：请用分号分隔的单条查询」 | 正常 | JSON |
| 查询(API) | 护栏：文件读取函数 | `SELECT * FROM read_text('.env')` | 拦截 | HTTP 400「该语句包含不被允许的 DuckDB 能力：read_text」 | 正常 | JSON |
| 查询(API) | 未建表复核 | `GET /api/v1/tables` | 无害载荷未动库 | `tmp_uitest_guard_probe` 不存在 | 正常 | JSON |
| 查询(API) | 本地复验 | 同三条载荷 | 同上 | 合法=200/code0；多语句=400 拦截；read_text=400 拦截；探针未建表（false） | 正常 | `agent5-p06-local-results.json` |

## 2. P07 AI 素材中心 · 控件表（按页面）

页面（5 个）：**概览 / 素材库 / 以文搜图 / AI 生成 / 效果关联** + 素材详情（深链 `#asset/{id}`）。**无 ingest 相关 UI**（按要求未触碰 `POST /api/v1/ingest`）。
顶部 LLM 状态徽章实测：初始 `LLM 已接入 · qwen3.8-max │ 网关调用 0 次 · 0 tokens · mock 0`，全程结束累计 `4 次 · 3304 tokens · mock 0`（calls_by_model：qwen3.8-flash 3、qwen3.8-max 1）。

### 2.1 概览
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 概览 | 整页加载 | 打开 /p07/ | 徽章+指标卡+6 图 | HTTP 200；4 张指标卡（素材总数 17 / 已关联投放 8 / 总花费 ¥45,200 / ROI 10.25x）；**6/6 图渲染出 canvas**（echarts 懒加载成功） | 正常 | `agent5-01-p07-public-dashboard.png`、`agent5-02-p07-public-dashboard-charts.png` |
| 概览 | 演示数据边界文字 | 读取 | 应如实标注 demo 边界 | 页面含「演示数据边界：source=demo 的 12 条素材…」 | 正常 | 同截图 |
| 概览 | `/llm/status` | 审阅 | 真实/降级状态 | `configured=true, model=qwen3.8-max, reason=""`；cost 含 mock_calls 计数 | 正常 | JSON |

### 2.2 素材库
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 素材库 | 进入 Tab | 点击 | 上传表单+网格 | 共 17 条；自动打标勾选=**true**，标签文案「上传后自动智能打标（LLM 真实调用，约 2-8 秒）」 | 正常 | `agent5-03-p07-public-library-initial.png` |
| 素材库 | 名称/类型/标签/描述 | 填入「UI测试-可删-夏季控油防晒喷雾主图」等 | 可编辑 | 正常 | 正常 | `agent5-04-p07-public-library-form-filled.png` |
| 素材库 | 文件选择（真实文件） | 选 `AST-18356A.png`(4.8KB) | 显示已选+大小 | 「已选：AST-18356A.png（5 KB）」 | 正常 | 同截图 |
| 素材库 | 「上传入库」 | 点击（自动打标=LLM） | 201 入库；真实打标或如实降级 | **201；AST-6A7FAE；tag_source=llm（真实未降级）**；tags=[防晒喷雾,主图,控油,清爽,夏季]；真实宽高 640×480；file_url=/api/v1/assets/AST-6A7FAE/file；toast「已入库 AST-6A7FAE · 打标来源 llm」 | 正常 | `agent5-05-p07-public-library-upload-done.png` |
| 素材库 | 上传校验 | 不填名称点上传 | 前端提示 | toast「请填写素材名称」 | 正常 | JSON |
| 素材库 | 搜索按钮 | 关键字「防晒」 | 过滤 | 共 3 条，显示 3 条 | 正常 | JSON |
| 素材库 | 类型筛选 select | type=copy + 关键字 | 组合过滤 | 0 条（符合当前库） | 正常 | JSON |
| 素材库 | 重置按钮 | 点击 | 恢复全量 | 18 条（17+新传 1） | 正常 | JSON |
| 素材库 | 素材卡片点击 | 点击第一张卡 | 进详情 | `#asset/AST-C9B117`，详情含「返回素材库」按钮（本地补充测试通过；公网 10:29 抖动转本地） | 正常 | `agent5-90-p07-local-card-click-detail.png` |

### 2.3 以文搜图
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 以文搜图 | 进入 Tab | 点击 | 检索框+示例词+边界说明 | 渲染正常；含「文本层检索，不是 CLIP 多模态向量检索」声明 | 正常 | `agent5-06-p07-public-search-initial.png` |
| 以文搜图 | 搜索（命中） | 点示例词「夏天清爽的防晒霜」 | 命中相关素材 | refused=false；total=5；threshold=0.18；**含刚上传的 AST-6A7FAE**（另有种子 AST-007 防晒霜对比图 0.461） | 正常 | `agent5-07-p07-public-search-hit.png` |
| 以文搜图 | 搜索（拒答） | 点示例词「库里没有的无人机航拍素材」 | 明确拒答 | **refused=true**；reason「最高相关度 0.049 低于阈值 0.18…拒答而非返回弱相关结果」；页面显示「库内无匹配素材（已拒答）」+ 切词 | 正常 | `agent5-08-p07-public-search-refused.png` |
| 以文搜图 | 类型筛选 + TopN | type=image + Top10 | 过滤生效 | refused=false；total=4；返回均为 image | 正常 | JSON |
| 以文搜图 | 匹配解释 | 读取结果卡 | 命中理由可读 | 每卡有「相关度 %」+「词→命中的字段」徽章 | 正常 | `agent5-07-p07-public-search-hit.png` |

### 2.4 AI 生成
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| AI 生成 | 进入 Tab | 点击 | mock 边界说明可见 | note：「图片类型为程序化绘制的投放规格卡片，不是 AI 出图」 | 正常（标注诚实） | `agent5-09-p07-public-generate-initial.png` |
| AI 生成 | 提示词/类型/风格/保存勾选 | 填入并切换 | 可编辑 | 正常 | 正常 | 同截图 |
| AI 生成 | 「生成」（图片/mock 路径，保存勾选） | prompt=618大促主图规格卡 | 生成+UI 标注 mock+入库 | source=**programmatic**；badge「**程序化占位图**」；note「非真实 AI 出图：Pillow 按投放规格绘制的占位卡片…」；已保存 AST-9FB3F0 | 正常（mock 标注诚实） | `agent5-10-p07-public-generate-image-mock.png` |
| AI 生成 | 「生成」（文案/真实 LLM，保存不勾选） | prompt=防晒喷雾卖点文案 | 真实 LLM 或如实降级 | source=**llm**；model=qwen3.8-max；latency≈19004.8ms；tokens 285+620；badge「LLM 真实生成」 | 正常 | `agent5-11-p07-public-generate-copy-real.png` |
| AI 生成 | 生成结果的保存链接 | 检查 | 可跳详情 | 已保存时出现「已保存到素材库：AST-xxxx」链接（同 showAssetDetail 路径，经深链/卡片点击两路验证） | 正常 | JSON |

### 2.5 效果关联（投放效果报表）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 效果关联 | 进入 Tab（大盘对照） | 点击 | 真实调用 P06 指标且有来源标注 | `platform_metrics.available=true`；`source_url=http://127.0.0.1:8060/api/v1/metrics/summary`；`fetched_at=2026-10-15T10:15:35`；对照卡=成交总额/转化率/客单价/独立访客数；页面展示目标 URL+取数时间 | 正常（真实跨模块） | `agent5-12-p07-public-report-platform-metrics.png` |
| 效果关联 | 平台筛选 select | 选「抖音」 | 过滤 | 接口 total=4 且 platform 全为 douyin；页面计数一致 | 正常 | `agent5-13-p07-public-report-filter-douyin.png` |
| 效果关联 | P06 不可用时行为 | 代码/文案审阅 | 不编造数字 | 不可用时展示「P06 指标不可用，此处不编造大盘数字。原因：…」 | 正常（如实） | `agent5-p07-sweep.js` 结果 JSON |
| 效果关联 | 报表行点击 | 点第一行 | 进素材详情 | `#asset/AST-009`（本地补充通过） | 正常 | `agent5-p07-local-extra.json` |

### 2.6 素材详情（#asset/{id}）
| 页面 | 控件 | 操作 | 预期 | 实际 | 判定 | 证据 |
|---|---|---|---|---|---|---|
| 素材详情 | 深链打开+文件预览 | `#asset/AST-6A7FAE` | file 接口真实出图 | `img` naturalWidth>0；src=/api/v1/assets/AST-6A7FAE/file；标签徽章含 tag_source；投放 0 条 | 正常 | `agent5-14-p07-public-asset-detail.png` |
| 素材详情 | 「← 返回素材库」 | 点击 | 回素材库 | 通过（本地补充） | 正常 | `agent5-p07-local-extra.json` |
| 素材详情 | 「录入投放数据」 | 点击 | 展开表单 | 表单展开（默认值 50000/3000/120/2000/15000） | 正常 | JSON |
| 素材详情 | 「提交」（合法） | 曝光 40000/点击 2500/转化 100/花费 1500/收入 12000 | 201 入库+表格出现 | HTTP 201；投放行=1 | 正常 | `agent5-15-p07-public-asset-perf-saved.png` |
| 素材详情 | 「提交」（非法：点击>曝光） | 曝光 100/点击 900 | 被拒绝 | 本次点击先命中**前端**校验（表单重渲染后店铺为空 → toast「请填写店铺名」）；**后端 422 另行 API 直验通过**：`422 "Value error, 点击数不能大于曝光数"`（探针资产 AST-E90F71 已删） | 正常（两路都拦） | `agent5-p07-422-probe.json` |
| 素材详情 | 「重新打标（覆盖）」 | 点击 | LLM 或如实兜底 | tag_source=**llm**（8453.5ms）；tags 更新含 UI测试 | 正常 | `agent5-16-p07-public-asset-retag.png` |
| 素材详情 | 「追加」 | 点击 | 标签合并 | tag_source=llm；tags=[UI测试,主图,夏季,控油,清爽,美妆,防晒喷雾] | 正常 | JSON |
| 素材详情 | 「删除 AST-6A7FAE」 | 点击+确认弹窗 | 删素材+文件+投放关联 | confirm 文案「确认删除素材 AST-6A7FAE？文件与投放关联会一并删除。」；DELETE 200；`file_removed=true`；随后 API 复核 **404**（含生成卡 AST-9FB3F0），库内「UI测试-可删」0 条 | 正常 | `agent5-17-p07-public-asset-deleted.png` |

## 3. 缺陷明细（现象/复现/证据/严重度/疑似根因/建议修法）

**严重度口径**：高=主流程断/白屏/数据破坏；中=功能随机失败/信息缺失但可重试；低=观感与边界。
> P0 级（主流程断/白屏/数据被破坏）：**无**。两模块主链路可用；未发现种子数据被破坏。

### D1【中】P06「查看」表详情偶发失败 —— 并发假 404/500（app 层竞态）· **已于 10:39 修复，本窗口 10:45 复验通过**
- **现象（修复前）**：点表行「查看」随机弹 toast「加载表详情失败」（详情面板不出现）；接口 `/tables/{name}`（有时是 `/preview`）返回 404 `Table 'x' not found` 或 500（纯文本 Internal Server Error），而**同一张表的配对接口同一时刻返回 200**（自相矛盾）。
- **复现（修复前，均为 10:39 前实测）**：
  1) UI 复现：公网 09:47 第二轮 7/15（失败 8：`dwd_customer_profile/dws_daily_shop/ods_products` 假 404 + `dwd_order_detail/ods_stores/ods_traffic/qoder_probe_ok/tmp_uitest_agent5_csv` 隧道 502）；本地 10:25–10:39 复跑成功 **5/14**（失败 9：ads_key_metrics、ads_product_ranking、dwd_customer_profile、dws_daily_product、dws_daily_shop、ods_customers、ods_dirty_probe、ods_orders、tmp_uitest_agent5_csv —— 同对请求 404/500 与 200 并存）；本地补尾独立复跑（10:34–10:39，与上一轮并发进行）成功 **4/14**。
  2) 定向实验（决定性）：`_scripts/agent5-p06-race.js` 按前端同款并发对（info+preview）连打 12 轮：**12/12 轮至少一个响应是错的**（10:24:29：8 轮互斥 404、1 轮 info=500、3 轮反向 404）；**串行对照 12/12 全 200**。快照 `agent5-p06-race-experiment-before-fix.json`。
- **修复与复验（10:39–10:45：另一窗口修复 + 本窗口独立复验）**：10:39:08 `projects/p06-data-platform/app/duckdb_engine.py` 加 `threading.RLock`（execute+fetch 原子化，ingestion 写序列同样持锁）；10:40:07 P06 服务重启；10:40:14 修复方复跑 0/12；**本窗口 10:45 自验：竞态实验 2 轮各 0/12（`agent5-p06-race-postfix-1/2.json`）+ UI「查看」15/15 全过（`agent5-p06-postfix-ui.json`、`agent5-95-p06-postfix-table-detail.png`）**。
- **证据**：race 4 份 JSON、`agent5-p06-public-results.json`、`agent5-p06-local-results.json`、`agent5-p06-local-partial.json`（+`_agent5-p06-local-partial-analysis.txt`）、`agent5-p06-postfix-ui.json`。
- **疑似根因**：`app/duckdb_engine.py` 全局单例连接被 FastAPI 线程池并发使用；`conn.execute()+fetchone()` 非原子、非线程安全，两请求交错会取到对方/过期的结果集 → `table_exists` 假 0 → 404；交错下抛错 → 500。前端 `showTableDetail` 的 `Promise.all` 让这对请求每次都并发，放大了触发率。
- **建议修法（已落地）**：给 duckdb 单连接加 `threading.RLock` 把 execute+fetch 包成原子操作（10:39 的修复即此实现）。

### D2【低】P06 指标卡无「口径」标注
- **现象**：核心指标概览 7 项齐全，但卡片只见 名称/最新值/趋势；口径（如「支付用户数 / 独立访客数」）在接口 `metric.description` 里而页面未展示。
- **复现**：总览页读卡文本即可（`agent5-01/02` 截图）；对照 `GET /api/v1/metrics` 的 description 字段。
- **证据**：截图 + JSON。
- **疑似根因**：前端未渲染 description（无字段缺失问题）。
- **建议修法**：卡片加悬浮/角标展示口径，或指标页标题区展示 description。

### D3【低】P06 指标页首查图表迟滞（echarts 懒加载）
- **现象**：公网首次点「查询」后摘要卡即时更新，但图表 canvas 迟到（首次检查 canvas=0；随后查询恢复 canvas=1）。属加载时序（echarts 1MB 仅到时才注入），非数据问题。
- **复现**：公网第一轮 gmv 首查（截图 05 为空图区）；**本地复测 7/7 即时出图（单项 27–206ms，canvas 立刻=1）**——即这是公网隧道 + 1MB echarts 首包的加载时延，非代码缺陷。公网第二次打开后图表正常。
- **证据**：`agent5-05-p06-public-metrics-gmv.png`（首查空图区）+ JSON。
- **疑似根因**：`ensureEcharts()` 懒加载与首查并发，加载完成前图区为空。
- **建议修法**：查询按钮旁加「图表加载中…」占位，或进入指标 Tab 即预热 echarts。

### D4【低】P06 无 SQL 查询 UI 入口（与任务预期不一致）
- **现象**：实测 6 个 Tab，无「查询」页；SQL 能力仅 `POST /api/v1/query` 接口层可用（护栏已验有效，见 §1.7）。
- **复现**：页面 nav DOM 与源码 `web/index.html` 均无查询页。
- **证据**：`agent5-01` 截图侧栏；JSON。
- **疑似根因**：功能未做 UI 或按设计不给前端开放。
- **建议修法**：若演示脚本需要 SQL 入口，可加一个简单查询页复用现有护栏；否则在 README 明确「仅接口开放」。

### D5【低（潜在中）】P06 同名上传会覆盖既有表
- **现象（代码级）**：ingest 实现为 `DROP TABLE IF EXISTS` + `CREATE`，对已存在表名上传 = 直接覆盖（无误触，纪律禁止未实测）。
- **复现**：阅读 `app/ingestion.py:115-116/200-201`；无 UI 防呆。
- **证据**：源码路径 + 上传页交互截图。
- **疑似根因**：演示用简化实现。
- **建议修法**：同名上传前加二次确认，或改为追加/版本化表名。

### D6【低】P07 两个观感小项（合并）
- ① favicon.ico 在 公网/P07/本地 均 404（浏览器默认请求；P06 同）→ 控制台红字 1 条。② 控制台 1 条 tailwind 提示「cdn.tailwindcss.com should not be used in production」（用的是本地 vendor 的同一构建）→ 仅提示。均不影响功能。建议：补一个 favicon；如介意可将 Tailwind 改构建期产物。

### 环境备注（非缺陷）
- 公网隧道 09:47–49 批量 502、10:29 goto 超时、监督窗口 15s 单次超时 —— 均为链路抖动；本地恒稳。已在 §0 如实归并。
- `ods_dirty_probe`、`qoder_probe_ok` 表非本次创建（他窗口测试遗留），未触碰。

## 4. 未测清单（含原因）
1. P06 拖拽 **drop** 上传（只测了点击→文件选择器；drop 分支同函数，未用 drag 事件模拟）。
2. P06 大文件（>100MB）/空 CSV/坏编码拒绝 —— 未造大样本（磁盘紧张+无必要）。
3. P06 **覆盖已有表**上传 —— 纪律禁止（D5 仅代码级观察）。
4. P06 指标**非法/边界日期**（如 end<start、未来日期）—— 未测（默认值流程外）。
5. P06 列统计接口 `/{col}/stats`、`POST /api/v1/lineage` —— 无 UI 入口、不在本轮点击范围，未单独调。
6. P07 视频上传、视频脚本生成、风格 select 全枚举、Top20 档、多租户权限 —— 未测（时间/无素材；文案+图片两条真实路径已覆盖生成链路）。
7. P07 深色主题/外壳 iframe 内表现 —— 未测（外壳登录链路不在本窗口范围）。
8. 两模块后端鉴权 —— 已知「模块后端零鉴权」（平台级已知项），未重复验证。

## 5. 数据清理与备注
- **P06**：新建 `tmp_uitest_agent5_csv`（3 行）、`tmp_uitest_agent5_json`（3 行）两张临时表；**无删表 UI/接口**，服务进程持有 DuckDB 文件锁，未冒险直改库文件 → **两张 tmp 表留在库中**（命名自带标识，建议平台加清理脚本）。非法名 `tmp_uitest_bad name!` 被拒、未建表；护栏载荷未建 `tmp_uitest_guard_probe`。后续复跑对同名 tmp 表为「同名重传替换」，行数一致（3 行），未产生额外实体。
- **P07**：测试资产 **AST-6A7FAE**（上传）、**AST-9FB3F0**（生成）、**AST-E90F71**（422 探针）**已全部删除**（DELETE 200 + file_removed=true + API 复核 404）；库内「UI测试-可删」0 条；种子数据未动。
- 截图 16+ 张见本目录 `agent5-*.png`；脚本副本 `_scripts/`。
- 环境注：库内 `ods_dirty_probe`、`qoder_probe_ok` 等他窗口测试产物非本次创建、未触碰；修复窗口 10:39–10:40 对 P06 的改动（加锁+重启）非本窗口所为，本报告仅记录与复核。

## 6. 附：原始结果文件索引（时间均为本机 2026-10-15）
| 文件 | 内容 |
|---|---|
| `agent5-p06-public-results.json` | P06 公网第二轮（09:47–49）全量 step/console/网络/API 转储（含竞态与隧道 502 混杂） |
| `agent5-p06-local-results.json` | P06 本地全量复跑（10:25:44–10:39:33，47 steps）——修复前，竞态失败 5/14 |
| `agent5-p06-local-tail-results.json` | P06 本地补尾独立复跑（10:34–10:39，指标/质量/血缘/接入/SQL/查看 4/14）——修复前 |
| `agent5-p06-local-partial.json` + `_agent5-p06-local-partial-analysis.txt` | P06 本地第一次尝试被看门狗兜底的部分结果（10:17，竞态重灾区）+ 分析 |
| `_agent5-p06-local-run2-analysis.txt` | 本地全量复跑（上表第 2 行）的步骤/控制台/非 2xx 汇总 |
| `agent5-p06-race-experiment-before-fix.json` | **修复前**竞态实验快照（10:24:29，12/12 轮有错；原文件由修复方保留为此名） |
| `agent5-p06-race-experiment.json` | **修复后**竞态实验（10:40:14，修复方复跑：0/12） |
| `agent5-p06-race-postfix-1.json` / `-2.json` | **修复后**本窗口独立复验（10:45，各 0/12） |
| `agent5-p06-postfix-ui.json` + `agent5-95-p06-postfix-table-detail.png` | **修复后** UI「查看」复验（15/15 全过） |
| `agent5-p07-public-results.json` | P07 公网全量（10:14:49–10:17:00，26 steps） |
| `agent5-p07-422-probe.json` | 后端 422 直验（10:26）+ 探针资产清理 |
| `agent5-p07-local-extra.json` | 卡片点击/返回素材库/报表行点击（10:30，公网抖动时本地补充） |
| `_scripts/*.js` | 可重跑脚本：P06 sweep / P07 sweep / race / 422 探针 / P07 extra / P06 tail / postfix-ui |