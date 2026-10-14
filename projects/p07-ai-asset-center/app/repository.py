"""P07 数据访问层：所有 SQL 收口在这里，`tags` 出参统一为字符串数组。

历史坑：`tags` 以原始字符串入库（前端 `JSON.parse` 遇到 `护肤,夏季` 直接抛错，
整块素材库渲染失败）。这里在读侧做规范化，接口对外只暴露数组。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from app.db import get_db, now_iso


def normalize_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    if not raw:
        return []
    text = str(raw).strip()
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, list):
        return [str(t).strip() for t in parsed if str(t).strip()]
    if isinstance(parsed, str) and parsed:
        return [t.strip() for t in parsed.replace("，", ",").split(",") if t.strip()]
    return [t.strip() for t in text.replace("，", ",").split(",") if t.strip()]


def _row_to_asset(row: sqlite3.Row, *, with_performance: bool = False) -> dict[str, Any]:
    asset = dict(row)
    asset["tags"] = normalize_tags(asset.get("tags"))
    if with_performance:
        asset["file_url"] = f"/api/v1/assets/{asset['asset_id']}/file" if asset.get("file_path") else None
    return asset


def list_assets(
    page: int, size: int, asset_type: str | None = None, keyword: str | None = None
) -> tuple[int, list[dict[str, Any]]]:
    conn = get_db()
    where, params = ["status != 'archived'"], []
    if asset_type:
        where.append("asset_type = ?")
        params.append(asset_type)
    if keyword:
        where.append("(name LIKE ? OR tags LIKE ? OR description LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM assets WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM assets WHERE {clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        params + [size, (page - 1) * size],
    ).fetchall()
    conn.close()
    return total, [_row_to_asset(r, with_performance=True) for r in rows]


def get_asset(asset_id: str) -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if not row:
        conn.close()
        return None
    asset = _row_to_asset(row, with_performance=True)
    perf = conn.execute(
        "SELECT * FROM performance_links WHERE asset_id = ? ORDER BY period_start DESC", (asset_id,)
    ).fetchall()
    conn.close()
    asset["performance"] = [dict(p) for p in perf]
    return asset


def new_asset_id() -> str:
    return f"AST-{uuid.uuid4().hex[:6].upper()}"


def create_asset(
    *,
    name: str,
    asset_type: str,
    tags: Any,
    description: str,
    file_path: str = "",
    file_size: int = 0,
    width: int | None = None,
    height: int | None = None,
    mime_type: str = "",
    content: str = "",
    source: str = "upload",
    tag_source: str = "manual",
    asset_id: str | None = None,
) -> dict[str, Any]:
    """`asset_id` 可由调用方预先分配 —— 上传落盘时文件名必须与最终行 ID 一致，否则磁盘上会留下孤儿文件。"""
    ts = now_iso()
    conn = get_db()
    asset_id = asset_id or new_asset_id()
    conn.execute(
        "INSERT INTO assets (asset_id, name, asset_type, tags, description, content, file_path,"
        " file_size, width, height, source, status, created_at, updated_at, mime_type, tag_source)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (asset_id, name, asset_type, json.dumps(normalize_tags(tags), ensure_ascii=False),
         description, content, file_path, file_size, width, height, source, "active", ts, ts,
         mime_type, tag_source),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    conn.close()
    return _row_to_asset(row, with_performance=True)


def update_asset(asset_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"name", "asset_type", "tags", "description", "content", "file_path", "file_size",
               "width", "height", "mime_type", "tag_source", "status"}
    sets, params = [], []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "tags":
            value = json.dumps(normalize_tags(value), ensure_ascii=False)
        sets.append(f"{key} = ?")
        params.append(value)
    if not sets:
        return get_asset(asset_id)
    sets.append("updated_at = ?")
    params.append(now_iso())
    params.append(asset_id)
    conn = get_db()
    conn.execute(f"UPDATE assets SET {', '.join(sets)} WHERE asset_id = ?", params)
    conn.commit()
    conn.close()
    return get_asset(asset_id)


def delete_asset(asset_id: str) -> str | None:
    """删除素材行及其投放关联，返回被删除的文件路径（可能为空）。"""
    conn = get_db()
    row = conn.execute("SELECT file_path FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute("DELETE FROM assets WHERE asset_id = ?", (asset_id,))
    conn.execute("DELETE FROM performance_links WHERE asset_id = ?", (asset_id,))
    conn.commit()
    conn.close()
    return row["file_path"] or ""


def active_assets() -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM assets WHERE status = 'active'").fetchall()
    conn.close()
    return [_row_to_asset(r) for r in rows]


def add_performance(asset_id: str, data: dict[str, Any]) -> dict[str, Any]:
    conn = get_db()
    conn.execute(
        "INSERT INTO performance_links (asset_id, store_name, platform, impressions, clicks,"
        " conversions, spend, revenue, period_start, period_end, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (asset_id, data["store_name"], data["platform"], data["impressions"], data["clicks"],
         data["conversions"], data["spend"], data["revenue"], data["period_start"],
         data["period_end"], now_iso()),
    )
    conn.commit()
    conn.close()
    return get_asset(asset_id)  # type: ignore[return-value]


def stats() -> dict[str, Any]:
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    by_type = {r["asset_type"]: r["cnt"] for r in conn.execute(
        "SELECT asset_type, COUNT(*) as cnt FROM assets GROUP BY asset_type")}
    by_source = {r["source"]: r["cnt"] for r in conn.execute(
        "SELECT source, COUNT(*) as cnt FROM assets GROUP BY source")}
    by_tag_source = {r["tag_source"]: r["cnt"] for r in conn.execute(
        "SELECT tag_source, COUNT(*) as cnt FROM assets GROUP BY tag_source")}
    with_file = conn.execute("SELECT COUNT(*) FROM assets WHERE file_path != ''").fetchone()[0]
    linked_ids = {r["asset_id"] for r in conn.execute("SELECT DISTINCT asset_id FROM performance_links")}
    spend = conn.execute("SELECT COALESCE(SUM(spend),0) FROM performance_links").fetchone()[0]
    revenue = conn.execute("SELECT COALESCE(SUM(revenue),0) FROM performance_links").fetchone()[0]
    conn.close()
    return {
        "total_assets": total,
        "with_preview_file": with_file,
        "by_type": by_type,
        "by_source": by_source,
        "by_tag_source": by_tag_source,
        "linked_assets": len(linked_ids),
        "linked_performance": len(linked_ids),
        "coverage_rate": round(len(linked_ids) / total, 4) if total else 0,
        "total_spend": round(spend, 2),
        "total_revenue": round(revenue, 2),
        "roi": round(revenue / spend, 2) if spend > 0 else 0,
    }


def performance_report(platform: str | None = None) -> list[dict[str, Any]]:
    conn = get_db()
    where, params = ["1=1"], []
    if platform:
        where, params = ["p.platform = ?"], [platform]
    rows = conn.execute(
        f"""
        SELECT a.asset_id, a.name, a.asset_type, a.tags, a.source,
               p.store_name, p.platform, p.impressions, p.clicks, p.conversions,
               p.spend, p.revenue, p.period_start, p.period_end,
               CASE WHEN p.impressions > 0 THEN ROUND(p.clicks * 1.0 / p.impressions, 4) ELSE 0 END as ctr,
               CASE WHEN p.clicks > 0 THEN ROUND(p.conversions * 1.0 / p.clicks, 4) ELSE 0 END as cvr,
               CASE WHEN p.spend > 0 THEN ROUND(p.revenue / p.spend, 2) ELSE 0 END as roi
        FROM performance_links p
        JOIN assets a ON a.asset_id = p.asset_id
        WHERE {' AND '.join(where)}
        ORDER BY p.revenue DESC
        """,
        params,
    ).fetchall()
    conn.close()
    items = []
    for r in rows:
        item = dict(r)
        item["tags"] = normalize_tags(item.get("tags"))
        items.append(item)
    return items
