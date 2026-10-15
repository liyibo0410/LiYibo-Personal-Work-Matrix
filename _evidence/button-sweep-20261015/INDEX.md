# 全平台按钮全量实测与监督修复 · 总索引（2026-10-15）

> **执行方式**：监督窗口派 6 路「只测不改」子智能体并行点击测试十个模块 + 统一外壳的全部可交互控件；
> 期间 3 路补测/复测（P01+P04、P02+P03 重试；P06/P07 现场竞态实验）。
> 全部结论带证据（截图/原始 JSON/网络与 console 记录）；「未测」如实列出。代码修复由监督窗口完成并逐项复验。

## 1. 各智能体报告（按模块）

| 报告 | 覆盖 | 计数（测 / 正常 / 缺陷 / 部分 / 未测） | 关键发现（已修标 ✔） |
|---|---|---|---|
| `agent1-shell.md` | 统一外壳（8070/8800） | 96 / 89 / 4（中1低3）/ 3 / 2 | **127.0.0.1 被误判为非本机 → 挂载指公网隧道 URL**（✔）；brand 兜底请求 `:8800` 公网必失败（✔）；favicon 404 |
| `agent2-p01-p04.md` | P01 + P04 | P01 20 / 14 / 6（中2低4）/ 2 / 4；P04 34 / 26 / 8（高1中1低-中2低3）/ 3 / 5 | **P04 列表强缓存 → 删除假象（✔）**；**502 页 HTML 贴进气泡（✔）**；「处理中」脏行删不掉；TTS 503 无提示；数字人 code 10005 |
| `agent3-p02-p03.md` | P02 + P03 | P02 71 / 53 / 8（**高3**中4低1）/ 2 / 8；P03 10 / 4 / 2（高1中1）/ 2 / 2 | **文案/脚本保存 100% 失败**（漏 authHeaders，待修）；合规检测接口对、UI 无（待修）；素材预览 404；P03 图表/溯源零实现 + 免责文案指向不存在组件（待修）；P03 拒答门禁实测通过（有条件） |
| `agent4-p05-p08.md` | P05 + P08 | P05 77 / 57 / 3（**高1**中1低1）/ 1 / 2（另 18 项被 P0 阻断）；P08 32 / 29 / 2（中1低1）/ 1 | **P05 四大页面 TDZ 整页打死（✔）**；写回审批单对上传件永败（待修）；P08 无开始/暂停/队列，任务即时 100%（待修/改标注） |
| `agent5-p06-p07.md` | P06 + P07 | P06 6 Tab 全点 / 缺陷 5（中1低4）；P07 全正常 / 低1 | **DuckDB 并发假 404/500（12/12 复现 → ✔ 0/12）**；同名覆盖无防呆（待定）；favicon/tailwind 提示 |
| `agent6-p09-p10.md` | P09 + P10 | P09 29 / 28 / 1（高1）；P10 25 / 11 / 10 组（**高2**中9低2 归并） | **小数据集训练 500 + 前端静默（✔）**；4 个「新增按钮」未接线（数据面已通、UI 未做，待修）；模型指标/曲线缺模拟标注等 8 组 |

> 补测/复测：`agent2` 重试与 `agent3` 二轮均写入同目录（后者覆盖 P02 全页 + P03 全部问句，含无数据拒答的 341s 完整轨迹 `q3-detail.json`）。

## 2. 监督窗口修复清单（本日，全部带复验）

