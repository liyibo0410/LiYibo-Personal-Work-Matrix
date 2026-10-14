# `_evidence/p02/` 证据登记（P02 电商运营助手 ★旗舰）

> 本目录此前**没有** `INDEX.md`，43 份证据只登记在上级 `_evidence/INDEX.md` 的 D3/D5 段落里。
> 本次先补齐**最要命的一条**：P02 是十个模块里唯一没有 pytest 运行日志的（其余 9 个模块都有
> `pytest-20261013.log`），而 `_evidence/INDEX.md:51` 写着「157 → 162 tests passed」却无日志支撑。
> 2026-10-13 23:52 真实重跑并归档，见下表第一行。

## pytest 套件

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `pytest-20261013.log` | **后端全量测试 162 passed / 0 failed / 24.13s**（172 行完整 `-v` 输出） | 2026-10-13 23:52 |
| `pytest-20261014.log` | **后端全量测试 166 passed / 0 failed / 20.47s**（含新增 `test_product_delete.py` 4 条，见 D23） | 2026-10-14 |

## D23 · 商品池支持删除（2026-10-14，两轮）

| 文件 | 证明哪一条 |
|---|---|
| `D23-商品池删除.md` | 根因（前后端两层都没有删除功能，不是被拦截）、改动清单、级联范围与 AgentRun 保留策略、第二轮「点删除没反应」= 外壳 sandbox 缺 `allow-modals`、**未验证项** |
| `product_delete_live.log` | 实机接口序列：路由已注册 → 建临时商品+SKU(含库存流水)+竞品 → 客服 403 / 未登录 401 / 老板 204 → 详情 404 → 商品池无残留 |
| `verify_product_delete.py` | 上面这份日志的复现脚本（只操作本次新建的临时商品） |
| `pytest-20261014.log` | 4 条新用例：级联清除 18 张子表（开了 `PRAGMA foreign_keys=ON`，漏删即抛约束错误）+ 跨 Workspace 404 + 客服 403 + 未登录 401 |

**两轮的关系**：第一轮用 `window.confirm()` 做二次确认，在统一外壳里**点了没反应** —— 模块 iframe 的
`sandbox` 缺 `allow-modals`，沙箱帧内 `confirm()` 直接返回 false，`preventDefault` 于是恒被触发。
第二轮把商品删除改成服务端渲染的两步确认页（`/products/{id}/delete` 读真实连带数量 →
`/products/{id}/delete/confirm` 才 POST），零 JS 依赖；外壳则补 `allow-modals` 让店铺删除的弹窗恢复可用。
两步链路在「面板不可见 → 页面不水合」的自动化环境里也完整跑通，**含取消分支**（确认页点返回，商品未被删）；
删除后只读 SQL 复核 product_id=7 的 SKU/库存档案/库存流水/竞品/推广链接与全库孤儿行均为 0。

**未验证**：店铺删除只改了外壳，它自己的 `confirm()` 写法没动，「在 iframe 里点店铺删除能弹窗」没实测
（自动化环境不水合 React，真点还会删掉演示店铺）。本目录也没有截图（无可视 surface）。

**命令**（在 `projects/p02-ecommerce-ops-assistant/api/` 目录内执行，必须带 `PYTHONIOENCODING=utf-8`，
否则中文路径在 GBK 控制台下会变成 `PycharmProjects\??????\`，证据即失效）：

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -v
```

**环境**（日志头部原样）：`platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0`，
`configfile: pyproject.toml`，`collected 162 items`。

**跑法说明**：P02 把 pytest 声明成 `[project.optional-dependencies] dev`（不是 dependency-groups），
所以 `uv sync` 不会装它，要 `uv sync --extra dev`；本次归档时 `.venv` 内已有 pytest 9.1.1，直接复用运行环境，
避免 `--with` 造出一个和线上服务不同的临时依赖集。

**测试隔离**（已复核，非断言）：`tests/` 下没有 conftest，各用例自行用
`create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)` + `Base.metadata.create_all`
+ `app.dependency_overrides[get_db]` 建内存库并覆盖鉴权依赖。跑前跑后
`local_dev.db`（1486848 字节）与 `.env.sqlite` 的大小和 mtime 均未变化，**没有污染真实开发库**。

## 这些测试对应哪条门禁（`.qoder/rules/04-验收门禁.md` P02 行）

| 门禁项 | 证据 |
|---|---|
| 权限验证：客服角色访问老板看板被拒（403） | `test_permissions.py` / `test_platform_authorization.py` / `test_users.py` 内多条 403 断言，运行期截图与接口返回另见 `permission_verify.log`、`rbac_四角色验证报告.md`、`e2e_*_viewer.html` |
| 合规词与极限词检测命中拦截 | `test_compliance.py`（套件内），指标与评测见 `compliance_verify.log`、`合规检测评测报告.md` |
| 广告实验（含显著性/统计） | `test_ad_experiments.py` / `test_ad_experiment_stats.py` / `test_ad_recommendation_confirmation.py` |
| 选店 / 商品 / 库存 / 导入链路 | `test_workspace_demo_data.py`、`test_store_inventory_summary.py`、`test_inventory.py` |
| 经营复盘、竞品、素材、视频脚本 | `test_review.py`、`test_competitor_monitoring.py`、`test_generated_assets.py`、`test_video_generation.py` |
| LLM 走网关 + 故障转移 + 无 Key 降级 mock | `test_llm.py`（无出网）；端到端四场景见 `gateway_integration_test.log` |
| 单测 + 集成测试通过 | **本日志** |

## Mock 边界与未测量项（不要当成已完成）

- **覆盖率未测量**：这些模块没有配置任何 coverage 插件，规则 02 要的「输出真实覆盖率数字」目前仍为空，
  本条不声称覆盖。
- **测试全程不出网**：`test_llm.py` / `test_volcengine.py` 只验证请求构造与签名确定性，不发起真实模型或
  即梦调用。真实模型链路证据在 `gateway_integration_test.log` 与 `_evidence/shell/`，属不同验证面。
- **前端测试不在本日志范围**：`web/`（Next.js）无 vitest/Playwright 套件运行记录。
- **门禁「部署上线可访问」仍未满足**：无公网入口（原因见 `_evidence/shell/INDEX.md` 与根 `agents.md`
  「已知未闭环 ④」），本目录的截图都是本地 `127.0.0.1` 采集。
- **环境偏离**：`.venv` 是 Python 3.13.14，而 `.qoder/rules/02-技术规范.md` 要求 3.11/3.12。本次没有改
  运行环境（旗舰服务正跑在同一 venv 上，端口 8000），只登记偏离。

## 顺带登记的存量欠账

- `D3验收报告-P1复核.md` 与 `D3验收报告-深色化与权限-P1复核.md`、`合规检测评测报告.md` 与
  `合规评测报告.md` 是两组内容重叠的报告，命名未统一；上级 `_evidence/INDEX.md` 引用的是前者。
- `verify_backend.py` / `verify_compliance.py` / `verify_permissions.py` 是 P1 复核时的一次性验证脚本，
  留在本目录作为「怎么采的证据」的可复现说明，不是被测代码。
