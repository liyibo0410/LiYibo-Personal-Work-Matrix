# P02 · 电商运营助手 ★旗舰

> 本项目的 AI 协作任务卡。开工时**把「本次任务」一节整段粘进 Qoder 的 Quest / Agent 对话**。

## 定位

整套作品集的**全栈旗舰**：唯一带完整认证、权限、后台、真实数据库的业务系统。
演示时它是主战场 —— 最可能说"跑一下我看看"的就是它。

## 源项目

```
D:\software\PycharmProjects\ecommerce-operation-assistant\
```

**原件禁止修改或删除**。改造方式：复制到本项目目录后重构（`.git` 不要复制）。

## 现状（体检结论）

- 后端：`api/`（FastAPI + SQLAlchemy 2.x + Alembic + Pydantic v2），含 `agents/`（LangGraph 编排）、`core/`、`db/`、`services/`、`worker/`（Celery）
- 前端：`web/`（**Next.js 16 / React 19 / TypeScript / Tailwind 4 / ECharts**）
- **已有能力**：商品诊断 / 竞品分析 / 创意策划 / 图视频生成 / 库存建议 / 经营复盘 / 广告实验（`tests/test_ad_experiments.py`）/ LangGraph 多 Agent + 人工审批 + 断点恢复 / **JWT + RBAC 三级角色 + Workspace 多租户**
- 工程化：`Dockerfile` + `docker-compose.yml`（API+Web+Worker+MySQL+Redis+PG）+ `alembic/` + `tests/` + `evals/`
- 启动：后端 `cd api && python scripts/run_local_dev.py`（**SQLite 离线模式，不必起 3 个数据库**）；前端 `cd web && npm install && npm run dev`
- 判定：**五个项目里最成熟，改造量最小** → 定为旗舰

## 改造目标

从"功能齐全的 AI 工具集"→ **"可交付给品牌方的运营 SaaS"**。

## 必做功能清单

### A. 认证与权限（多数已有，需验收与补齐）
- [ ] 登录 / 注册 / JWT 刷新
- [ ] 四角色：老板 / 运营 / 美工 / 客服，按店铺授权
- [ ] 前端路由守卫 + 按钮级权限
- [ ] **权限验证证据**：客服角色访问老板看板返回 403

### B. 商品运营（核心卖点）
- [ ] 标题 / 卖点 / 详情页文案 / SEO 关键词生成
- [ ] **合规词与极限词检测**：内置词库（"最""第一""国家级""绝无仅有"等），生成后自动检测并高亮拦截
- [ ] 合规检测要有**拦截率数据**（评测集 → 命中率）

### C. 广告投放
- [ ] 投放计划创建
- [ ] A/B 实验（扩展已有 `ad_experiments`），含显著性检验
- [ ] 效果统计与投放建议

### D. 内容生产
- [ ] 主图文案 / 短视频脚本 / 直播话术生成
- [ ] 一键推送到 P07 素材中心（跨模块调用）

### E. 数据看板
- [ ] GMV / 转化率 / ROI / 客单价趋势（ECharts）
- [ ] **数据取自 P06 数据中台的指标 API**（不是自己造数）

### F. 工程与质量
- [ ] 任务队列（Celery/RQ）异步化 + 进度回传
- [ ] 扩展 `evals/product_operation_cases.json`，出评测报告
- [ ] 单测 + 集成测试通过，输出覆盖率
- [ ] 前端视觉统一到深色体系（`shared/ui-kit`）
- [ ] Docker Compose 一键起全栈

## 技术栈（遵守与调整）

```
后端  Python 3.12 + uv + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
AI    LangGraph + shared/llm-gateway（禁止绕过网关直连模型）
异步  Celery + Redis
数据  SQLite(开发) / PostgreSQL(生产) / agent 检查点用 Postgres
前端  Next.js 16 + React 19 + TS + Tailwind 4 + ECharts
部署  Docker Compose
```

> 迁移要求：把现有的模型调用改造成走 `shared/llm-gateway`；把 `requirements.txt` 收敛到 `pyproject.toml`（保留 uv 管理）。

## 跨模块依赖