| # | 位置 | 缺陷 | 修法 | 复验 |
|---|---|---|---|---|
| 1 | `shell/index.html` | `IS_LOCAL` 正则 `^(127\.…)$` 判不中 `127.0.0.1` → 本机打开时模块 iframe 全指公网，隧道一断整排白屏 | 改 `127(\.\d{1,3}){3}` 全段匹配 | 登录后实测 iframe `src=http://127.0.0.1:8060?cp-theme=light`（`监督验证-P05-外壳-20261015.json`） |
| 2 | `p05-contract-review/ui/assets/app.js` | `CFX_*` 4 个 const 声明在初始化调用之后 → TDZ ReferenceError → 大盘/工作台/规则库/孪生四页全死 | const 块上移到初始化之前 | 四页 `CR=object` 零报错：workbench 2358 字 / rules typeList=3159 / twin 7871 字（同上 JSON） |
| 3 | `p04 web/api/console_service.py` | 动态 JSON（`/search`、`/documents`…）被误加 `public,max-age=300` → 删除/刷新后浏览器复用旧列表（「删掉了行还在」「再删报文档不存在」） | 白名单化：仅静态资源与 HTML 页强缓存，其余 `no-store` | curl -D 实测：`/documents → no-store`、`/shared/* → max-age=300`（`监督验证-P04-缓存头-20261015.txt`） |
| 4 | `p04 web/page/console.html` | 切片预览翻页不封顶（1 块文档可翻到「第 6~5 块」空白页） | `previewTotal` 回填 + 边界钳制 | 服务端已吐含修复版本（标记核验） |
| 5 | `p04 web/page/{chat,console}.html` | 后端 502 时把 nginx 整页 HTML 原文贴进回答气泡 | 识别 HTML 响应 → 「服务暂时不可用（HTTP xxx）」 | 服务端已吐含修复版本（标记核验） |
| 6 | `p10 app/main.py` | `total_steps<5`（≤32 样本）时 `step % (total_steps // 5)` 除零 → 训练端点 500；空曲线再 `[-1]` IndexError | `eval_every=max(1,…)` + 空曲线守卫 + 调用处空值兜底（`final_loss=None` 有类型支持） | POST `ds-101`（22条）→ **200**（total_steps=1、curve=2）；`ds-102`（0条）→ **200**（curve=0）（`监督验证-P10-训练-*.json`） |
| 7 | `p10 web/index.html` | 训练创建失败前端完全静默（只有 `if (resp.ok)` 分支） | 非 2xx 弹 alert 并带后端 `detail` | 服务端已吐含修复版本（标记核验） |
| 8 | `p06 app/duckdb_engine.py` + `app/ingestion.py` | DuckDB 单连接无锁，FastAPI 线程池并发交错 → `/tables/{name}` 与 `/preview` 假 404/500（agent5 并发 12/12 复现，串行 12/12 全对） | `DB_LOCK(RLock)` 包住「execute+取数」；ingest 的 DROP/CREATE/INSERT 持锁 | agent5 竞态脚本复跑：矛盾 **0/12**、串行 0 失败；ingest 冒烟 3 行入库（`agent5-p06-race-experiment*.json`） |
| 9 | `shared/ui-kit/ui-kit.js` + `brand-bridge.js` | 公网访客每次页面加载都请求 `http://<IP>:8800/api/brand`（安全组挡死）→ console 持续报错 | 公网主机改走同源 `/api/brand`（8070 nginx 已反代到外壳）；本机/局域网保留 host:8800 | 两个文件服务端已吐含修复版本（标记核验） |
| — | 进程清理 | P04 在 8041 上残留双进程（绑定失败的僵进程 + 实际服务进程）；P10 亦为双进程 | 杀帧余进程 → supervisor 重启为单实例；重启 P04/P06/P10 使修复上线 | netstat 单 LISTENING（P04=51196）；`/health` 200 |

> 附注：P04 的这次重启同时让 Qoder 当日上午的 D30（`/search` 正则注入转义）/D31（`/statistics` 口径）两项"等重启生效"的修复在线上生效。

## 3. 环境事件（非代码缺陷，但与演示强相关）

- **隧道时段性中断**：09:40–10:02 公网入口整段 502（保活循环当时未在运行）；09:42–09:57 P05/P08 公网 502 集中在该窗口；10:12 后仍有零星超时（含 `/p06/api/v1/health` 单次 15s 超时后 5/5 恢复）。本地全程 200。
- **服务静默死亡无自愈**：09:41 P04 进程无 traceback 消失、09:40 前后 P02-web 消失 —— `supervisor.py` 是一次性 CLI **没有看门狗**，不自动拉起。
- **cp_mod 单值 cookie**：同一浏览器先后开两个模块会互相改写 cookie（nginx 靠它分流根级路径），并发挂载会串台。
- P06 库中留有两张他窗口测试表（`ods_dirty_probe`、`qoder_probe_ok`）与两张本次 `tmp_uitest_*` 表（无删表 UI，服务持有文件锁未强删）。

## 4. 优化建议清单（收敛版）

