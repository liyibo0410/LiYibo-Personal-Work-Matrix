"""Integration tests for the P06 data-platform HTTP API.

These exercise the real request path (route → DuckDB/SQLAlchemy → response)
against a cold-started sample warehouse, covering the acceptance gates:
ETL output present, metric API returns data, lineage graph navigable,
CSV/JSON ingestion works, and destructive SQL is blocked at the API boundary.
"""

from __future__ import annotations


# ── Health & info ────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "healthy"


def test_info_reports_all_four_layers(client):
    body = client.get("/api/v1/info").json()["data"]
    assert body["tables"] > 0
    assert body["total_rows"] > 0
    for layer in ("ODS", "DWD", "DWS", "ADS"):
        assert body["layers"][layer], f"{layer} layer should be populated by the ETL"


# ── Tables ───────────────────────────────────────────────────────

def test_list_tables_includes_core_tables(client):
    tables = {t["table_name"] for t in client.get("/api/v1/tables").json()["data"]}
    assert {"ods_orders", "dwd_order_detail", "dws_daily_shop", "ads_key_metrics"} <= tables


def test_get_table_detail(client):
    data = client.get("/api/v1/tables/ods_orders").json()["data"]
    assert data["row_count"] > 0
    col_names = {c["name"] for c in data["columns"]}
    assert {"order_id", "total_amount", "status"} <= col_names


def test_get_missing_table_returns_404(client):
    resp = client.get("/api/v1/tables/does_not_exist")
    assert resp.status_code == 404
    assert resp.json()["code"] == 1


def test_preview_returns_rows(client):
    data = client.get("/api/v1/tables/ods_orders/preview?limit=5").json()["data"]
    assert data["count"] == 5
    assert len(data["rows"]) == 5


def test_column_stats_numeric(client):
    data = client.get("/api/v1/tables/ods_orders/columns/total_amount/stats").json()["data"]
    assert data["total"] > 0
    assert data["min_val"] is not None
    assert data["max_val"] >= data["min_val"]


# ── Query safety ─────────────────────────────────────────────────

def test_query_select_allowed(client):
    data = client.post("/api/v1/query", json={"sql": "SELECT COUNT(*) AS n FROM ods_orders"}).json()["data"]
    assert data["rows"][0]["n"] > 0


def test_query_blocks_destructive_sql(client):
    for sql in ("DROP TABLE ods_orders", "DELETE FROM ods_orders", "TRUNCATE ods_orders"):
        resp = client.post("/api/v1/query", json={"sql": sql})
        assert resp.status_code == 400, sql
        assert resp.json()["code"] == 1
    # The table must survive the blocked attempts.
    assert client.get("/api/v1/tables/ods_orders").status_code == 200


def test_query_rejects_empty_sql(client):
    resp = client.post("/api/v1/query", json={"sql": "   "})
    assert resp.status_code == 400


# ── Metrics ──────────────────────────────────────────────────────

def test_list_metrics(client):
    metrics = client.get("/api/v1/metrics").json()["data"]
    codes = {m["code"] for m in metrics}
    assert {"gmv", "order_count", "conversion_rate", "avg_order_value", "return_rate"} <= codes


def test_query_gmv_metric_returns_timeseries(client):
    data = client.get("/api/v1/metrics/gmv/query?granularity=day").json()["data"]
    assert data["metric"]["code"] == "gmv"
    assert len(data["data"]) > 0
    assert data["summary"]["total"] > 0
    assert "avg" in data["summary"]


def test_query_unknown_metric_returns_404(client):
    resp = client.get("/api/v1/metrics/not_a_metric/query")
    assert resp.status_code == 404


def test_metrics_summary(client):
    data = client.get("/api/v1/metrics/summary").json()["data"]
    assert len(data) >= 5
    gmv = next(m for m in data if m["code"] == "gmv")
    assert gmv["latest"] is not None


# ── Quality ──────────────────────────────────────────────────────

def test_quality_check_returns_health(client):
    data = client.get("/api/v1/quality/check").json()["data"]
    assert len(data["checks"]) > 0
    health = data["health"]
    assert 0 <= health["score"] <= 100
    assert health["total_checks"] == len(data["checks"])
    assert health["total_checks"] == health["passed"] + health["warned"] + health["failed"]


def test_quality_health_endpoint(client):
    data = client.get("/api/v1/quality/health").json()["data"]
    assert "score" in data
    assert "checks" in data


# ── Lineage ──────────────────────────────────────────────────────

def test_lineage_full_graph(client):
    data = client.get("/api/v1/lineage").json()["data"]
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0
    node_ids = {n["id"] for n in data["nodes"]}
    for edge in data["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def test_lineage_table_upstream_downstream(client):
    data = client.get("/api/v1/lineage/dwd_order_detail").json()["data"]
    upstream_sources = {u["source"] for u in data["upstream"]}
    downstream_targets = {d["target"] for d in data["downstream"]}
    assert "ods_orders" in upstream_sources
    assert "dws_daily_shop" in downstream_targets


def test_add_lineage_edge(client):
    payload = {"source": "ods_orders", "target": "ads_custom", "transform_type": "AGGREGATE", "description": "test edge"}
    resp = client.post("/api/v1/lineage", json=payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["target_table"] == "ads_custom"
    graph = client.get("/api/v1/lineage").json()["data"]
    assert any(e["target"] == "ads_custom" for e in graph["edges"])


# ── Ingestion ────────────────────────────────────────────────────

def test_ingest_csv(client):
    csv_bytes = b"id,name,amount\n1,apple,10.5\n2,banana,20\n3,cherry,30.25\n"
    resp = client.post(
        "/api/v1/ingest/csv?table_name=ods_test_csv&layer=ODS&display_name=CSV%E6%B5%8B%E8%AF%95",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["row_count"] == 3
    types = {c["name"]: c["type"] for c in data["column_details"]}
    assert types["id"] == "INTEGER"
    assert types["amount"] == "DOUBLE"
    assert types["name"] == "VARCHAR"
    # The ingested table is queryable and registered.
    assert client.get("/api/v1/tables/ods_test_csv").status_code == 200


def test_ingest_json(client):
    json_bytes = b'[{"sku": "A1", "qty": 5}, {"sku": "A2", "qty": 7}]'
    resp = client.post(
        "/api/v1/ingest/json?table_name=ods_test_json",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["row_count"] == 2


def test_ingest_rejects_non_csv(client):
    resp = client.post(
        "/api/v1/ingest/csv?table_name=ods_bad",
        files={"file": ("data.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


# ── Dashboard ────────────────────────────────────────────────────

def test_dashboard_aggregate(client):
    data = client.get("/api/v1/dashboard").json()["data"]
    assert data["table_count"] > 0
    assert data["total_rows"] > 0
    assert "health" in data
    assert len(data["metrics"]) >= 5
