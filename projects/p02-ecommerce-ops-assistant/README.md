# 电商运营助手 · 云枢智能（CloudPivot）作品集版

> **本目录是作品集模块 P02**，属于「云枢智能」虚拟企业架构的 L3 应用层。
> 下面的原始 README 保留自源项目，便于对照。

## 改造说明（作品集要求）

| 项 | 内容 |
|---|---|
| **源项目路径** | `D:\software\PycharmProjects\ecommerce-operation-assistant` |
| **原件状态** | **不删除、不覆盖**（改造只在本目录进行） |
| **复制方式** | robocopy 单向复制，排除 `.git` / `venv` / `node_modules` / `__pycache__` / `.next` |
| **复制结果** | 35.5 MB / 400 文件 |
| **复制日期** | 2026-10-12 |
| **本次阶段** | D2 —— 跑通原始版本（**不改业务逻辑**） |

### 本地启动（已验证）

```bash
# 后端（SQLite 离线模式，无需 MySQL/Redis/PostgreSQL）
cd api
uv sync
.venv/Scripts/python.exe scripts/run_local_dev.py     # http://127.0.0.1:8000/docs

# 前端
cd web
npm install
npm run dev -- -p 3001        # http://127.0.0.1:3001（端口取自 SERVICE_REGISTRY）
```

> 用 `127.0.0.1` 访问是必须的：Next 16 的 dev server 默认只放行 `localhost` 来源的
> `/_next/*`，`next.config.ts` 已把 `127.0.0.1` 加进 `allowedDevOrigins`；
> 换成别的域名/IP 访问要一并加进去，否则 JS chunk 会被判跨站返回 403，
> 页面有样式但没有水合 —— 图表一张都不画。

### 已验证结果（2026-10-12）

- 后端：uvicorn 3 秒就绪；`/health` 200；登录 200（JWT）；无 token 访问 `/api/v1/auth/me` → 401；OpenAPI 78 路径
- 前端：Next.js 16.3.1 (Turbopack) 4.4 秒 Ready；`/` `/login` `/agent` `/imports` `/settings` 全部 200
- 证据：`_evidence/p02/验收报告.md`

### 商品池支持删除（2026-10-14）

此前商品池**只有增改查、没有删除**（后端无 `DELETE` 路由，列表行也没有删除按钮）。本次补齐：

- 接口：`DELETE /api/v1/products/{product_id}` → 204；需编辑权限（老板/运营/美工），客服 403，
  未登录 401，跨 Workspace 或不存在 404。
- 级联范围：SKU 与库存档案/流水、平台映射、竞品与监控快照、创意方案、生成任务、素材、
  推广链接与点击、经营数据、复盘、广告建议与实验、诊断、公开链接解析任务随商品一并删除。
- **保留**：`agent_runs` / `agent_approvals` 只把 `product_id` 置空。Agent 运行与人工审批是审计事实，
  且 `agent_approvals.run_id` 没有外键级联，连带删除会触发约束错误。
- 入口与确认方式：商品池列表行、工作台首页商品池行、商品详情页头部各有一个「删除」入口（只读角色不渲染），
  点进 `/products/{id}/delete` 是**服务端渲染的两步确认页** —— 上面列出这次会连带清除的真实数量，
  按下「确认删除商品」才 POST `/products/{id}/delete/confirm` → 回跳 `/products?product=deleted`。
  不用 `window.confirm()`：统一外壳把模块挂在 `sandbox` iframe 里，缺 `allow-modals` 时 `confirm()`
  直接返回 `false`，依赖它的按钮会「点了没反应」（外壳本次已补该项）。
- 证据：`_evidence/p02/D23-商品池删除.md`、`product_delete_live.log`、`pytest-20261014.log`（166 passed）、
  删除后只读 SQL 复核子表与全库孤儿行均为 0、两步链路含「取消」分支的零 JS 实测。
- **未验证**：店铺删除仍是 `window.confirm()` 写法（本次只给它补了外壳 `allow-modals`），
  「在外壳 iframe 里点店铺删除能弹窗」没实测；PostgreSQL 侧也未实机复跑，本机 P02 用 SQLite。

### 改造清单（对照 `AGENTS.md`）

