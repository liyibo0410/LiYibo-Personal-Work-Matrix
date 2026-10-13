# SQL 安全护栏（纯标准库实现，可独立测试）
#
# 设计目标：在 execute_sql_query 真正连接数据库之前，拦截一切非只读 / 多语句 /
# 带注释注入的 SQL，满足验收门禁「恶意 SQL（DROP TABLE）被拦截」的要求。
#
# 该模块不依赖任何第三方库与数据库连接，因此可以在没有 MySQL 的环境下被单元测试覆盖。

import re

# 允许的只读起始动词
_ALLOWED_START = (
    "select",
    "show",
    "describe",
    "desc",
    "explain",
    "with",
)

# 危险关键字：即便出现在只读语句内部（如子查询、CTE）也要拦截
_DANGEROUS_KEYWORDS = (
    "drop", "delete", "truncate", "alter", "insert", "update", "create",
    "replace", "grant", "revoke", "merge", "call", "exec", "execute",
    "load", "handler", "lock", "unlock", "rename", "set", "shutdown",
    "kill", "outfile", "dumpfile", "commit", "rollback", "savepoint",
)

# 注释标记（SQL 注入常见载体）
_COMMENT_MARKERS = ("--", "/*", "*/", "#")


def _strip_literals(sql: str) -> str:
    """移除字符串字面量与反引号标识符，避免把 'drop' 这类数据误判为关键字。"""
    # 先去掉单引号 / 双引号字符串，再去掉反引号标识符
    sql = re.sub(r"'(?:''|\\.|[^'])*'", " ", sql)
    sql = re.sub(r'"(?:""|\\.|[^"])*"', " ", sql)
    sql = re.sub(r"`(?:``|[^`])*`", " ", sql)
    return sql


def check_sql_safety(sql: str) -> tuple[bool, str]:
    """校验 SQL 是否为安全的只读查询。

    返回 (is_safe, reason)。is_safe=True 时 reason 为空字符串；
    is_safe=False 时 reason 说明拦截原因。
    """
    if not sql or not sql.strip():
        return False, "SQL 为空"

    raw = sql.strip()

    # 1. 注释拦截
    for marker in _COMMENT_MARKERS:
        if marker in raw:
            return False, f"SQL 含注释符 '{marker}'，疑似注入"

    body = raw.rstrip(";").strip()

    # 2. 多语句拦截（去掉末尾分号后仍含分号）
    if ";" in body:
        return False, "禁止一次执行多条语句"

    lowered = _strip_literals(body).lower()

    # 3. 起始动词必须是只读
    first_word = re.match(r"[a-z]+", lowered.strip())
    if not first_word or first_word.group(0) not in _ALLOWED_START:
        return False, "仅允许 SELECT / SHOW / DESCRIBE / EXPLAIN / WITH 开头的只读查询"

    # 4. 危险关键字扫描（词边界匹配，避免 deleted / update_time / offset 误伤）
    for kw in _DANGEROUS_KEYWORDS:
        if re.search(rf"\b{kw}\b", lowered):
            return False, f"检测到危险关键字 '{kw.upper()}'"

    return True, ""
