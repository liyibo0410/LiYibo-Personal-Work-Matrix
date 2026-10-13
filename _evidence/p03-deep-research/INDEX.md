# P03 Deep Research 问数 — 证据索引

## pytest-20261013.log
- **命令**：`.venv/Scripts/python.exe -m pytest tests -v`（PYTHONIOENCODING=utf-8）
- **结果**：61 passed in 0.26s
- **证明的功能**：
  - `tools/sql_guard.py::check_sql_safety` 只读 SQL 护栏（验收门禁「恶意 SQL（DROP TABLE）被拦截」）
    - 合法只读查询放行：SELECT / SHOW / DESCRIBE / EXPLAIN / WITH、末尾单分号、字符串字面量内危险词不误伤、含 update/delete 子串的列名不误伤、OFFSET 不误伤 SET
    - 破坏性写操作拦截：DROP / DELETE / TRUNCATE / UPDATE / INSERT / ALTER / CREATE / REPLACE / GRANT / REVOKE / MERGE / CALL / EXEC(UTE) / LOAD / HANDLER / LOCK / UNLOCK / RENAME / SET / SHUTDOWN / KILL / OUTFILE / DUMPFILE / COMMIT / ROLLBACK / SAVEPOINT
    - 注入手法拦截：多语句（分号）、行注释 `--`、块注释 `/* */`、MySQL 注释 `#`、空 SQL
    - 只读语句内部嵌套危险关键字（如 `WITH ... (DROP TABLE ...) SELECT`）也被关键字扫描命中
  - `tools/mysql_tools.py::execute_sql_query` 已接入护栏（test_tool_integration.py）
    - 危险 SQL 在 `connect()` 之前返回 `[已拦截] ...`，无需数据库连接即可验证

## 未测量 / 未覆盖（诚实标注）
- **幻觉测试（问库里没有的数据必须拒答而非编造）**：该行为由 LLM + prompt（deepagents 主/子智能体）驱动，
  非确定性纯函数，**未编写单元测试**，需在真实 LLM 端点下人工验证。当前仅护栏层（确定性逻辑）有自动化测试。
- **前端流式思考链可见**：依赖 WebSocket + 真实 LLM 调用，属人工演示项，非 pytest 覆盖范围。
- **SQL 自动生成 / 图表生成 / 溯源报告**：属 LLM 链路，未做自动化评测。