### P0 · 演示前建议完成（未修部分）
1. **P02 文案/脚本保存 100% 失败**（高）——`web/src/app/(app)/products/[id]/creative-plans/[planId]/main-image/update/route.ts:15-17` 与 `video-script/update/route.ts:15-17` 读商品时补 `authHeaders()`；同时把 422 `compliance_blocked` 的 hits 渲染成可见提示。（前端窗口）
2. **P02 合规检测缺 UI**（高）——引擎接口已正确（422+span+法条）；要么加只读检测面板，要么至少让保存失败展示命中词。（前端窗口）
3. **P09/P10 四个「新增按钮」接线**（高）——从 P01 导入会话 / 发起评分 / 导出低分样本 / 从 P09 拉取；对应 API 全部已就绪。（功能窗口）
4. **演示前检查单**：`python _tools\tunnel_remote.py start` 自校验 + 当场浏览器复测 8070/8090；演示结束 `stop`（弱口令暴露纪律）。
5. **服务看门狗建议**：supervisor 增加 watch/restart 循环或任务计划定期探活（今日两次静默死亡均未自愈）。

### P1 · 演示加分（未修部分）
- P01：TTS 失败给可见提示（catch 里 `errorMessage`）；数字人 code 10005 与厂商核对 appId 资源。
- P03：① 免责文案改口（或实现「溯源卡」：SQL+行数+时间范围+耗时）；② 首屏加 `/api/health` 徽标；③ 会话写 sessionStorage + 按 thread 回放；④ 无数据类问句早期短路（先 list_sql_tables 判断相关性）；⑤ `prompts.yml` 加「库内取数不得用公网数据作答」硬规则 + 剥夺该轮 tavily 路由。
- P04：① 「处理中」脏行删除兜底（Mongo 无记录时清磁盘备份并移除行）；② 无关问题先判「召回为空 → 拒答」再澄清。
- P05：① `writeback.py:ensure_instance` 在 base_url 非空时也向 `{base}/instances` 登记；② 自检「模式对照」文案改注「降级路径演练」。
- P06：① 指标卡展示口径（描述字段已有）；② 首查图表占位「图表加载中…」；③ 同名上传加二次确认或改追加模式。
- P08：任务页补「开始/暂停/继续」或明写「Mock：即时完成不产出文件」；评分明细区就近标注「能量/语速/互动为模拟值」。
- P02（非阻断）：素材预览 404（补占位图 + 同源路径）、`forbidden` 参数落地提示、生成结果来源标注、健康度 98% 改真实派生、`aria-current` 水合告警。
- P10：M1 曲线卡移出训练页容器 / M2 加训练列表端点 / M3 训练页 init 拉数据集 / M4 星标按 `measured_fields` 判定 / M5-M6 补「模拟」标注 / L2 上传弹窗文案。

### P2 · 工程与体验
- favicon 全局补齐（shell/P01/P04/P06/P07/P09/P10 均有 404）；Tailwind CDN 构建期化（低）。
- nginx：`location /` 兜底块补 `proxy_set_header Host`（本次未动服务器）；`cp_mod` 改 per-module cookie 或重定向保留 `/pXX/` 前缀（消除串台与裸请求 404）。
- 隧道：保活加"服务器侧回环实测自愈"（断链即重连，不等人）；演示页可加「链路抖动请重试」提示。
- P03 单问句时延（30s~8min）与 P06/P07 等模块的 favicon/console 清洁度。

## 5. 复跑入口

- 监督验证脚本：`_tools-agent1/_verify-fixes.js`（P05 四页 + 外壳挂载）→ `监督验证-P05-外壳-20261015.json`
- P06 竞态复现：`_scripts/agent5-p06-race.js`（前置 `Copy-Item` 保留 before 版本）
- P10 训练回归：`监督验证-P10-训练-22条-200.json` / `-0条-200.json`
- P04 缓存头：`监督验证-P04-缓存头-20261015.txt`

---

## 6. 第二波修复（2026-10-15 11:0x–11:2x，「全部修复」）——含复验

> 使用者下达「全部修复」后，监督窗口在 §2 的 9 项之外继续修复以下缺陷；每项均跑过对应回归。

