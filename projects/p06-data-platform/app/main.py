"""P06 Data Platform - CloudPivot 数据中台

FastAPI application entry point. Run with: python -m app.main
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Ensure project root (parent of app/) is on sys.path so `from app.xxx` works
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ── Logging ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("p06")

# ── Paths ────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# ── Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init metadata DB, generate sample data, register lineage."""
    logger.info("P06 Data Platform starting...")

    from app.models import init_db
    init_db()
    logger.info("Metadata database initialized")

    from app import sample_data
    from app import duckdb_engine as db

    # Generate sample data if tables don't exist
    if not db.table_exists("ods_orders"):
        logger.info("Generating sample e-commerce data...")
        sample_data.generate_all()
        logger.info("Sample data generation complete")
    else:
        logger.info("Sample data already exists, skipping generation")

    # Register lineage
    from app import lineage as lineage_module
    lineage_module.register_default_lineage()
    logger.info("Lineage registered")

    # Register all tables in metadata
    _sync_table_registry()

    logger.info("P06 Data Platform ready on port 8060")
    yield

    # Shutdown
    db.close()
    logger.info("P06 Data Platform shut down")


app = FastAPI(
    title="P06 数据中台 - CloudPivot",
    description="电商数据中台：数据接入 · OLAP分析 · 指标服务 · 数据质量 · 数据血缘",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一设计系统：挂载仓库根 shared/ 到 /shared，前端引用 tokens.css（配色唯一真源）+ ui-kit.js（主题桥接）
_SHARED_DIR = BASE_DIR.parent.parent / "shared"
if _SHARED_DIR.exists():
    app.mount("/shared", StaticFiles(directory=str(_SHARED_DIR)), name="shared")


# ── Response helpers ─────────────────────────────────────────────

def _serialize(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    return obj


def ok(data: Any = None, msg: str = "success") -> JSONResponse:
    return JSONResponse({"code": 0, "data": _serialize(data), "msg": msg})


def err(msg: str, code: int = 400) -> JSONResponse:
    return JSONResponse({"code": 1, "data": None, "msg": msg}, status_code=code)


# ── Pydantic models ──────────────────────────────────────────────

class QueryBody(BaseModel):
    sql: str = Field(..., description="SQL query to execute")


class LineageAdd(BaseModel):
    source: str
    target: str
    transform_type: str = "ETL"
    description: str = ""


class IngestMeta(BaseModel):
    table_name: str
    layer: str = "ODS"
    display_name: str = ""
    description: str = ""


# ── Health & Info ────────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    return ok({"status": "healthy", "service": "p06-data-platform"})


@app.get("/api/v1/info")
def info():
    from app import duckdb_engine as db
    tables = db.list_tables()
    total_rows = sum(db.table_row_count(t) for t in tables)
    return ok({
        "service": "P06 数据中台",
        "version": "1.0.0",
        "tables": len(tables),
        "total_rows": total_rows,
        "layers": {
            "ODS": [t for t in tables if t.startswith("ods_")],
            "DWD": [t for t in tables if t.startswith("dwd_")],
            "DWS": [t for t in tables if t.startswith("dws_")],
            "ADS": [t for t in tables if t.startswith("ads_")],
        },
    })


# ── Tables ───────────────────────────────────────────────────────

@app.get("/api/v1/tables")
def list_tables():
    """List all registered tables with metadata."""
    from app.models import get_session, TableRegistry
    session = get_session()
    try:
        tables = session.query(TableRegistry).order_by(TableRegistry.layer, TableRegistry.table_name).all()
        result = []
        for t in tables:
            result.append({
                "table_name": t.table_name,
                "display_name": t.display_name,
                "layer": t.layer,
                "description": t.description,
                "row_count": t.row_count,
                "column_count": len(t.columns),
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return ok(result)
    finally:
        session.close()


@app.get("/api/v1/tables/{table_name}")
def get_table(table_name: str):
    """Get table metadata and column info."""
    from app import duckdb_engine as db
    if not db.table_exists(table_name):
        return err(f"Table '{table_name}' not found", 404)

    info = db.table_info(table_name)
    row_count = db.table_row_count(table_name)

    from app.models import get_session, TableRegistry
    session = get_session()
    try:
        reg = session.query(TableRegistry).filter_by(table_name=table_name).first()
        meta = {
            "display_name": reg.display_name if reg else table_name,
            "layer": reg.layer if reg else "UNKNOWN",
            "description": reg.description if reg else "",
        } if reg else {}
    finally:
        session.close()

    return ok({
        "table_name": table_name,
        **meta,
        "row_count": row_count,
        "columns": info,
    })


@app.get("/api/v1/tables/{table_name}/preview")
def preview_table(table_name: str, limit: int = Query(50, ge=1, le=500)):
    """Preview table data."""
    from app import duckdb_engine as db
    if not db.table_exists(table_name):
        return err(f"Table '{table_name}' not found", 404)
    rows = db.preview(table_name, limit)
    return ok({"table_name": table_name, "rows": rows, "count": len(rows)})


@app.get("/api/v1/tables/{table_name}/columns/{column_name}/stats")
def get_column_stats(table_name: str, column_name: str):
    """Get column statistics."""
    from app import duckdb_engine as db
    if not db.table_exists(table_name):
        return err(f"Table '{table_name}' not found", 404)
    stats = db.column_stats(table_name, column_name)
    if "error" in stats:
        return err(stats["error"], 404)
    return ok({"table_name": table_name, "column_name": column_name, **stats})


# ── Query ────────────────────────────────────────────────────────

@app.post("/api/v1/query")
def execute_query(body: QueryBody):
    """Execute arbitrary SQL against DuckDB (read-only recommended)."""
    from app import duckdb_engine as db
    sql = body.sql.strip()
    if not sql:
        return err("SQL query is empty")

    # Safety: block destructive operations
    upper = sql.upper()
    for keyword in ("DROP ", "DELETE ", "TRUNCATE ", "ALTER ", "CREATE ", "INSERT ", "UPDATE "):
        if upper.startswith(keyword):
            return err(f"Operation not allowed: {keyword.strip()} is blocked via API")

    try:
        rows = db.execute(sql)
        return ok({"rows": rows, "count": len(rows)})
    except Exception as e:
        return err(f"Query error: {str(e)}")


# ── Metrics ──────────────────────────────────────────────────────

@app.get("/api/v1/metrics")
def list_metrics():
    """List all available metrics."""
    from app.metrics import list_metrics
    return ok(list_metrics())


@app.get("/api/v1/metrics/{code}/query")
def query_metric(
    code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    store_id: str | None = None,
):
    """Query a metric's time-series data."""
    from app.metrics import query_metric as _query
    try:
        result = _query(code, start_date, end_date, granularity, store_id)
        return ok(result)
    except ValueError as e:
        return err(str(e), 404)
    except Exception as e:
        return err(f"Metric query error: {str(e)}")


@app.get("/api/v1/metrics/summary")
def metrics_summary(
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Get latest summary for all metrics."""
    from app.metrics import query_all_summary
    return ok(query_all_summary(start_date, end_date))


# ── Quality ──────────────────────────────────────────────────────

@app.get("/api/v1/quality/check")
def run_quality_checks(table_name: str | None = None):
    """Run data quality checks."""
    from app.quality import run_all_checks, save_results, compute_health_score
    results = run_all_checks(table_name)
    save_results(results)
    health = compute_health_score(results)
    return ok({"checks": results, "health": health})


@app.get("/api/v1/quality/health")
def quality_health():
    """Get current data health score (runs checks if needed)."""
    from app.quality import run_all_checks, compute_health_score
    results = run_all_checks()
    health = compute_health_score(results)
    health["checks"] = results
    return ok(health)


# ── Lineage ──────────────────────────────────────────────────────

@app.get("/api/v1/lineage")
def get_lineage():
    """Get the full data lineage graph."""
    from app.lineage import get_full_graph
    return ok(get_full_graph())


@app.get("/api/v1/lineage/{table_name}")
def get_table_lineage(table_name: str):
    """Get lineage for a specific table."""
    from app.lineage import get_table_lineage as _get
    return ok(_get(table_name))


@app.post("/api/v1/lineage")
def add_lineage(body: LineageAdd):
    """Register a new lineage edge."""
    from app.lineage import add_edge
    result = add_edge(body.source, body.target, body.transform_type, body.description)
    return ok(result)


# ── Ingestion ────────────────────────────────────────────────────

@app.post("/api/v1/ingest/csv")
async def ingest_csv(
    file: UploadFile = File(...),
    table_name: str = Query(..., description="Target table name"),
    layer: str = Query("ODS", description="Warehouse layer"),
    display_name: str = Query("", description="Display name"),
    description: str = Query("", description="Table description"),
):
    """Upload and ingest a CSV file."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return err("Only CSV files are accepted")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB limit
        return err("File too large (max 100MB)")

    from app.ingestion import ingest_csv as _ingest
    try:
        result = _ingest(content, table_name, layer, display_name, description)
        return ok(result, msg=f"Successfully ingested {result['row_count']} rows")
    except Exception as e:
        return err(f"Ingestion error: {str(e)}")


@app.post("/api/v1/ingest/json")
async def ingest_json(
    file: UploadFile = File(...),
    table_name: str = Query(..., description="Target table name"),
    layer: str = Query("ODS", description="Warehouse layer"),
    display_name: str = Query("", description="Display name"),
    description: str = Query("", description="Table description"),
):
    """Upload and ingest a JSON file."""
    if not file.filename or not file.filename.lower().endswith(".json"):
        return err("Only JSON files are accepted")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        return err("File too large (max 100MB)")

    from app.ingestion import ingest_json as _ingest
    try:
        result = _ingest(content, table_name, layer, display_name, description)
        return ok(result, msg=f"Successfully ingested {result['row_count']} rows")
    except Exception as e:
        return err(f"Ingestion error: {str(e)}")


# ── Dashboard ────────────────────────────────────────────────────

@app.get("/api/v1/dashboard")
def dashboard():
    """Aggregate dashboard data: health, table counts, latest metrics."""
    from app import duckdb_engine as db
    from app.metrics import query_all_summary
    from app.quality import run_all_checks, compute_health_score

    tables = db.list_tables()
    total_rows = sum(db.table_row_count(t) for t in tables)

    # Quality
    quality_results = run_all_checks()
    health = compute_health_score(quality_results)

    # Metrics
    metrics = query_all_summary()

    # Layer counts
    layers = {}
    for t in tables:
        for prefix in ("ods_", "dwd_", "dws_", "ads_"):
            if t.startswith(prefix):
                layer = prefix[:-1].upper()
                layers[layer] = layers.get(layer, 0) + 1
                break

    return ok({
        "table_count": len(tables),
        "total_rows": total_rows,
        "layers": layers,
        "health": health,
        "metrics": metrics,
    })


# ── Static frontend ──────────────────────────────────────────────

@app.get("/")
def serve_frontend():
    """Serve the single-page frontend."""
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        return err("Frontend not found", 404)
    return FileResponse(str(index_path), media_type="text/html")


# ── Table registry sync ─────────────────────────────────────────

def _sync_table_registry():
    """Ensure all DuckDB tables are registered in metadata."""
    from app import duckdb_engine as db
    from app.models import get_session, TableRegistry, ColumnMetadata

    tables = db.list_tables()
    session = get_session()

    layer_map = {
        "ods_": "ODS",
        "dwd_": "DWD",
        "dws_": "DWS",
        "ads_": "ADS",
    }

    display_names = {
        "ods_orders": "原始订单表",
        "ods_products": "商品主数据",
        "ods_customers": "客户主数据",
        "ods_stores": "店铺主数据",
        "ods_traffic": "流量日志表",
        "dwd_order_detail": "订单明细宽表",
        "dwd_customer_profile": "客户画像表",
        "dws_daily_shop": "店铺日度汇总",
        "dws_daily_product": "商品日度汇总",
        "ads_key_metrics": "核心经营指标",
        "ads_product_ranking": "商品排行榜",
    }

    descriptions = {
        "ods_orders": "各渠道原始订单数据，包含订单号、客户、商品、金额、状态等",
        "ods_products": "商品主数据，包含SKU、名称、品类、售价、成本",
        "ods_customers": "客户主数据，包含昵称、性别、省份、注册日期",
        "ods_stores": "店铺主数据，包含店铺名称、平台、经营品类",
        "ods_traffic": "各渠道每日流量数据，UV/PV/跳出率",
        "dwd_order_detail": "订单明细宽表，关联店铺/商品/客户维度",
        "dwd_customer_profile": "客户画像，汇总消费行为指标",
        "dws_daily_shop": "按店铺+日期聚合的经营指标",
        "dws_daily_product": "按商品+日期聚合的销售指标",
        "ads_key_metrics": "全局核心指标：GMV/订单量/转化率/客单价/退货率/流量",
        "ads_product_ranking": "商品GMV排行榜，含日度排名",
    }

    try:
        for tbl_name in tables:
            existing = session.query(TableRegistry).filter_by(table_name=tbl_name).first()
            layer = "ODS"
            for prefix, l in layer_map.items():
                if tbl_name.startswith(prefix):
                    layer = l
                    break

            if existing:
                existing.row_count = db.table_row_count(tbl_name)
                existing.updated_at = __import__("datetime").datetime.utcnow()
            else:
                reg = TableRegistry(
                    table_name=tbl_name,
                    display_name=display_names.get(tbl_name, tbl_name),
                    layer=layer,
                    description=descriptions.get(tbl_name, ""),
                    row_count=db.table_row_count(tbl_name),
                )
                session.add(reg)
                session.flush()

                # Add column metadata
                cols = db.table_info(tbl_name)
                for i, c in enumerate(cols):
                    col = ColumnMetadata(
                        table_id=reg.id,
                        column_name=c["name"],
                        display_name=c["name"],
                        data_type=c["type"],
                        is_nullable=c["nullable"],
                        ordinal_position=i,
                    )
                    session.add(col)

        session.commit()
        logger.info(f"Table registry synced: {len(tables)} tables")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Entry point ──────────────────────────────────────────────────

def main():
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8060,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
