"""Unit tests for P06 pure-logic helpers.

Focused on the acceptance gate "质量校验能抓到故意注入的脏数据" plus the
type-inference and health-score maths, using an isolated in-memory DuckDB so
no test depends on the randomly generated sample warehouse.
"""

from __future__ import annotations

import pytest

from app import quality
from app.ingestion import _infer_type, _normalize_column_name
from app.metrics import METRIC_REGISTRY, query_metric


# ── Health score maths ───────────────────────────────────────────

def test_compute_health_score_perfect():
    results = [{"status": "PASS"} for _ in range(10)]
    health = quality.compute_health_score(results)
    assert health["score"] == 100
    assert health["passed"] == 10
    assert health["failed"] == 0


def test_compute_health_score_penalises_warn_and_fail():
    results = [{"status": "PASS"}, {"status": "PASS"}, {"status": "WARN"}, {"status": "FAIL"}]
    health = quality.compute_health_score(results)
    # base = 2/4 * 100 = 50; penalty = 1*2 + 1*5 = 7 → 43
    assert health["score"] == 43
    assert health["total_checks"] == 4
    assert health["warned"] == 1
    assert health["failed"] == 1


def test_compute_health_score_empty():
    health = quality.compute_health_score([])
    assert health == {"score": 0, "total_checks": 0, "passed": 0, "warned": 0, "failed": 0}


def test_health_score_never_negative():
    results = [{"status": "FAIL"} for _ in range(5)]
    assert quality.compute_health_score(results)["score"] == 0


# ── Dirty-data detection (injected) ──────────────────────────────

def test_value_range_flags_injected_negative_amounts(memdb):
    memdb.execute("CREATE TABLE dirty_orders (order_id VARCHAR, total_amount DOUBLE)")
    # 9 clean rows + 3 deliberately dirty (negative) rows → 25% outliers → FAIL
    clean = [("C%02d" % i, 100.0 + i) for i in range(9)]
    dirty = [("D%02d" % i, -50.0 - i) for i in range(3)]
    memdb.executemany("INSERT INTO dirty_orders VALUES (?, ?)", clean + dirty)

    results = quality.check_value_range("dirty_orders", "total_amount", min_val=0)
    assert len(results) == 1
    check = results[0]
    assert check["status"] == "FAIL"
    assert check["severity"] == "CRITICAL"
    assert check["metric_value"] == pytest.approx(0.25, abs=1e-6)


def test_value_range_passes_clean_column(memdb):
    memdb.execute("CREATE TABLE clean_orders (order_id VARCHAR, total_amount DOUBLE)")
    memdb.executemany(
        "INSERT INTO clean_orders VALUES (?, ?)",
        [("A%02d" % i, 50.0 + i) for i in range(20)],
    )
    check = quality.check_value_range("clean_orders", "total_amount", min_val=0)[0]
    assert check["status"] == "PASS"
    assert check["metric_value"] == 0.0


def test_null_rate_flags_heavily_null_column(memdb):
    memdb.execute("CREATE TABLE nullish (id INTEGER, note VARCHAR)")
    rows = [(i, None if i % 2 == 0 else "x") for i in range(10)]  # 50% null on note
    memdb.executemany("INSERT INTO nullish VALUES (?, ?)", rows)
    checks = {c["column_name"]: c for c in quality.check_null_rates("nullish")}
    # 50% null → boundary: >0.5 is FAIL, ==0.5 is WARN
    assert checks["note"]["status"] == "WARN"
    assert checks["note"]["metric_value"] == pytest.approx(0.5)


def test_duplicate_detection(memdb):
    memdb.execute("CREATE TABLE dupes (a INTEGER, b VARCHAR)")
    memdb.executemany(
        "INSERT INTO dupes VALUES (?, ?)",
        [(1, "x"), (1, "x"), (1, "x"), (2, "y")],  # 2 duplicate rows of 4 → 50%
    )
    check = quality.check_duplicates("dupes")[0]
    assert check["status"] == "FAIL"
    assert check["metric_value"] == pytest.approx(0.5)


# ── Type inference & column normalisation ────────────────────────

@pytest.mark.parametrize(
    "values,expected",
    [
        (["1", "2", "3"], "INTEGER"),
        (["1.5", "2", "3.0"], "DOUBLE"),
        (["2024-01-01", "2024-02-15"], "TIMESTAMP"),
        (["true", "false", "true"], "BOOLEAN"),
        (["apple", "banana"], "VARCHAR"),
        (["", "  "], "VARCHAR"),
    ],
)
def test_infer_type(values, expected):
    assert _infer_type(values) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Order ID", "order_id"),
        ("total-amount", "total_amount"),
        ("  Spaced  ", "spaced"),
        ("2024col", "col_2024col"),
        ("", "unnamed"),
    ],
)
def test_normalize_column_name(raw, expected):
    assert _normalize_column_name(raw) == expected


# ── Metric registry sanity ───────────────────────────────────────

def test_unknown_metric_raises_valueerror():
    with pytest.raises(ValueError):
        query_metric("does_not_exist")


def test_all_registered_metrics_have_required_fields():
    for code, meta in METRIC_REGISTRY.items():
        assert meta["source_table"], code
        assert meta["value_column"] is not None, code
        assert meta["aggregation"] in ("SUM", "AVG", "COUNT"), code
