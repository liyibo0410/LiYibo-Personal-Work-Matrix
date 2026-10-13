"""Data quality checks - null rate, duplication, anomaly detection."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app import duckdb_engine as db
from app.models import QualityResult, get_session


# ── Check implementations ───────────────────────────────────────

def check_null_rates(table_name: str) -> list[dict[str, Any]]:
    """Check null rates for all columns in a table."""
    columns = db.table_info(table_name)
    if not columns:
        return []

    total = db.table_row_count(table_name)
    if total == 0:
        return []

    results = []
    for col in columns:
        col_name = col["name"]
        stats = db.execute(
            f'SELECT COUNT("{col_name}") AS non_null FROM "{table_name}"'
        )
        non_null = stats[0]["non_null"] if stats else 0
        null_count = total - non_null
        null_rate = round(null_count / total, 4) if total else 0

        # Thresholds
        if null_rate > 0.5:
            status = "FAIL"
            severity = "CRITICAL"
        elif null_rate > 0.2:
            status = "WARN"
            severity = "WARN"
        else:
            status = "PASS"
            severity = "INFO"

        results.append({
            "table_name": table_name,
            "check_type": "null_rate",
            "check_name": f"空值率检查 - {col_name}",
            "column_name": col_name,
            "status": status,
            "severity": severity,
            "metric_value": null_rate,
            "threshold": 0.2,
            "details": f"总行数: {total}, 空值: {null_count}, 空值率: {null_rate:.2%}",
        })

    return results


def check_duplicates(table_name: str) -> list[dict[str, Any]]:
    """Check for duplicate rows based on all columns."""
    total = db.table_row_count(table_name)
    if total == 0:
        return []

    # Count distinct rows using all columns
    columns = db.table_info(table_name)
    col_names = [c["name"] for c in columns]
    col_list = ", ".join(f'"{c}"' for c in col_names)

    distinct_count = db.execute_scalar(
        f'SELECT COUNT(*) FROM (SELECT DISTINCT {col_list} FROM "{table_name}")'
    ) or 0

    dup_count = total - distinct_count
    dup_rate = round(dup_count / total, 4) if total else 0

    if dup_rate > 0.1:
        status = "FAIL"
        severity = "CRITICAL"
    elif dup_rate > 0.01:
        status = "WARN"
        severity = "WARN"
    else:
        status = "PASS"
        severity = "INFO"

    return [{
        "table_name": table_name,
        "check_type": "duplication",
        "check_name": "重复行检查",
        "column_name": "",
        "status": status,
        "severity": severity,
        "metric_value": dup_rate,
        "threshold": 0.01,
        "details": f"总行数: {total}, 重复行: {dup_count}, 重复率: {dup_rate:.2%}",
    }]


def check_primary_key(table_name: str) -> list[dict[str, Any]]:
    """Check if the first column (assumed PK) has unique values.
    
    Note: Some tables (like ranking/summary tables) naturally have
    non-unique first columns. This check reports but doesn't fail
    for known aggregate tables.
    """
    columns = db.table_info(table_name)
    if not columns:
        return []

    pk_col = columns[0]["name"]
    total = db.table_row_count(table_name)
    distinct = db.execute_scalar(
        f'SELECT COUNT(DISTINCT "{pk_col}") FROM "{table_name}"'
    ) or 0

    dup_count = total - distinct
    
    # Aggregate/summary tables naturally have non-unique first columns
    is_aggregate = any(
        table_name.startswith(prefix) 
        for prefix in ("ads_product_", "dws_daily_")
    ) or "ranking" in table_name or "profile" in table_name
    
    if is_aggregate:
        # Just informational for aggregate tables
        status = "PASS"
        severity = "INFO"
    elif dup_count > 0:
        status = "FAIL"
        severity = "CRITICAL"
    else:
        status = "PASS"
        severity = "INFO"

    return [{
        "table_name": table_name,
        "check_type": "primary_key",
        "check_name": f"主键唯一性检查 - {pk_col}",
        "column_name": pk_col,
        "status": status,
        "severity": severity,
        "metric_value": dup_count,
        "threshold": 0,
        "details": f"主键列: {pk_col}, 总行数: {total}, 唯一值: {distinct}, 重复: {dup_count}",
    }]


def check_freshness(table_name: str, date_column: str = "stat_date") -> list[dict[str, Any]]:
    """Check data freshness - how recent is the data."""
    columns = db.table_info(table_name)
    col_names = [c["name"] for c in columns]

    # Find a date/timestamp column
    target_col = None
    if date_column in col_names:
        target_col = date_column
    else:
        for c in columns:
            if "date" in c["name"].lower() or "time" in c["name"].lower():
                target_col = c["name"]
                break

    if not target_col:
        return []

    max_date = db.execute_scalar(
        f'SELECT MAX("{target_col}") FROM "{table_name}"'
    )
    if max_date is None:
        return [{
            "table_name": table_name,
            "check_type": "freshness",
            "check_name": f"数据新鲜度检查 - {target_col}",
            "column_name": target_col,
            "status": "FAIL",
            "severity": "CRITICAL",
            "metric_value": 0,
            "threshold": 0,
            "details": "表中无数据",
        }]

    # Parse the date
    if isinstance(max_date, str):
        try:
            max_date = datetime.strptime(max_date[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    if isinstance(max_date, datetime):
        max_date = max_date.date()

    if hasattr(max_date, "timetuple"):
        from datetime import date as dt_date
        ref = dt_date.today()
        days_ago = (ref - max_date).days
    else:
        days_ago = -1

    if days_ago < 0:
        status = "PASS"
        severity = "INFO"
    elif days_ago <= 7:
        status = "PASS"
        severity = "INFO"
    elif days_ago <= 30:
        status = "WARN"
        severity = "WARN"
    else:
        status = "FAIL"
        severity = "CRITICAL"

    return [{
        "table_name": table_name,
        "check_type": "freshness",
        "check_name": f"数据新鲜度检查 - {target_col}",
        "column_name": target_col,
        "status": status,
        "severity": severity,
        "metric_value": max(0, days_ago),
        "threshold": 7,
        "details": f"最新日期: {max_date}, 距今: {max(0, days_ago)}天",
    }]


def check_value_range(table_name: str, column_name: str, min_val: float = None, max_val: float = None) -> list[dict[str, Any]]:
    """Check if numeric values fall within expected range."""
    if min_val is None and max_val is None:
        return []

    conditions = []
    if min_val is not None:
        conditions.append(f'"{column_name}" < {min_val}')
    if max_val is not None:
        conditions.append(f'"{column_name}" > {max_val}')

    where = " OR ".join(conditions)
    outlier_count = db.execute_scalar(
        f'SELECT COUNT(*) FROM "{table_name}" WHERE {where}'
    ) or 0
    total = db.table_row_count(table_name)
    outlier_rate = round(outlier_count / total, 4) if total else 0

    if outlier_rate > 0.05:
        status = "FAIL"
        severity = "CRITICAL"
    elif outlier_rate > 0.01:
        status = "WARN"
        severity = "WARN"
    else:
        status = "PASS"
        severity = "INFO"

    range_desc = []
    if min_val is not None:
        range_desc.append(f"最小值: {min_val}")
    if max_val is not None:
        range_desc.append(f"最大值: {max_val}")

    return [{
        "table_name": table_name,
        "check_type": "value_range",
        "check_name": f"值域范围检查 - {column_name}",
        "column_name": column_name,
        "status": status,
        "severity": severity,
        "metric_value": outlier_rate,
        "threshold": 0.01,
        "details": f"异常值: {outlier_count}/{total}, 异常率: {outlier_rate:.2%}, 期望范围: {', '.join(range_desc)}",
    }]


# ── Run all checks ──────────────────────────────────────────────

def run_all_checks(table_name: str | None = None) -> list[dict[str, Any]]:
    """Run all quality checks on specified table or all tables."""
    tables = [table_name] if table_name else db.list_tables()
    all_results = []

    for tbl in tables:
        all_results.extend(check_null_rates(tbl))
        all_results.extend(check_duplicates(tbl))
        all_results.extend(check_primary_key(tbl))
        all_results.extend(check_freshness(tbl))

    # Specific range checks for known columns
    if db.table_exists("ods_orders"):
        all_results.extend(check_value_range("ods_orders", "total_amount", min_val=0))
        all_results.extend(check_value_range("ods_orders", "quantity", min_val=1, max_val=100))
    if db.table_exists("ods_products"):
        all_results.extend(check_value_range("ods_products", "price", min_val=0))
        all_results.extend(check_value_range("ods_products", "cost", min_val=0))

    return all_results


def save_results(results: list[dict[str, Any]]) -> None:
    """Persist quality check results to metadata DB."""
    session = get_session()
    try:
        for r in results:
            qr = QualityResult(
                table_name=r["table_name"],
                check_type=r["check_type"],
                check_name=r["check_name"],
                column_name=r.get("column_name", ""),
                status=r["status"],
                severity=r.get("severity", "INFO"),
                metric_value=r.get("metric_value", 0),
                threshold=r.get("threshold", 0),
                details=r.get("details", ""),
            )
            session.add(qr)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def compute_health_score(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute an overall data health score from quality results."""
    if not results:
        return {"score": 0, "total_checks": 0, "passed": 0, "warned": 0, "failed": 0}

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    # Score: percentage-based with penalties
    # Base score is pass rate (0-100), then subtract penalties
    base_score = (passed / total * 100) if total > 0 else 0
    penalty = warned * 2 + failed * 5
    score = max(0, min(100, round(base_score - penalty)))

    return {
        "score": score,
        "total_checks": total,
        "passed": passed,
        "warned": warned,
        "failed": failed,
    }