| 方向 | 内容 |
|---|---|
| 依赖 P06 | 经营数据、指标口径（看板取数） |
| 依赖 shared | llm-gateway、auth、ui-kit、config |
| 输出到 P07 | 生成的文案 / 图片素材 |
| 被 shell 挂载 | `/workspace/ecommerce-ops` |

## 验收门禁

- [ ] 登录 → 选店 → 生成商品文案 → **合规检测命中并拦截** → 创建广告实验 → 查看对比数据（全链路截图）
- [ ] 权限验证：客服角色访问老板看板被拒（403 证据）
- [ ] 单元测试 + 集成测试通过，输出测试报告
- [ ] 评测集跑通，出准确率与合规拦截率
- [ ] 本地一键启动（含前端），有启动日志
- [ ] 证据落到 `_evidence/p02/` 并登记 `INDEX.md`

## 执行顺序建议

```
1. 复制源项目 → uv sync / npm install 跑通原始版本（先证明"能跑"）
2. 接 shared/llm-gateway，替换裸模型调用
3. 补合规词检测 + 评测集
4. 前端深色化 + 权限守卫
5. 接 P06 指标 API（P06 就绪后）
6. 全链路验收 + 截图存证
```

## 本次任务

> 每次开工把这里替换成本次要做的具体事项。

### D2（2026-10-12）· 复制 + 跑通原始版本 — ✅ 已完成

```
① 复制源项目到本项目目录（排除 .git / venv / node_modules / __pycache__ / .next）
② 后端走 SQLite 离线模式跑通（api/scripts/run_local_dev.py）
③ 前端 npm install 后 npm run dev 跑通
④ 不改任何业务逻辑
⑤ 产出：环境验证报告 + 启动日志 + 路由探测结果
```

**实际结果**：后端 3 秒就绪、前端 4.4 秒 Ready、5 个页面 200、认证链路（登录/JWT/401）全通。
详见 `_evidence/p02/验收报告.md`。

### D3（待开工）· 核心卖点

```
① 商品文案生成加「合规词与极限词检测」（词库可维护 + 拦截开关 + 评测集 ≥30 条）
② 前端深色化（登录 / 工作台 / 看板三页优先）+ 权限守卫
③ 补 /stores、/products 列表页（原项目缺失）
④ 产出：客服角色访问老板看板 403 的证据 + 合规拦截率数据
```

## 进度

| 日期 | 完成 | 证据 | 未完成 |
|---|---|---|---|
| 2026-10-12 | 复制源项目（35.5MB/400 文件）；uv sync（21s）；后端跑通（health/登录/JWT/401）；npm install（368 包）；前端跑通（5 页 200） | `_evidence/p02/` 全套（验收报告 + 3 份日志 + 路由表 + home.html） | 列表页缺失；npm audit 12 漏洞；深色化未开始；合规检测未开始 |
| 2026-10-14 | 商品池**删除**能力补齐（此前前后端两层都没有）：`DELETE /api/v1/products/{id}` + 三个入口（列表行 / 首页行 / 详情页头部），级联清除 18 张子表，`agent_runs`/`agent_approvals` 只置空 `product_id` 保留审计。第二轮修「点删除没反应」：外壳模块 iframe 的 `sandbox` 缺 `allow-modals`，沙箱内 `window.confirm()` 恒返回 false → 商品删除改成**服务端两步确认页**（`/products/{id}/delete` 读真实连带数量 → `.../delete/confirm` 才 POST，零 JS 依赖），外壳补 `allow-modals` 让店铺删除弹窗恢复可用 | `_evidence/p02/D23-商品池删除.md`、`product_delete_live.log`（实机 403/401/204/404 序列）、`pytest-20261014.log`（162 → **166 passed**，级联用例开 `PRAGMA foreign_keys=ON`）、删除后只读 SQL 子表与全库孤儿行全 0、两步链路含「取消」分支的零 JS 实测 | 店铺删除的 `confirm()` 写法未改，「在 iframe 里点店铺删除能弹窗」没实测；无截图（内置浏览器无可视 surface）；PostgreSQL 侧未实机复跑 |
