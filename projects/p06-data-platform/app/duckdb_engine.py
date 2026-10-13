"""DuckDB analytics engine - manages in-process OLAP connections."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb

_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE_DIR / "data"
_DATA_DIR.mkdir(exist_ok=True)
_DB_PATH = str(_DATA_DIR / "analytics.duckdb")

_conn: duckdb.DuckDBPyConnection | None = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """Return the singleton DuckDB connection, creating it on first call."""
    global _conn
    if _conn is None:
        _conn = duckdb.connect(_DB_PATH)
        _conn.execute("SET TimeZone = 'Asia/Shanghai'")
        _conn.execute("PRAGMA threads=4")
        _conn.execute("PRAGMA memory_limit='2GB'")
    return _conn


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


# ── query helpers ──────────────────────────────────────────────

def execute(sql: str, params: list | None = None) -> list[dict[str, Any]]:
    """Execute SQL and return rows as list of dicts."""
    conn = get_conn()
    if params:
        result = conn.execute(sql, params)
    else:
        result = conn.execute(sql)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def execute_scalar(sql: str, params: list | None = None) -> Any:
    """Execute SQL and return a single scalar value."""
    conn = get_conn()
    if params:
        result = conn.execute(sql, params)
    else:
        result = conn.execute(sql)
    row = result.fetchone()
    return row[0] if row else None


def table_exists(table_name: str) -> bool:
    """Check whether a table exists in DuckDB."""
    conn = get_conn()
    result = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return result[0] > 0 if result else False


def list_tables() -> list[str]:
    """Return all user table names in DuckDB."""
    conn = get_conn()
    result = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    return [r[0] for r in result]


def table_info(table_name: str) -> list[dict[str, Any]]:
    """Return column metadata for a table."""
    conn = get_conn()
    result = conn.execute(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = ? ORDER BY ordinal_position",
        [table_name],
    ).fetchall()
    return [
        {"name": r[0], "type": r[1], "nullable": r[2] == "YES"}
        for r in result
    ]


def table_row_count(table_name: str) -> int:
    """Return the number of rows in a table."""
    return execute_scalar(f'SELECT COUNT(*) FROM "{table_name}"') or 0


def preview(table_name: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return the first N rows of a table."""
    return execute(f'SELECT * FROM "{table_name}" LIMIT {limit}')


def column_stats(table_name: str, column_name: str) -> dict[str, Any]:
    """Compute basic statistics for a numeric or string column."""
    conn = get_conn()
    col_type_rows = conn.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = ?",
        [table_name, column_name],
    ).fetchall()
    if not col_type_rows:
        return {"error": f"Column {column_name} not found in {table_name}"}

    col_type = col_type_rows[0][0].upper()
    is_numeric = any(
        t in col_type
        for t in ("INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "HUGEINT")
    )

    base_sql = (
        f'SELECT COUNT(*) AS total, COUNT("{column_name}") AS non_null, '
        f'COUNT(DISTINCT "{column_name}") AS distinct_count '
        f'FROM "{table_name}"'
    )
    stats = execute(base_sql)[0]
    total = stats["total"]
    non_null = stats["non_null"]
    stats["null_count"] = total - non_null
    stats["null_rate"] = round((total - non_null) / total, 4) if total else 0

    if is_numeric:
        detail = execute(
            f'SELECT MIN("{column_name}") AS min_val, '
            f'MAX("{column_name}") AS max_val, '
            f'AVG("{column_name}") AS avg_val, '
            f'MEDIAN("{column_name}") AS median_val, '
            f'STDDEV("{column_name}") AS stddev_val '
            f'FROM "{table_name}"'
        )[0]
        stats.update(detail)
    else:
        top = execute(
            f'SELECT "{column_name}" AS val, COUNT(*) AS cnt '
            f'FROM "{table_name}" WHERE "{column_name}" IS NOT NULL '
            f'GROUP BY "{column_name}" ORDER BY cnt DESC LIMIT 10'
        )
        stats["top_values"] = top

    return stats
