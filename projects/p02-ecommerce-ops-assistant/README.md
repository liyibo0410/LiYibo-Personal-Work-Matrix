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
npm run dev                                            # http://127.0.0.1:3000
```

### 已验证结果（2026-10-12）

- 后端：uvicorn 3 秒就绪；`/health` 200；登录 200（JWT）；无 token 访问 `/api/v1/auth/me` → 401；OpenAPI 78 路径
- 前端：Next.js 16.3.1 (Turbopack) 4.4 秒 Ready；`/` `/login` `/agent` `/imports` `/settings` 全部 200
- 证据：`_evidence/p02/验收报告.md`

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
