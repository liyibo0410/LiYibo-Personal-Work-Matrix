# AGENTS.md · 面试作品集平台

> 本文件供 Qoder / Claude Code / CodeBuddy 等 AI 编程工具自动加载。
> 详细规范见 `.qoder/rules/`，架构总纲见 `00-总纲/00-总纲提示词.md`。

## 这是什么

一套面向 **AI 应用开发 / AI-FDE 岗位** 的作品集工程：由**十个 AI 能力模块**组成一套统一的「AI 电商运营中台」。

**核心叙事**：底层数据中台统一口径 → 模型层沉淀微调能力 → 能力层提供 RAG / 研究 / 素材 / 切片 → 应用层组装成客服 / 运营 / 合同 / 考核四条业务线，并通过数据回流形成闭环。

## 公司设定（虚构，用于业务建模）

- 名称：**云枢智能（CloudPivot）** —— 面向品牌电商与 MCN 的 AI 原生运营服务商
- 客户：年 GMV 千万至十亿级的品牌方、代运营公司、直播机构
- 设定规模：服务 200+ 店铺，日均会话 50 万条 → 因此**多租户 / 多店铺 / 高并发 / 数据合规**是每个模块都要体现的设计约束

## 十个模块

| 层 | 编号 | 模块 | 目录 | 来源 |
|---|---|---|---|---|
| L3 应用 | P01 | AI 电商客服 | `projects/p01-ai-customer-service` | 改造 customer-service-backend |
| L3 应用 | P02 | 电商运营助手 ★旗舰 | `projects/p02-ecommerce-ops-assistant` | 改造 ecommerce-operation-assistant |
| L2 能力 | P03 | NL2SQL 问数 | `projects/p03-deep-research` | 改造 deep_agent_search |
| L2 能力 | P04 | RAG 知识库 | `projects/p04-rag-knowledge-base` | 改造 knowledge_base |
| L3 应用 | P05 | 合同审批系统 | `projects/p05-contract-review` | 改造 合同审批系统-李奕波 |
| L0 数据 | P06 | 数据中台 | `projects/p06-data-platform` | 新建 |
| L2 能力 | P07 | AI 素材中心 | `projects/p07-ai-asset-center` | 新建 |
| L2 能力 | P08 | 直播切片 | `projects/p08-live-clip` | 新建 |
| L3 应用 | P09 | AI 销售考核 | `projects/p09-ai-sales-assessment` | 新建 |
| L1 模型 | P10 | 模型微调平台 | `projects/p10-model-finetune` | 新建 |

## 四条不可动摇的规矩

