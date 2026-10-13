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
- **进程托管**：`_tools/supervisor.py`（start/stop/restart/status，`--takeover` 接管手工启动的旧进程）取代「开十几个黑窗口」；日志 `_runtime/logs/`，端口仍从 SERVICE_REGISTRY 解析
- **首屏即作品集**：`shell/index.html` 的首页是完整作品集（四层模块卡带实测指标与 Mock 边界 + 闭环与 6 条 ADR + Ragas 对照 + 真实/模拟边界），**未登录即可整屏读完**，点「进入演示」才弹登录模态并回跳 —— 证据 `_evidence/shell/D13-portfolio-home.md`
- **技术选型决策记录**：`docs/adr/`（6 条 ADR + 索引）
- **全平台联调证据**：`_evidence/shell/`（登录→矩阵→挂载 P06/P07 真实截图；**D5 返工**：十项用户反馈的根因表 + 十模块挂载截图 + 品牌定制截图）；各模块证据见 `_evidence/pXX/` + `INDEX.md`

启动：`start-all.bat`（= `python _tools\supervisor.py start`），统一入口 **http://127.0.0.1:8800**。

**已知未闭环**（不要当成已完成）：① P03 问数的模型层**已真实接通**（2026-10-13 晚，根因是 `agent/llm.py` 把仓库根算成了 `projects/`、根 `.env` 从未被读到；两套百炼 Key 本身有效，详见 `_evidence/INDEX.md` D12）。全链路仍缺数据源：MySQL(3306)/RAGFlow(9380) 未启动、Tavily 仍是 mock —— 已实测到「库里没有的数据会明确拒答而非编造」；② P02 浅色态仍会被 `/`→`/login` 跳转丢掉 `?cp-theme`，需 Cookie 供 SSR 读取；③ **P02 的 `api/scripts/test_gateway_integration.py` 曾把 `sk-sp-` 真实 Key 写成源码字面量并已推到 GitHub**，本轮已改为读 `.env`，但**历史里的 Key 仍在公网，需在百炼控制台吊销重发**；④ **没有任何公网入口**：面试官远程访问尚未打通 —— 本机「快车VPN」TUN + fake-IP 对 `argotunnel.com` 做 TLS 中间人，cloudflared 边缘握手 `EOF`、访客侧 530。隧道工具 `_tools/tunnel.py`（start/stop/status，自校验通过才发链接）与网关侧 `public_urls` 下发均已就位，只差网络放行；当前仅同 WiFi 可用 `http://192.168.1.112:8800`。三条出路见 `_evidence/shell/D13-portfolio-home.md` 第三节。

> 历史：Phase 0 体检见 `00-总纲/05-项目体检报告.md`；进度全量登记在 `_evidence/INDEX.md`（D1~D10）。
