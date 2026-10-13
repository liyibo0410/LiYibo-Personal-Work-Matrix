"""Shared fixtures for P06 data-platform tests.

The DuckDB analytics engine and the SQLAlchemy metadata store both bind to
file-based singletons under ``data/`` at import time. To keep tests isolated
from the developer's real warehouse, we redirect both paths to a temp dir and
reset the singletons *before* the FastAPI lifespan runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `import app.*` work regardless of the cwd pytest is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    """FastAPI TestClient backed by isolated temp DuckDB + metadata databases.

    Entering the client context triggers the app lifespan, which initialises the
    metadata DB, generates the full sample warehouse (ODS→DWD→DWS→ADS) and
    registers default lineage — exactly like a real cold start.
    """
    tmp = tmp_path_factory.mktemp("p06data")

    from app import duckdb_engine, models

    old_db_path = duckdb_engine._DB_PATH
    old_conn = duckdb_engine._conn
    old_meta = models._META_DB
    old_engine = models._engine
    old_factory = models._SessionLocal

    duckdb_engine._DB_PATH = str(tmp / "analytics.duckdb")
    duckdb_engine._conn = None
    models._META_DB = str(tmp / "metadata.db")
    models._engine = None
    models._SessionLocal = None

    from fastapi.testclient import TestClient

    from app.main import app

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        duckdb_engine.close()
        duckdb_engine._DB_PATH = old_db_path
        duckdb_engine._conn = old_conn
        models._META_DB = old_meta
        models._engine = old_engine
        models._SessionLocal = old_factory


@pytest.fixture
def memdb():
    """Swap the DuckDB singleton for a fresh in-memory connection.

    Used by pure-logic unit tests that need full control over the data (e.g.
    injecting deliberately dirty rows) without touching the sample warehouse.
    """
    import duckdb

    from app import duckdb_engine

    old_conn = duckdb_engine._conn
    conn = duckdb.connect(":memory:")
    duckdb_engine._conn = conn
    try:
        yield conn
    finally:
        conn.close()
        duckdb_engine._conn = old_conn