| # | 位置 | 缺陷 | 修法 | 复验 |
|---|---|---|---|---|
| 10 | P02 两处 update route | **文案/脚本保存 100% 失败**（读商品漏带鉴权头 → 401 → 静默 `edit=failed`） | 补 `authHeaders()` | 路由落盘；Next dev 热编译 |
| 11 | P02 两处 update route | 合规拦截（422 hits）在页面静默丢弃 | 命中词+法条经 `reason` 参数透传，页面横幅展示 | 同上 |
| 12 | P02 product 页 / dashboard / home | 编辑结果无提示 / 「数据健康度 98%」硬编码 / `forbidden` 降级无提示 | 保存成败横幅、「在营店铺占比」真实派生、越权提示条 | 源码核验 |
| 13 | P02 api/uploads | 种子素材 `demo-oat-main-image.png` 缺失 → 预览 404（本地） | 生成占位 PNG | `GET /uploads/demo-oat-main-image.png → 200 image/png` |
| 14 | P09 web | 「从 P01 导入 / 发起评分 / 导出低分样本」三按钮缺失 | 看板页三按钮 + 完整 JS（含降级不伪造文案） | 无头检查三函数 `function`、零报错 |
| 15 | P10 web + app | 训练历史写死两条 ID；曲线卡被页面容器隐藏；数据集下拉空值静默 404；p09 回流集误标「预置」；模型指标/曲线缺模拟标注；上传弹窗文案反向；「从 P09 拉取」按钮缺失 | 新增 `GET /api/v1/training` + 前端 12 处接线 | 无头检查零报错；列表端点返回数组；P10 pytest **40 passed** |
| 16 | P06 ingestion | 同名上传静默覆盖（公网零鉴权端点可换掉核心表） | 拒绝覆盖任何已存在表（明确文案） | 重传同表 → **400**；护栏测试 **6 passed** |
| 17 | P06 web | 指标页无口径；首查图表空白（echarts 懒加载） | 口径行 + 「图表加载中…」占位 | 页面标记核验 + 无头检查 |
| 18 | P05 writeback + mock | 本地上传合同「写回审批单」永远失败（approval_http 通道从不登记实例） | mock 增 `POST /instances`；writeback 在 base 非空时同样登记 | mock 直测 `code:0`；**selftest 66/66 passed** |
| 19 | P05 selftest | 「模式对照」自检文案与运行时矛盾 | 改为「降级路径演练…运行时见工作台」 | selftest 66/66 |
| 20 | P08 web | 批量任务即时 100% 无说明；评分明细未就近标注模拟值 | 两处 Mock 说明 | 页面标记核验 |
| 21 | P03 web | 免责文案承诺不存在的「下方溯源报告」 | 改为如实口径（只读 SQL 可在思考过程核对） | 页面标记核验（Vite 热更新） |
| 22 | 全站 ×13 页面 | `/favicon.ico` 404 全站刷红 | 新增 `shared/ui-kit/favicon.svg` + 各页 `<link rel="icon">` | 两模块 `/shared` 200 + 页面标记 True |
| 23 | `_tools/supervisor.py` | 服务静默死亡无自愈（当日 P04/P02-web 各一次） | 新增 `watch` 看门狗（周期探活自动拉起；`--once` 自检） | `watch --once` 跑通 |

**复验证据（同目录）**：`监督验证-全部修复-前端无头检查.json`、`监督验证-P05-selftest-66of66.log`、`监督验证-P06-ingest-guard-pytest.log`、`监督验证-P10-pytest-40passed.log`。

**仍未做（原因如实）**：
1. P04「无关问题先拒答再澄清」—— 属拒答阈值校准，需跑评测集（沿用 `_evidence/p04/refusal-calibration.*` 那条线），本轮不盲调阈值。
2. P02 素材预览的绝对地址（`127.0.0.1:8000`）在公网访客侧会指向访客自己；「生成结果来源标注」「推送到素材中心按钮」—— 均在 3000 行的 product 页组件深处，留给前端窗口。
3. P03 健康徽标 + 会话持久化（需动 Vue 状态层）。 → **本波已修，见 §7**
4. P01 TTS 失败可见提示（P01 `App.vue` 有其他窗口热区）。
5. 服务器侧 nginx（兜底块 Host 头、`cp_mod` per-module cookie）—— 按红线需本人确认后再动。
6. P08 真正的开始/暂停/队列（本轮以如实标注代替）。

---

## 7. 第三波（2026-10-15 11:2x–11:5x，「继续」）—— 外部测试收口 + P03 三连修

### A. 收编新到证据