1. **真跑通 > 好看**：声称完成的功能必须有真实证据（启动日志 / 接口返回 / 截图 / 测试输出），落到 `_evidence/`。跑不通就写"未跑通 + 原因"。
2. **不造假**：不编造数据、指标、性能数字。允许本地 mock，但必须在 UI 与 README **双处标注** mock 边界。
3. **不动原件**：`D:\software\PycharmProjects\` 下的**原始项目禁止删除或覆盖**，改造一律复制到本项目 `projects/` 后重构。
4. **高风险先问**：删除 / 覆盖 / 批量重命名 / 对外发布，必须先红色警告 → 列受影响路径 → 等确认。

## 环境要点

- Python 包管理**强制 uv**（`pyproject.toml` + `uv.lock`），禁用裸 `pip install`
- 模型调用一律走 `shared/llm-gateway`，配置从根目录 `.env` 读取，**禁止硬编码 Key**
- 本机：Windows + RTX 4060 8GB + 16GB 内存 + **磁盘紧张**（D 盘仅剩 ~64G，重物走 E 盘）
- Docker 可用；Node 22 可用；ffmpeg 9.0 可用

## 当前阶段

十个模块 + 统一外壳 + 作品集门户已全部构建，并合并为一套「云枢智能」统一平台：

- **集成形态**：微前端外壳（`shell/` 网关 8800 提供登录/分层导航/主题/iframe 挂载），非单体合并 —— 见 `docs/adr/0001`
- **端口单一真源**：`shared/config/services.json`（SERVICE_REGISTRY），跨模块调用与挂载一律解析于此 —— 见 `docs/adr/0002`
- **统一认证**：外壳用 `shared/auth` 签发 HS256 令牌、postMessage 下发；P02 保留自身 Cookie RBAC（有意识例外）—— 见 `docs/adr/0003`
- **跨模块真实取数**：P02→P06 指标、P09→P01 会话，正常路径真实调用 + 降级路径不伪造 —— 见 `docs/adr/0004`
- **设计系统全局统一**：`shared/ui-kit/tokens.css` 单一真源；静态模块运行时挂 `/shared`，构建型模块（P01/P02/P03）构建期内联令牌 + 主题桥 —— 见 `docs/adr/0005`。**P05 已从「自带调色」改为消费 ui-kit**（`/shared/*` 只读映射 + `cp:theme` 桥 + 强调色回指 `--cp-brand`），浅色态与外壳一致
- **品牌位可自定义**：`shared/config/brand.json` 是公司名称/logo 的唯一真源，经 `GET/POST /api/brand` 读写（写需登录令牌，读开 CORS 只为兜底），外壳 ⚙ 上传 logo（自动缩到 128px）后全站生效。取数链是「页面声明的同源 `/shared/config/brand.json` → 外壳网关 `GET /api/brand`」，网关端口来自注册表顶层 `gateway.web_port`；静态模块用 `data-cp-brand="company|name_en|logo|..."` + `CP.applyBrand`/`cp:brand` 下发，构建型模块（P01/P02/P03）用 `shared/ui-kit/brand-bridge.js` 或 Next 侧的 `useBrand()`，自带产品标识的模块用 `data-cp-brand-logo-src`（自定义 logo 优先、否则回自带图）—— 证据 `_evidence/shell/D16-brand-fullsite.md`
- **侧栏状态点是真探活**：`GET /api/services/health` 对各模块端口做 TCP 探测（由网关代查避开 CORS），绿=在监听、灰=未启动；未启动的模块在挂载区给出可执行的启动命令而不是一个空白 iframe
- **进程托管**：`_tools/supervisor.py`（start/stop/restart/status，`--takeover` 接管手工启动的旧进程）取代「开十几个黑窗口」；日志 `_runtime/logs/`，端口仍从 SERVICE_REGISTRY 解析。**服务标志位必须是 `CREATE_NO_WINDOW`**：Win11「默认终端 = Windows Terminal」在 `DETACHED_PROCESS` 下照样给每个服务开一个黑窗口（实测 10 服务 = 11 窗口）
- **静默启动与桌面应用**：`_tools/launcher.py`（pythonw 静默编排 start/stop/status/open，命名互斥量防连点，只在服务没起来时弹一个框）；`_tools/make_desktop_app.py` 从 `brand.json` logo 生成多尺寸 ico、用系统自带 `csc.exe` 编 `_tools/dist/云枢智能.exe`（41,984 字节，零额外运行时），并在桌面写「一键启动 / 停止服务 / 服务状态」三个快捷方式。起业务进程前会先确保 **P01 的 MySQL 容器**（`customer-service-mysql`，宿主 3307，端口从那份 compose 解析）在监听，需要时拉起 Docker Desktop —— 少了它客服页就是「加载历史消息失败 / 加载订单列表失败」（D21）。实测双击后**控制台窗口 0 个**、门户 +2s、15/15 在线 +12s —— 证据 `_evidence/shell/D20-silent-launch-desktop-app.md`；使用说明见 `docs/使用手册-静默启动与桌面应用.md`
- **P07 素材中心已补成全链路可演示**（2026-10-14）：后端拆成分层 + prompt 版本化，智能打标经 `shared/llm-gateway` 真实调用（凭证不齐退回词表并标注），检索改为中文 n-gram + 同义归一 + 字段加权带拒答（Recall@5 0.05 → 1.0），上传读真实宽高、`GET /api/v1/assets/{id}/file` 可预览、删除连带文件，生成物可入库，报表真实调用 P06 大盘指标，并开放 `POST /api/v1/ingest` 供 P02 推送。图片仍是**程序化规格卡不是 AI 出图**、检索仍是**文本层不是 CLIP 向量**，两处边界写进接口与页面 —— 证据 `_evidence/p07-ai-asset-center/`（7 张截图 + 2 份评测 + 68 passed）
- **首屏即作品集**：`shell/index.html` 的首页是完整作品集（四层模块卡带实测指标与 Mock 边界 + 闭环与 6 条 ADR + Ragas 对照 + 真实/模拟边界），**未登录即可整屏读完**，点「进入演示」才弹登录模态并回跳 —— 证据 `_evidence/shell/D13-portfolio-home.md`
- **技术选型决策记录**：`docs/adr/`（6 条 ADR + 索引）
- **全平台联调证据**：`_evidence/shell/`（登录→矩阵→挂载 P06/P07 真实截图；**D5 返工**：十项用户反馈的根因表 + 十模块挂载截图 + 品牌定制截图）；各模块证据见 `_evidence/pXX/` + `INDEX.md`

启动：桌面「**云枢智能 一键启动**」图标（静默零窗口，门户就绪自动开浏览器），或 `start-all.bat`（= `python _tools\supervisor.py start`，会开一个进度窗口）；统一入口 **http://127.0.0.1:8800**。图标/程序丢失或仓库搬家后重建：`python -X utf8 _tools\make_desktop_app.py`。

**已知未闭环**（不要当成已完成）：① P03 问数的模型层**已真实接通**（2026-10-13 晚，根因是 `agent/llm.py` 把仓库根算成了 `projects/`、根 `.env` 从未被读到；两套百炼 Key 本身有效，详见 `_evidence/INDEX.md` D12）。全链路仍缺数据源：MySQL(3306)/RAGFlow(9380) 未启动、Tavily 仍是 mock —— 已实测到「库里没有的数据会明确拒答而非编造」；② ~~P02 浅色态会被 `/`→`/login` 跳转丢掉 `?cp-theme`~~ **已修复**（`web/src/app/layout.tsx` 改从 Cookie `cp_theme_v2` 读主题供 SSR，`src/middleware.ts` 在重定向里显式带 `cp-theme`，2026-10-14 复核）；③ **P02 的 `api/scripts/test_gateway_integration.py` 曾把 `sk-sp-` 真实 Key 写成源码字面量并已推到 GitHub**，本轮已改为读 `.env`，但**历史里的 Key 仍在公网，需在百炼控制台吊销重发**（只有账号本人能做）。~~文档区仍含明文 Key 待脱敏~~ **已更正**（2026-10-14 D24 实测）：对全部 git 跟踪文件跑长 Key 正则 **0 命中**，`00-总纲/26` 与 `09` 号文里那两处分别是被截断的 17 字符前缀和 `sk-sp-...` 占位 —— 这项待办可以划掉；`p03/_site_8120/` 四个 HTML 里 8 处真实 Key 已就地替换为占位符（该目录本就 gitignore、未入库，未删文件）；④ ~~**没有任何公网入口**：面试官远程访问尚未打通~~ **已打通**（2026-10-14 起用「SSH 反向隧道 + 服务器 nginx 路径分流」；**但不是常态在线** —— 2026-10-15 09:40 实测 `http://39.96.200.45:8070` 与 `http://39.96.200.45:8090/p06/` 可正常返回，**09:54 同一批入口复测全部 502**（服务器 nginx 在、上游隧道已断），逐条记录见 `docs/assets/github/online-demo.md`；演示前需 `tunnel_remote.py start` 自校验后才会通）。cloudflared 那条路仍不通 —— 本机代理（现记录为 FlClash，早先写作「快车VPN」）的 TUN + fake-IP 对 `argotunnel.com` 做 TLS 中间人，cloudflared 边缘握手 `EOF`、访客侧 530；给 `argotunnel.com` 加一条 DIRECT 规则（属改本机配置，需本人操作）是唯一未验证出路，`trycloudflare` 路线则必须继续走代理，三条出路见 `_evidence/shell/D13-portfolio-home.md` 第三节。**演示安全**：公网入口用的就是本地种子弱口令账号，而 `_tools/tunnel_remote.py` **无自动超时/停机制**，忘记 `stop` 就是持续暴露公网。同 WiFi 仍可用 `http://192.168.1.112:8800`；⑤ **P09「与人工评分一致性报告」尚未出具** —— 假人工分（AI 分 + 随机噪声）已删除，真人盲评评分台与 Kappa 口径已就位，等真人评满 ≥5 条才出数，见 `_evidence/p09-ai-sales-assessment/INDEX.md`；⑥ **P10 微调门禁四项全空**（真实训练 / loss 曲线 / 前后评测对比 / OpenAI 兼容接口调通），接口里无测量来源的数字已清空，按红线 8 保持「明确未完成」，方案见 `00-总纲/07-P10微调算力方案.md`；⑦ P01 门禁点名的 50 并发压测仍无工具与数据，全平台首页已如实写「未做并发压测（无 P95 / 错误率）」；⑧ **P01 只剩一条 P0 未闭环**：~~知识检索 `knowledge/providers.py:171-192` 是恒返回「未检索到」的 TODO stub（`knowledge/seed/` 是空目录）~~ **已实装**（`FAQProvider` + `knowledge/seed/faq.json`，命中不足即如实拒答，P01 62→73 passed，见 `_evidence/p01-ai-customer-service/pytest-20261014-knowledge-retrieval.log`）；「负面情绪自动建单转人工」**整链不存在**（全仓无 sentiment / 建单代码，只有 `human_handoff` 流程），注册表三条 desc（p01/p03/p08）与 README 第五/七章（2026-10-15）均已按实测改口，评测脚本仍待补；⑨ **P08 直播切片仍是纯内存 mock**：ffmpeg 一次都没调用、无上传入口、不产出任何切片文件，打点的 energy/speech_rate/interaction 来自 `hash(text)` 伪随机，`_evidence/p08-live-clip/` 零截图 —— 门禁「端到端出片 + 前后对比」不成立；⑩ **P03 门禁的「生成图表 + 带溯源报告」零实现**，且无数据源时不拒答反而转公网找替身数据（修法已写明：`prompts.yml` main_agent 加硬规则 + 编排层剥夺该轮 tavily 路由权）；⑪ **四统一只落地一半**：认证只有网关校验（P04/P06/P07/P08/P09/P10 后端零鉴权，且 8060/8070/8090/8800 绑 `0.0.0.0`），LLM 网关只有 P02/P07 走（P01/P03/P04/P05 各自直连模型），`shared/logging` 不存在（trace_id 只有 P07 有）；⑫ **ADR-0001 写的统一入口 `/workspace/{route}` 实测 404** —— 真实入口是 hash 路由 `#/workspace/{route}`（十条挂载本身全部正常）。本轮 10 组缺陷的现象/根因/复验见 `_evidence/D24-全平台回归与缺陷修复.md`。

- **首屏与传输层已按实测加固**（2026-10-14 D24）：网关改 **HTTP/1.1 keep-alive**（含 `timeout=30` 回收空闲连接、以及不读请求体分支的排空/断链修正），探活结果加 **30 秒缓存** —— 此前 HTTP/1.0 每资源新建连接 + 每 6 秒 14 次 TCP 探活，把本机临时端口堆出 **387 个 TIME_WAIT**，导致浏览器 `ERR_NO_BUFFER_SPACE` **随机丢掉 `tokens.css`**（丢了整站就塌回浏览器默认样式）；修后稳态约 56 个。**没有**用 `SO_LINGER(1,0)` 发 RST 把它压到 0 —— 那个方案跑了半小时后 P10 的 uvicorn `accept` 循环崩过一次（`WinError 64`），无法排除相关，服务稳定性优先于端口数字好看，`probe_port` 里已写明这段取舍。第三方库（echarts / chart.js / marked / highlight.js / tailwind）全部落到 `shared/vendor/`（1.8 MB，经各模块既有 `/shared` 挂载直接可用）：原先六个静态模块首屏要等公网 CDN **3.9~8.8 秒**，与「本机实跑」矛盾；顺带修好 P04 从未生效的语法高亮（原先引的是 highlight.js 的 CommonJS 构建，`window.hljs` 恒 undefined）。令牌密钥改为**缺 `CP_AUTH_SECRET` 时按进程随机生成**（原常量写在公开源码里，实测可自签 admin 令牌；代价是网关重启后需重新登录），品牌写接口加 `require_role(admin)`。P06 查询端点新增白名单护栏 `app/query_guard.py`（实测拦掉 `SELECT 1; DROP TABLE` 与 `read_text('.env')` 两条载荷，且 `WITH`/`replace`/字面量分号不误伤）。全平台 **705 passed / 0 failed**（**D24 基线**；2026-10-14 当晚四个切片再加 P01 62→73 · P02 171→178 · P09 51→55 · P10 31→35，合计 **731 passed**，README 第六章表与本口径一致，逐行可用对应 `_evidence/<模块>/pytest-*.log` 复算），见 `_evidence/D24-全平台回归与缺陷修复.md` 与 `_evidence/regression-20261014-pytest.log`

> 历史：Phase 0 体检见 `00-总纲/05-项目体检报告.md`；进度全量登记在 `_evidence/INDEX.md`（D1~D24）。
>
> **证据可复核性**（2026-10-14 修）：`.gitignore` 的全局 `*.log` 曾把 `_evidence/` 下 53 份运行日志
> （pytest 输出、启动日志、跨模块调用日志）全部挡在仓库外 —— 远端只剩结论、无可复核证据。
> 现已加 `!_evidence/**/*.log` 例外；新增证据一律落 `_evidence/pXX/` 并登记进该目录 `INDEX.md`。
