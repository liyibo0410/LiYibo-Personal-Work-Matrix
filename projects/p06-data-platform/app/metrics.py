"""Metrics engine - time-series queries for pre-defined business metrics."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app import duckdb_engine as db

# ── Metric definitions ──────────────────────────────────────────

METRIC_REGISTRY: dict[str, dict[str, Any]] = {
    "gmv": {
        "name": "成交总额",
        "description": "所有已完成订单的成交金额总和",
        "unit": "元",
        "source_table": "ads_key_metrics",
        "value_column": "gmv",
        "aggregation": "SUM",
    },
    "order_count": {
        "name": "订单量",
        "description": "所有订单数量（含已完成和已退货）",
        "unit": "单",
        "source_table": "ads_key_metrics",
        "value_column": "order_count",
        "aggregation": "SUM",
    },
    "conversion_rate": {
        "name": "转化率",
        "description": "支付用户数 / 独立访客数",
        "unit": "%",
        "source_table": "ads_key_metrics",
        "value_column": "conversion_rate",
        "aggregation": "AVG",
    },
    "avg_order_value": {
        "name": "客单价",
        "description": "成交总额 / 订单量",
        "unit": "元",
        "source_table": "ads_key_metrics",
        "value_column": "avg_order_value",
        "aggregation": "AVG",
    },
    "return_rate": {
        "name": "退货率",
        "description": "退货订单数 / 总订单数",
        "unit": "%",
        "source_table": "ads_key_metrics",
        "value_column": "return_rate",
        "aggregation": "AVG",
    },
    "traffic_uv": {
        "name": "独立访客数",
        "description": "每日独立访客数量",
        "unit": "人",
        "source_table": "ads_key_metrics",
        "value_column": "uv",
        "aggregation": "SUM",
    },
    "traffic_pv": {
        "name": "页面浏览量",
        "description": "每日页面浏览次数",
        "unit": "次",
        "source_table": "ads_key_metrics",
        "value_column": "pv",
        "aggregation": "SUM",
    },
}


def list_metrics() -> list[dict[str, Any]]:
    """Return all registered metric definitions."""
    result = []
    for code, meta in METRIC_REGISTRY.items():
        result.append({"code": code, **meta})
    return result


def query_metric(
    code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "day",
    store_id: str | None = None,
) -> dict[str, Any]:
    """Query a metric and return time-series data.

    Args:
        code: Metric code (e.g. 'gmv', 'order_count')
        start_date: Start date string YYYY-MM-DD
        end_date: End date string YYYY-MM-DD
        granularity: 'day', 'week', or 'month'
        store_id: Optional store filter
    """
    if code not in METRIC_REGISTRY:
        raise ValueError(f"Unknown metric code: {code}")

    meta = METRIC_REGISTRY[code]
    source_table = meta["source_table"]
    value_col = meta["value_column"]
    agg = meta["aggregation"]

    # Build date filter
    where_clauses = []
    params = []
    if start_date:
        where_clauses.append("stat_date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("stat_date <= ?")
        params.append(end_date)

    # Store filter - only works for DWS tables
    if store_id and source_table.startswith("dws_"):
        where_clauses.append("store_id = ?")
        params.append(store_id)
        # For store-level queries, use dws_daily_shop
        if source_table == "ads_key_metrics":
            source_table = "dws_daily_shop"
            value_col = {
                "gmv": "gmv",
                "order_count": "order_count",
                "conversion_rate": None,  # need special handling
                "avg_order_value": "avg_order_value",
                "return_rate": "return_rate",
                "traffic_uv": None,
                "traffic_pv": None,
            }.get(code, value_col)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Granularity grouping
    if granularity == "month":
        date_expr = "STRFTIME(stat_date, '%Y-%m') AS period"
        group_expr = "STRFTIME(stat_date, '%Y-%m')"
    elif granularity == "week":
        date_expr = "STRFTIME(stat_date - (EXTRACT(DOW FROM stat_date)::INTEGER), '%Y-%m-%d') AS period"
        group_expr = "STRFTIME(stat_date - (EXTRACT(DOW FROM stat_date)::INTEGER), '%Y-%m-%d')"
    else:
        date_expr = "CAST(stat_date AS VARCHAR) AS period"
        group_expr = "CAST(stat_date AS VARCHAR)"

    # Special handling for derived metrics
    if code == "conversion_rate":
        if source_table == "dws_daily_shop":
            sql = f"""
                SELECT {date_expr},
                       ROUND(SUM(paying_customers) * 1.0 / NULLIF(SUM(paying_customers) + SUM(return_count), 0), 4) AS value
                FROM {source_table}
                WHERE {where_sql}
                GROUP BY {group_expr}
                ORDER BY period
            """
        else:
            sql = f"""
                SELECT {date_expr},
                       ROUND(AVG(conversion_rate), 4) AS value
                FROM {source_table}
                WHERE {where_sql}
                GROUP BY {group_expr}
                ORDER BY period
            """
    elif code == "avg_order_value" and source_table == "dws_daily_shop":
        sql = f"""
            SELECT {date_expr},
                   ROUND(SUM(gmv) / NULLIF(SUM(order_count), 0), 2) AS value
            FROM {source_table}
            WHERE {where_sql}
            GROUP BY {group_expr}
            ORDER BY period
        """
    else:
        sql = f"""
            SELECT {date_expr},
                   {agg}({value_col}) AS value
            FROM {source_table}
            WHERE {where_sql}
            GROUP BY {group_expr}
            ORDER BY period
        """

    rows = db.execute(sql, params if params else None)

    # Compute summary stats
    values = [r["value"] for r in rows if r["value"] is not None]
    summary = {}
    if values:
        summary = {
            "total": round(sum(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "max": round(max(values), 2),
            "min": round(min(values), 2),
            "count": len(values),
            "latest": values[-1] if values else None,
        }
        # Trend: compare last period to previous
        if len(values) >= 2:
            prev = values[-2]
            curr = values[-1]
            if prev != 0:
                summary["trend"] = round((curr - prev) / abs(prev), 4)
            else:
                summary["trend"] = 0.0

    return {
        "metric": {
            "code": code,
            "name": meta["name"],
            "unit": meta["unit"],
            "description": meta["description"],
        },
        "granularity": granularity,
        "data": rows,
        "summary": summary,
    }


def query_all_summary(start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Get latest summary for all metrics."""
    results = []
    for code in METRIC_REGISTRY:
        try:
            data = query_metric(code, start_date, end_date, granularity="day")
            results.append({
                "code": code,
                "name": data["metric"]["name"],
                "unit": data["metric"]["unit"],
                "latest": data["summary"].get("latest"),
                "avg": data["summary"].get("avg"),
                "trend": data["summary"].get("trend", 0),
            })
        except Exception:
            results.append({
                "code": code,
                "name": METRIC_REGISTRY[code]["name"],
                "unit": METRIC_REGISTRY[code]["unit"],
                "latest": None,
                "avg": None,
                "trend": 0,
            })
    return results