- [ ] A. 认证与权限验收（四角色 + 403 证据）
- [ ] B. 合规词与极限词检测（核心卖点）
- [ ] C. 广告投放 A/B 实验扩展
- [ ] D. 内容生产 + 推送 P07
- [ ] E. 数据看板接 P06 指标 API
- [ ] F. 工程与质量（llm-gateway 接入 / 评测 / 测试覆盖率 / 深色化 / Compose）
- [ ] 补 `/stores`、`/products` 列表页（源项目缺失）

---

# 电商运营助手（源项目 README，保留原文）

> 基于 FastAPI + LangGraph + Next.js 的电商运营 AI 助手，覆盖商品诊断、创意生成、素材生产、竞品监控、库存建议与经营复盘全链路。

## 项目简介

电商运营助手面向电商运营团队，将"数据采集 - AI 生成 - 媒体任务 - 人工审批 - 系统交付"串成一条完整的自动化链路。后端以 FastAPI 为核心，结合 LangGraph 实现多 Agent 编排与受控工具调用；前端基于 Next.js 提供可视化工作台。支持 Docker Compose 一键部署，兼顾本地开发（SQLite 离线模式）与生产环境（MySQL + PostgreSQL + Redis）。

## 核心功能

| 模块 | 说明 |
|------|------|
| 商品诊断 | 将商品资料转化为结构化诊断结论 |
| 竞品分析 | 竞品资料管理、定时监控、快照对比 |
| 创意策划 | 主图方案、视频脚本、标题与详情页方案生成 |
| 图片/视频生成 | 对接 DashScope / 火山引擎等供应商，异步生成并落库 |
| 库存建议 | 基于库存与销量数据，提供补货/清仓建议 |
| 经营复盘 | 经营数据导入、复盘报告、广告实验分析与推荐 |
| 多 Agent 编排 | LangGraph 驱动，支持人工审批、断点恢复、检查点持久化 |
| 权限与多租户 | JWT 认证、RBAC 三级角色、Workspace 隔离 |

## 技术栈

```
后端:  Python 3.12+ / FastAPI / SQLAlchemy 2.x / Alembic / Pydantic v2
AI:    LangGraph / langgraph-checkpoint-postgres / OpenAI 兼容接口
异步:  Celery + Redis
数据库: MySQL (生产) / SQLite (开发) / PostgreSQL (Agent 检查点)
前端:  Next.js 16 / React 19 / TypeScript / Tailwind CSS 4 / ECharts
部署:  Docker Compose (API + Web + Worker + MySQL + Redis + PostgreSQL)
```

## 快速启动

```bash
# 1. 克隆项目
git clone <repo-url> && cd ecommerce-operation-assistant

# 2. 启动后端（离线开发模式，使用 SQLite）
cd api
cp .env.example .env
pip install -r requirements.txt
python scripts/run_local_dev.py

# 3. 启动前端
cd web
cp .env.example .env.local
npm install && npm run dev

# 4. Docker 一键部署（生产模式）
docker compose up -d
```

## 项目结构

```
ecommerce-operation-assistant/
├── api/                    # 后端服务
│   ├── app/
│   │   ├── agents/         # 多 Agent 编排（LangGraph 工作流）
│   │   ├── api/            # FastAPI 路由
│   │   ├── core/           # 配置与安全
│   │   ├── db/             # 数据库连接
│   │   ├── services/       # 业务服务层
│   │   └── worker/         # Celery 异步任务
│   ├── alembic/            # 数据库迁移
│   ├── tests/              # 测试用例
│   └── scripts/            # 运维脚本
├── web/                    # 前端工作台
│   └── src/
│       ├── app/            # Next.js 页面路由
│       ├── components/     # UI 组件
│       └── lib/            # 工具库
├── scripts/                # 全局脚本
├── docker-compose.yml      # 生产编排
└── docker-compose.offline.yml
```

## 功能扩展建议

1. 接入更多电商平台 API（淘宝/京东/拼多多），实现数据自动采集与同步。
2. 引入 RAG 知识库，将行业运营案例与最佳实践融入诊断和创意生成流程。
3. 增加数据看板模块，基于 ECharts 可视化经营指标与广告 ROI 趋势。

## License

MIT
