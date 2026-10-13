# 验证护栏已真正接入 execute_sql_query 工具：危险 SQL 在连接数据库之前就被拦截并返回提示。
# 若 P03 的重型依赖（langchain_core / mysql.connector / api.monitor）不可用，则跳过。

import pytest

pytest.importorskip("langchain_core.tools")
pytest.importorskip("mysql.connector")

try:
    from tools.mysql_tools import execute_sql_query
except Exception as exc:  # 依赖链任一环节缺失即跳过，不算失败
    pytest.skip(f"execute_sql_query 导入失败（依赖不全）: {exc}")


@pytest.mark.parametrize("sql", [
    "DROP TABLE users",
    "DELETE FROM orders",
    "SELECT 1; DROP TABLE users",
    "UPDATE t SET x = 1",
])
def test_execute_sql_query_blocks_dangerous(sql):
    # 护栏在 connect() 之前执行，因此即使没有数据库连接，也应返回拦截提示而非连接错误
    result = execute_sql_query.invoke({"sql": sql})
    assert isinstance(result, str)
    assert "[已拦截]" in result, f"危险 SQL 未被工具层拦截: {sql} -> {result!r}"
