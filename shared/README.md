# shared/ · 李奕波个人作品矩阵统一平台共享层

「四统一」的落地代码。10 个模块与 shell 一律复用本层，禁止各自造一套。

| 子模块 | 状态 | 职责 | 引入方式 |
|---|---|---|---|
| `config/` | ✅ 本轮新建 | 服务注册表 SERVICE_REGISTRY —— 端口的唯一真源，跨模块调用禁止硬编码端口 | Python：`pip install -e shared/config` 后 `from portfolio_config import api_url`；前端：`<script src=".../shared/config/services.js">` 后用 `CP.apiUrl(id, path)` |
| `ui-kit/` | ✅ 本轮新建 | 统一设计系统：设计令牌 + 共享组件样式 + 前端运行时 | 页面依次引入 `tokens.css` → `components.css` → `ui-kit.js` |
| `auth/` | ✅ 本轮新建 | 共享鉴权：纯标准库 HS256 令牌签发/校验，认证统一 | `pip install -e shared/auth` 后 `from portfolio_auth import issue_token, verify_token` |
| `llm-gateway/` | ✅ 既有 | 统一 LLM 网关：多端点故障转移 + 成本统计 + 无 Key mock 降级 | `from llm_gateway import chat_completion_json, GatewayConfig` |
| `logging/` | ⛔ 未实现 | 结构化日志 + trace_id（规范规划项，本轮未落地） | — |

## config · SERVICE_REGISTRY

- **真源**：`config/services.json`（10 个模块的 host / api_port / web_port / api_prefix / route / layer / icon）。
- **前端镜像**：`config/services.js` 由 `python config/build_js.py` 从真源生成，**不要手改**。
- Python API：`service_url(id)`、`api_url(id, path)`、`port(id, which=)`、`route_path(id)`、`by_layer()`、`get(id)`。
- 自检：`PYTHONPATH=shared/config/src python -m portfolio_config.registry`。

端口一览（改端口只改 services.json）：P01=18082 / P02=8000(API)+3001(Web) / P03=8030 /
P04=8041 / P05=8770 / P06=8060 / P07=8070 / P08=8080 / P09=8090 / P10=8101。

## ui-kit · 设计系统

- `tokens.css`：配色（深色默认 `#0B0E14` 底 / `#3370FF` 单一强调色，含浅色主题覆盖）、间距（8pt 栅格）、圆角、字体、阴影、布局尺寸、动效令牌。所有类名/变量以 `cp-` 前缀。
- `components.css`：布局骨架（sidebar/topbar/content）、卡片、智能体矩阵卡、统计块、按钮、徽章/标签、表格、表单、空态/骨架屏、响应式断点。
- `ui-kit.js`：主题切换、侧栏折叠/移动端抽屉、shell↔模块 postMessage 桥（`CP.initModuleBridge` / `CP.postToParent`）、SERVICE_REGISTRY 助手、内联 SVG 图标（`CP.icon(name)`）。
- 模块页面接入：`<body class="cp-app" data-cp-module="p06">`，引入三个文件即自动获得统一主题与（在 iframe 内时）桥接。

## auth · 统一鉴权

- HS256 令牌，结构与标准 JWT 兼容。密钥从环境变量 `CP_AUTH_SECRET` 读取。
- API：`issue_token(subject, roles, ttl=)`、`verify_token(token)`、`require_role(token, role)`、`parse_bearer(header)`。
- **红线**：未设置 `CP_AUTH_SECRET` 时用本地演示弱密钥并在 stderr 告警，**生产必须显式配置强密钥**。
- 自检：`PYTHONPATH=shared/auth/src python -m portfolio_auth.token`。

## 已知边界（诚实标注）

- `shared/logging` 尚未实现，各模块仍用自带日志；trace_id 贯穿未统一。
- 三个新共享包目前以源码路径（PYTHONPATH / `pip install -e`）方式复用，尚未在 10 个模块的 `.venv` 里全部安装接入；接入进度见各模块 README 与 `_evidence/`。
- auth 的跨 iframe 单点登录（shell 登录 → 令牌 postMessage 下发到各模块 → 模块校验）已提供原语（`CP.initModuleBridge` 接收 `cp:auth`、`require_role`），但各模块后端的强制校验接入是分批进行的，未接入的模块仍按其自有鉴权或无鉴权运行。
