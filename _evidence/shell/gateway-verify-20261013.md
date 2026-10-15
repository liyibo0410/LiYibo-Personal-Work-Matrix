# 李奕波个人作品矩阵统一平台外壳（shell gateway）· 验证记录

- **验证时间**：2026-10-13
- **验证方式**：单次调用内后台起 `shell/serve.py`（端口 8800）→ curl 打全套接口 → 浏览器（browser-use）走登录→首页→挂载黄金路径 → take_snapshot / evaluate_script 取证
- **环境**：Windows / Python 3.11 / 纯标准库 http.server；`CP_AUTH_SECRET=shell-selftest-secret-2026`

## 一、网关接口（curl 实测）

| 接口 | 结果 |
|---|---|
| `GET /api/health` | `{"ok": true, "service": "shell-gateway"}` |
| `POST /api/auth/login`（owner/owner123） | `ok=True`，返回用户「张总」roles=['owner'] + HS256 令牌（头 `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9`，JWT 兼容） |
| `POST /api/auth/login`（错误密码） | `{"ok": false, "error": "用户名或密码错误"}`（401） |
| `GET /api/auth/verify`（Bearer 令牌） | `ok=True sub=owner roles=['owner']` |
| `GET /api/registry` | `version=1.0 services=10`（SERVICE_REGISTRY 全量） |
| 静态：`/`（index.html） | 200，16743B |
| 静态：`/shared/ui-kit/{tokens.css,components.css,ui-kit.js}` | 全部 200 |
| 静态：`/shared/config/services.js` | 200 |

## 二、目录穿越防护（--path-as-is 实测）

| 请求 | 结果 |
|---|---|
| `/shared/../../.env` | **403**（解析后越出 base，被拦截） |
| `/../shared/auth/pyproject.toml` | **403** |
| `/shared/config/services.json`（合法） | 200 |

## 三、前端黄金路径（browser-use 结构取证）

1. **登录页渲染**：品牌「李奕波个人作品矩阵 / Li Yibo's Personal Portfolio」、账号+密码表单、登录按钮、5 个演示账号 chip（owner/ops/legal/sales/admin）—— take_snapshot 确认。
2. **真实登录**：填 owner/owner123 → 提交 → 网关签发令牌 → 进入应用视图（非 mock，走 /api/auth/login 真实校验）。
3. **登录后首页（智能体矩阵）**：
   - 侧栏按层分组导航：应用层 L3（P01/P02/P05/P09）、能力层 L2（P03/P04/P07/P08）、模型层 L1（P10）、数据层 L0（P06），每项带 `#/workspace/{route}` 链接；
   - 顶栏：菜单按钮、标题「工作台」、主题切换、用户徽章「张总 owner」、退出按钮；
   - 主区：标题「AI 智能体矩阵」+ 平台叙事 + 统计条（10 AI智能体 / 4 架构分层 / 1 旗舰模块 / /workspace/* 统一入口）+ 数据流闭环（P06→P04/P07→P01/P02→P09→P10↺）+ 按层分组的 10 张智能体卡片（名称/描述/状态/路由）。
4. **hash 路由 + iframe 挂载**（导航到 `#/workspace/data-platform`，evaluate_script 取证）：
   - `hash=#/workspace/data-platform`
   - `topbar=数据中台`（标题从 SERVICE_REGISTRY 解析）
   - `frameSrc=http://127.0.0.1:8060/`（**端口由注册表解析，非硬编码**）
   - `homeHidden=true / frameViewHidden=false`（正确切换到挂载区）
   - `activeNav=p06`（导航高亮同步）
   - `loadingHidden=true`（iframe onload 已触发 → P06 内容真正载入）
   - `iframeTitle=cross-origin(blocked)`（shell:8800 ↔ P06:8060 跨源，浏览器正确隔离 DOM；postMessage 为合规通信通道）

## 四、结论

外壳网关 + 统一登录（真实 HS256 令牌）+ SERVICE_REGISTRY 端口解析 + 智能体矩阵首页 + 分层导航 + hash 路由 + iframe 挂载 **全链路跑通**，跨源隔离正常。

## 五、未覆盖 / 边界（诚实标注）

- 本次仅起了 P06 一个真实模块验证挂载；其余 9 个模块的 iframe 挂载逻辑相同（URL 由注册表解析），但未逐个起服务实测。
- 截图未取（browser-use 视口不可用 `NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`），改用 take_snapshot（可访问性树）+ evaluate_script（DOM 状态）结构取证。
- postMessage 主题/令牌下发已在 ui-kit.js 与 shell 双侧实现，但**各模块前端尚未接入 ui-kit.js 的 `initModuleBridge`**（属任务 #29 模块前端重构范围），故本轮未验证模块侧接收。
- 演示账号密码写在 `shell/serve.py` 且已文档化，仅供本地联调；生产须接真实用户体系并设强 `CP_AUTH_SECRET`。
