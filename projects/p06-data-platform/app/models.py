"""SQLAlchemy metadata models - stored in SQLite alongside DuckDB."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship

_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE_DIR / "data"
_DATA_DIR.mkdir(exist_ok=True)
_META_DB = str(_DATA_DIR / "metadata.db")


class Base(DeclarativeBase):
    pass


# ── Table Registry ─────────────────────────────────────────────

class TableRegistry(Base):
    """Registered data tables with layer classification."""
    __tablename__ = "table_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(128), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False, default="")
    layer = Column(String(16), nullable=False, default="ODS")  # ODS/DWD/DWS/ADS
    description = Column(Text, default="")
    row_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    columns = relationship("ColumnMetadata", back_populates="table", cascade="all, delete-orphan")


class ColumnMetadata(Base):
    """Column-level metadata for registered tables."""
    __tablename__ = "column_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("table_registry.id"), nullable=False)
    column_name = Column(String(128), nullable=False)
    display_name = Column(String(128), default="")
    data_type = Column(String(64), default="")
    description = Column(Text, default="")
    is_nullable = Column(Boolean, default=True)
    is_partition = Column(Boolean, default=False)
    ordinal_position = Column(Integer, default=0)

    table = relationship("TableRegistry", back_populates="columns")


# ── Quality Results ────────────────────────────────────────────

class QualityResult(Base):
    """Data quality check results."""
    __tablename__ = "quality_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(128), nullable=False, index=True)
    check_type = Column(String(64), nullable=False)   # null_rate / duplication / anomaly / freshness
    check_name = Column(String(128), nullable=False, default="")
    column_name = Column(String(128), default="")
    status = Column(String(16), nullable=False, default="PASS")  # PASS / WARN / FAIL
    severity = Column(String(16), default="INFO")  # INFO / WARN / CRITICAL
    metric_value = Column(Float, default=0.0)
    threshold = Column(Float, default=0.0)
    details = Column(Text, default="")
    checked_at = Column(DateTime, default=datetime.utcnow)


# ── Lineage ────────────────────────────────────────────────────

class LineageEdge(Base):
    """Directed edge in the data lineage graph."""
    __tablename__ = "lineage_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_table = Column(String(128), nullable=False, index=True)
    target_table = Column(String(128), nullable=False, index=True)
    transform_type = Column(String(32), default="ETL")  # ETL / AGGREGATE / DERIVE / JOIN
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Metric Definitions ─────────────────────────────────────────

class MetricDefinition(Base):
    """Registered metric codes and their SQL definitions."""
    __tablename__ = "metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    unit = Column(String(32), default="")
    source_table = Column(String(128), default="")
    aggregation = Column(String(16), default="SUM")  # SUM / AVG / COUNT / RATIO
    formula = Column(Text, default="")


# ── Database session ────────────────────────────────────────────

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{_META_DB}", echo=False)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


def init_db() -> None:
    """Create all metadata tables."""
    Base.metadata.create_all(get_engine())


def get_session() -> Session:
    """Return a new database session."""
    factory = get_session_factory()
    return factory()
