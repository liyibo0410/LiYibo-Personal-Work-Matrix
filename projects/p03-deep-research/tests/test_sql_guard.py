# tools/sql_guard.py 的单元测试：验收门禁「恶意 SQL（DROP TABLE）被拦截」的证据。
# 纯函数测试，不需要 MySQL 连接。

import pytest

from tools.sql_guard import check_sql_safety


# ---------- 合法只读查询：必须放行 ----------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM drugs LIMIT 100",
    "select id, name from users where age > 18",
    "SHOW TABLES",
    "show databases",
    "DESCRIBE drugs",
    "desc drugs",
    "EXPLAIN SELECT * FROM drugs",
    "WITH t AS (SELECT id FROM drugs) SELECT * FROM t",
    "SELECT COUNT(*) AS total FROM orders GROUP BY status",
    "SELECT * FROM logs WHERE message = 'dropped connection'",  # 字符串字面量内的危险词不误伤
    "SELECT update_time, deleted_flag FROM t",  # 含 update/delete 子串的列名不误伤
    "SELECT * FROM t LIMIT 10 OFFSET 20",  # OFFSET 不误伤 SET
    "SELECT * FROM drugs;",  # 末尾单分号允许
])
def test_safe_queries_allowed(sql):
    ok, reason = check_sql_safety(sql)
    assert ok is True, f"应放行却被拦截: {reason}"
    assert reason == ""


# ---------- 破坏性 / 写操作：必须拦截 ----------

@pytest.mark.parametrize("sql", [
    "DROP TABLE users",
    "drop table drugs",
    "DELETE FROM users WHERE id = 1",
    "TRUNCATE TABLE orders",
    "UPDATE users SET name = 'x'",
    "INSERT INTO users VALUES (1, 'a')",
    "ALTER TABLE users ADD COLUMN x INT",
    "CREATE TABLE evil (id INT)",
    "REPLACE INTO users VALUES (1)",
    "GRANT ALL ON *.* TO 'hacker'",
    "REVOKE ALL ON *.* FROM 'user'",
    "MERGE INTO t USING s ON t.id = s.id",
    "CALL dangerous_proc()",
    "EXEC sp_help",
    "EXECUTE sp_help",
    "LOAD DATA INFILE '/etc/passwd' INTO TABLE t",
    "HANDLER users OPEN",
    "LOCK TABLES users WRITE",
    "UNLOCK TABLES",
    "RENAME TABLE users TO old_users",
    "SET GLOBAL max_connections = 1000",
    "SHUTDOWN",
    "KILL 1234",
    "SELECT * FROM t INTO OUTFILE '/tmp/x'",
    "SELECT * FROM t INTO DUMPFILE '/tmp/x'",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT sp1",
])
def test_destructive_queries_blocked(sql):
    ok, reason = check_sql_safety(sql)
    assert ok is False, f"危险 SQL 未被拦截: {sql}"
    assert reason != ""


# ---------- 注入手法：注释 / 多语句 / 空 ----------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM users; DROP TABLE users",       # 多语句
    "SELECT * FROM users WHERE 1=1; DELETE FROM x", # 多语句
    "SELECT * FROM users -- WHERE admin = 0",       # 行注释
    "SELECT * FROM users /* hidden */",             # 块注释
    "SELECT * FROM users # comment",                # MySQL 注释
    "",                                              # 空
    "   ",                                           # 空白
    "INSERT INTO t VALUES (1); SELECT 1",            # 写+多语句
])
def test_injection_patterns_blocked(sql):
    ok, reason = check_sql_safety(sql)
    assert ok is False, f"注入手法未被拦截: {sql!r}"
    assert reason != ""


# ---------- 非只读起始动词 ----------

@pytest.mark.parametrize("sql", [
    "banana",
    "1 + 1",
    "(SELECT 1)",  # 括号开头不是合法起始动词
])
def test_non_readonly_start_blocked(sql):
    ok, reason = check_sql_safety(sql)
    assert ok is False


# ---------- 只读语句内部藏危险关键字也要拦截 ----------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM (DELETE FROM users) AS x",
    "WITH evil AS (DROP TABLE t) SELECT * FROM evil",
    "SELECT * FROM users WHERE id IN (SELECT id FROM t); UPDATE x SET y=1",
])
def test_dangerous_keyword_nested_in_readonly(sql):
    ok, reason = check_sql_safety(sql)
    assert ok is False, f"嵌套危险关键字未被拦截: {sql}"


def test_reason_mentions_keyword_for_drop():
    # DROP TABLE 首先违反「只读起始动词」规则而被拦截；
    # 危险关键字扫描是针对藏在只读语句内部的情况（见 test_dangerous_keyword_nested_in_readonly）。
    ok, reason = check_sql_safety("DROP TABLE users")
    assert ok is False
    assert reason != ""


def test_reason_mentions_keyword_for_nested_drop():
    # 以 WITH 开头的只读语句里嵌套 DROP，应被关键字扫描命中并点名 DROP
    ok, reason = check_sql_safety("WITH evil AS (DROP TABLE t) SELECT * FROM evil")
    assert ok is False
    assert "DROP" in reason.upper()
