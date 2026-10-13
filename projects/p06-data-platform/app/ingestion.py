"""Data ingestion - CSV and JSON file upload with auto-schema detection."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from app import duckdb_engine as db
from app.models import TableRegistry, ColumnMetadata, get_session
from app import lineage as lineage_module


# ── Type inference ───────────────────────────────────────────────

def _infer_type(values: list[str]) -> str:
    """Infer DuckDB type from a sample of string values."""
    non_null = [v for v in values if v and v.strip() != ""]
    if not non_null:
        return "VARCHAR"

    # Try integer
    try:
        for v in non_null[:100]:
            int(v)
        return "INTEGER"
    except (ValueError, TypeError):
        pass

    # Try float
    try:
        for v in non_null[:100]:
            float(v)
        return "DOUBLE"
    except (ValueError, TypeError):
        pass

    # Try date
    date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
    for fmt in date_formats:
        try:
            for v in non_null[:100]:
                datetime.strptime(v.strip(), fmt)
            return "TIMESTAMP"
        except (ValueError, TypeError):
            continue

    # Try boolean
    bool_vals = {"true", "false", "0", "1", "yes", "no"}
    if all(v.strip().lower() in bool_vals for v in non_null[:100]):
        return "BOOLEAN"

    return "VARCHAR"


def _normalize_column_name(name: str) -> str:
    """Clean column name for DuckDB compatibility."""
    name = name.strip().lower()
    name = name.replace(" ", "_").replace("-", "_").replace(".", "_")
    name = "".join(c for c in name if c.isalnum() or c == "_")
    if name and name[0].isdigit():
        name = f"col_{name}"
    return name or "unnamed"


# ── CSV ingestion ────────────────────────────────────────────────

def ingest_csv(
    content: bytes,
    table_name: str,
    layer: str = "ODS",
    display_name: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Parse CSV content, create table in DuckDB, register in metadata."""
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    headers = next(reader)
    headers = [_normalize_column_name(h) for h in headers]

    # Read all rows
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file is empty (no data rows)")

    # Infer types from first 1000 rows
    sample = rows[:1000]
    col_types = []
    for i, h in enumerate(headers):
        col_values = [row[i] if i < len(row) else "" for row in sample]
        col_types.append(_infer_type(col_values))

    # Create table in DuckDB
    conn = db.get_conn()
    col_defs = ", ".join(f'"{h}" {t}' for h, t in zip(headers, col_types))
    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    # Insert data
    placeholders = ", ".join(["?"] * len(headers))
    insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'

    # Convert values to proper types
    converted_rows = []
    for row in rows:
        converted = []
        for i, val in enumerate(row):
            if i >= len(headers):
                break
            target_type = col_types[i]
            try:
                if val == "" or val is None:
                    converted.append(None)
                elif target_type == "INTEGER":
                    converted.append(int(val))
                elif target_type == "DOUBLE":
                    converted.append(float(val))
                elif target_type == "BOOLEAN":
                    converted.append(val.strip().lower() in ("true", "1", "yes"))
                else:
                    converted.append(val)
            except (ValueError, TypeError):
                converted.append(None)
        # Pad row if needed
        while len(converted) < len(headers):
            converted.append(None)
        converted_rows.append(converted)

    conn.executemany(insert_sql, converted_rows)

    # Register in metadata
    _register_table(table_name, display_name or table_name, layer, description, headers, col_types, len(rows))

    return {
        "table_name": table_name,
        "row_count": len(rows),
        "columns": len(headers),
        "column_details": [{"name": h, "type": t} for h, t in zip(headers, col_types)],
    }


# ── JSON ingestion ───────────────────────────────────────────────

def ingest_json(
    content: bytes,
    table_name: str,
    layer: str = "ODS",
    display_name: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Parse JSON content (array of objects), create table, register."""
    data = json.loads(content.decode("utf-8"))

    if isinstance(data, dict):
        # Try common keys
        for key in ("data", "records", "rows", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            data = [data]

    if not isinstance(data, list) or not data:
        raise ValueError("JSON must be an array of objects or contain a 'data' array")

    # Extract headers from first record
    headers = list(data[0].keys())
    headers = [_normalize_column_name(h) for h in headers]

    # Infer types
    sample = data[:1000]
    col_types = []
    for i, h in enumerate(headers):
        values = [str(row.get(headers[i], "")) for row in sample]
        col_types.append(_infer_type(values))

    # Create table
    conn = db.get_conn()
    col_defs = ", ".join(f'"{h}" {t}' for h, t in zip(headers, col_types))
    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    # Insert
    placeholders = ", ".join(["?"] * len(headers))
    insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'

    converted_rows = []
    for record in data:
        converted = []
        for i, h in enumerate(headers):
            val = record.get(h, record.get(headers[i]))
            target_type = col_types[i]
            try:
                if val is None or val == "":
                    converted.append(None)
                elif target_type == "INTEGER":
                    converted.append(int(val))
                elif target_type == "DOUBLE":
                    converted.append(float(val))
                elif target_type == "BOOLEAN":
                    converted.append(bool(val))
                else:
                    converted.append(str(val))
            except (ValueError, TypeError):
                converted.append(None)
        converted_rows.append(converted)

    conn.executemany(insert_sql, converted_rows)

    _register_table(table_name, display_name or table_name, layer, description, headers, col_types, len(data))

    return {
        "table_name": table_name,
        "row_count": len(data),
        "columns": len(headers),
        "column_details": [{"name": h, "type": t} for h, t in zip(headers, col_types)],
    }


# ── Metadata registration ───────────────────────────────────────

def _register_table(
    table_name: str,
    display_name: str,
    layer: str,
    description: str,
    headers: list[str],
    col_types: list[str],
    row_count: int,
) -> None:
    """Register table and columns in the metadata database."""
    session = get_session()
    try:
        # Upsert table registry
        existing = session.query(TableRegistry).filter_by(table_name=table_name).first()
        if existing:
            existing.display_name = display_name
            existing.layer = layer
            existing.description = description
            existing.row_count = row_count
            existing.updated_at = datetime.utcnow()
            # Clear old columns
            session.query(ColumnMetadata).filter_by(table_id=existing.id).delete()
            table_id = existing.id
        else:
            tbl = TableRegistry(
                table_name=table_name,
                display_name=display_name,
                layer=layer,
                description=description,
                row_count=row_count,
            )
            session.add(tbl)
            session.flush()
            table_id = tbl.id

        # Add columns
        for i, (h, t) in enumerate(zip(headers, col_types)):
            col = ColumnMetadata(
                table_id=table_id,
                column_name=h,
                display_name=h,
                data_type=t,
                is_nullable=True,
                ordinal_position=i,
            )
            session.add(col)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