- **`agent2-p04-outage-20261015.md`**（agent2 补测时采集）：P04 于 09:41:04 后静默死亡（无 traceback、无监听、公网 502）。**早已处置**：10:2x 拉回 + §6-23 `supervisor.py watch` 看门狗兜底；现 15/15 在线、`/console.html → 200`。
- **`p0-recon / p1-result / p1-content-dumps / p2-result / p3-fatal / p3b-result.json`**（另一窗口 09:28–09:47 对外壳的结构化点击，11:21 拷入本目录）。逐项甄别：

  | 失败项 | 判定 |
  |---|---|
  | local-mount ×11 `frame-not-found`（p3-fatal，09:46） | **已属修复态**：当时外壳没判本地主机、拼的是公网地址，恰逢隧道 09:40–10:02 全线 502。现 `webHost()` + `IS_LOCAL`（§2-1 的 D1 修复，另窗口 11:30 又复改过）已让本机访问走本地地址（代码级核验 + D1 时 p06 iframe 实测） |
  | sidebar-mount p01/p04/p05 + sidebar-health + 主题跟随（p2，09:5x） | 撞上 P04 掉线（09:41–10:2x）与隧道 502 窗口；`GET /api/services/health` 现 10 模块全绿 |
  | brand-modal ×3 + resume-modal ×2（owner 口令通道） | **归外壳窗口**：`shell/index.html` 11:30:40 正被该窗口热改中，其自测自修热区，本窗口不碰以免冲突 |
  | `#btn-resume-settings` 不可见（p3-fatal） | 同上——该元素已不在现文件里（页面重构为 `lp-resume` 区「下载完整材料 PDF / 在线预览」） |

- **`agent3-p02-p03.md` 终版（11:21，43KB）**：81 控件 / 10 缺陷（高4·中7·低2 + 门禁 2.3 专章），编号至 164 的截图。其结论与 §2/§6 对账后见 D。

### B. 本波修复（3 项，全部复验）

| # | 缺陷 | 修法 | 复验 |
|---|---|---|---|
| 2.13 | 编排层把库内取数类问题路由到公网（AGENTS ⑩ 点名） | `prompt/prompts.yml` main_agent 增「数据取数边界」红线硬规则 + `tools/internet_search_tool.py` 增 22 词数据闸门：命中即**不出网**，回传 `error+hint` 引导改走 DB 助手 / 如实拒答（即「剥夺该轮 tavily 路由权」的确定性实现；与提示词互为双保险） | `监督验证-P03-联网路由闸门-20261015.md`：2 条数据类查询 100% 拦截（日志见 `WARNING …未出网`）、YAML 规则在位、restart 后 `/api/health ok` |
| 2.10 | P03 健康徽标缺失（后端 `/api/health` 早有 mysql/sql_guard/降级原因） | App.vue 右上常驻徽标（ok/降级/不可用/未知四态）+ 60s 刷新，title 展开明细 | `监督验证-P03-徽标与会话持久化-20261015.json`：`● 数据源就绪`、title=`MySQL 已连接 · SQL护栏 active · 端到端 verified`、零报错 |
| 2.12 | Vite HMR 热更新清空对话（实测打断过一轮） | `messages+thread_id` 落 sessionStorage、挂载恢复（F5 亦不丢）；损坏数据按空会话启动 | 同上 JSON：restoredUser/ restoredAi/ threadKept 全 `true`、msgCount=2、无 vite overlay |

### C. 附带发现

P03 的 **MySQL(3306) 数据源此刻在线**：`mysql.reachable:true`、`sql_guard:active`、`sql_execute:verified`、`degraded_reasons:[]` —— AGENTS「已知未闭环 ①」记的"MySQL 未启动"**已过时**。库内取数现在有真数据可走，2.13 的"取数只认库内"正当其时。

### D. 子智能体配额

agent3 补测会话因 **token-plan 月配额耗尽**终止（重置 2026-10-21 16:00 UTC）；其交付物已完整落盘（43KB 终版报告 + 编号至 164 的截图 + p0~p3 结构化 JSON）。**10-21 前不再派子智能体**，由本窗口直测直修。

### E. 对账后的开放清单（承接并改写 §6-仍开放）

- ✅ **本波清账**：2.10、2.12、2.13（§6 旧第 3 条划掉）
- 高：2.14 P03 图表+溯源零实现（大前端工程）；2.2 P02 合规检测面板（大前端工程）
- 中：2.4 P02 推送按钮、2.5 生成结果来源标注、2.7 公网绝对地址残留、2.8 水合告警、P01 TTS 失败提示、2.11 P03 时延（结构性，只能压不能消）
- 流程/外部：nginx 服务器侧两项（等本人确认）；P08 真队列；P04 拒答校准；外壳 brand/resume 模态 5 失败（归外壳窗口）
