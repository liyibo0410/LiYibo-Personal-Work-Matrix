# P02 演示库漂移导致登录页四个演示账号全部 401（2026-10-15 11:55~12:25，Qoder）

## 现象

P02 是旗舰模块，也是读者第一个要登录进去点的东西。登录页 `web/src/app/login/page.tsx:13-20`
给出**四个可一键填充的演示账号**（`boss/ops/design/cs@example.com`，口令 `Test123456`）。
实测这四个账号**全部 401 `Invalid email or password`** —— 首屏点哪个都进不去。

## 定性过程（结论不是"代码写错了"）

1. 只读查 `api/local_dev.db`：库里 12 个用户，邮箱是 `boss@legacy.example.com`、`owner@legacy.example.demo`、
   `admin@local.dev` 这批，**一个 `@example.com` 都没有**；
2. 查代码口径：`api/scripts/bootstrap_demo_users.py:20-23`、`acceptance_check.py`、`routes/workspace.py`
   三处都用 `@example.com`；全仓 grep `legacy.example.com` 在代码与文档里**零出现**；
3. 所以代码与 UI 是自洽的，**漂移的是这台机器的演示库**：某次品牌改名时手工往库里塞了一批
   `@legacy.example.com` 用户，而文档化的种子路径创建的账号从未落库。
   连带后果：`acceptance_check.py`（验收脚本）在当前库上根本跑不过。

**不是代码 bug，所以没有改代码** —— 改 `page.tsx` 去迁就漂移的库，会让 fresh 环境（照 README 跑 bootstrap）反而对不上。

## 处置

跑文档化、幂等的种子脚本补齐账号（`ensure_bootstrap_user` 存在即跳过）：

```
[Created] boss@example.com role=owner
[Created] ops@example.com role=operator
[Created] design@example.com role=designer
[Created] cs@example.com role=cs
```
**动手前先备份** `api/local_dev.db` → `_runtime/qoder-backup-20261015/p02-local_dev.before-bootstrap.db`（1.49 MB）。
不需要重启服务：`run_local_dev.py:28` 用的是 `API_DIR/local_dev.db`，SQLite 每次读事务都能看到新提交。

## 复验（全部实测）

| 检查 | 结果 |
|---|---|
| 四个演示账号登录 | `boss/ops/design/cs@example.com` → **全部 200**，角色 owner/operator/designer/cs 正确 |
| **RBAC 门禁**（P02 验收项：客服访问老板看板须被拒） | `cs` → `/api/v1/dashboard/overview` **403**、`/api/v1/users` **403**；`boss` → overview **200** |
| P02→P06 跨模块真实取数 | `metrics_source="p06-live"`、`metrics_degraded=False`、`metrics_error=""` |
| 指标数值与 P06 逐条一致 | gmv `35958.37 / avg 36005.68 / trend 0.3387`、order_count `133/126.99/0.2547` 与 P06 `/api/v1/metrics/summary` 完全相同 |
| 计数自洽 | `total_stores=2` = `/stores` 长度 2；`total_products=3` = `/products` 长度 3 |

## 我自己犯的一个错（记下来免得重犯）

bootstrap 之后我第一轮验证报"四个账号仍然 401"，据此差点下结论"服务连的不是这个库"。
实际是**我的探测脚本写错了**：P02 的 `/api/v1/*` 用 **Bearer token**，我却用 Cookie 会话去访问，
且脚本里 `sess()` 返回三元组却被解包成两个变量，异常路径整个失真。
第二轮用正确的 Bearer 方式重测 → 全部 200。
随后还查了端口归属（`:8000` 是 PID 48776，启动于 10-14 23:01，**bootstrap 之后没有重启**），
排除了"靠重启才生效"这个误判。
教训：**验证失败先怀疑探针，再怀疑被测物** —— 尤其是我自己现写的探测脚本。

## 遗留

- 库里那 8 个 `@legacy.*` / `@local.dev` 用户是漂移残留，**我没删**（不是我的数据，且删用户属破坏性操作）。
  现在 12 个用户并存，`/api/v1/users` 会列出两批账号 —— 建议由负责功能完善的一方决定是清理还是收进 seed 脚本。
- 更根本的问题：**演示账号没有单一来源**。UI 硬编码一份、bootstrap 一份、库里的实际数据第三份，
  三者靠人肉对齐，这次就是它们散架的结果。正解是登录页的演示账号由后端下发（如 `GET /api/v1/auth/demo-accounts`），
  属功能完善（WorkBuddy 那条线），本轮不做。
