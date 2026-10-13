"""Data lineage tracking - source to consumption flow."""

from __future__ import annotations

from typing import Any

from app.models import LineageEdge, get_session


# ── Pre-defined lineage for sample data ─────────────────────────

DEFAULT_LINEAGE = [
    # ODS → DWD
    ("ods_orders", "dwd_order_detail", "JOIN", "订单表关联店铺、商品、客户维度"),
    ("ods_stores", "dwd_order_detail", "JOIN", "店铺维度关联到订单明细"),
    ("ods_products", "dwd_order_detail", "JOIN", "商品维度关联到订单明细"),
    ("ods_customers", "dwd_order_detail", "JOIN", "客户维度关联到订单明细"),
    ("ods_customers", "dwd_customer_profile", "AGGREGATE", "客户基础信息 + 订单汇总统计"),
    ("ods_orders", "dwd_customer_profile", "AGGREGATE", "客户消费行为聚合"),
    # DWD → DWS
    ("dwd_order_detail", "dws_daily_shop", "AGGREGATE", "按店铺+日期聚合订单数据"),
    ("dwd_order_detail", "dws_daily_product", "AGGREGATE", "按商品+日期聚合销售数据"),
    # DWS + ODS → ADS
    ("dws_daily_shop", "ads_key_metrics", "AGGREGATE", "全店日度汇总至核心指标"),
    ("ods_traffic", "ads_key_metrics", "JOIN", "流量数据关联到核心指标"),
    ("dws_daily_product", "ads_product_ranking", "DERIVE", "商品维度排行计算"),
]


def register_default_lineage() -> None:
    """Insert default lineage edges into metadata DB."""
    session = get_session()
    try:
        # Check if already exists
        existing = session.query(LineageEdge).count()
        if existing > 0:
            return

        for source, target, transform, desc in DEFAULT_LINEAGE:
            edge = LineageEdge(
                source_table=source,
                target_table=target,
                transform_type=transform,
                description=desc,
            )
            session.add(edge)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_edge(source: str, target: str, transform_type: str = "ETL", description: str = "") -> dict:
    """Register a new lineage edge."""
    session = get_session()
    try:
        edge = LineageEdge(
            source_table=source,
            target_table=target,
            transform_type=transform_type,
            description=description,
        )
        session.add(edge)
        session.commit()
        return {
            "source_table": source,
            "target_table": target,
            "transform_type": transform_type,
            "description": description,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_full_graph() -> dict[str, Any]:
    """Return the complete lineage graph as nodes and edges."""
    session = get_session()
    try:
        edges = session.query(LineageEdge).all()
        edge_list = [
            {
                "source": e.source_table,
                "target": e.target_table,
                "transform_type": e.transform_type,
                "description": e.description,
            }
            for e in edges
        ]

        # Collect unique nodes
        node_names = set()
        for e in edges:
            node_names.add(e.source_table)
            node_names.add(e.target_table)

        # Assign layers based on naming convention
        layer_map = {
            "ods_": "ODS",
            "dwd_": "DWD",
            "dws_": "DWS",
            "ads_": "ADS",
        }
        nodes = []
        for name in sorted(node_names):
            layer = "UNKNOWN"
            for prefix, l in layer_map.items():
                if name.startswith(prefix):
                    layer = l
                    break
            nodes.append({"id": name, "layer": layer})

        return {"nodes": nodes, "edges": edge_list}
    finally:
        session.close()


def get_table_lineage(table_name: str) -> dict[str, Any]:
    """Get upstream and downstream lineage for a specific table."""
    session = get_session()
    try:
        # Upstream: tables that feed INTO this table
        upstream_edges = (
            session.query(LineageEdge)
            .filter(LineageEdge.target_table == table_name)
            .all()
        )
        # Downstream: tables that this table feeds INTO
        downstream_edges = (
            session.query(LineageEdge)
            .filter(LineageEdge.source_table == table_name)
            .all()
        )

        upstream = [
            {
                "source": e.source_table,
                "transform_type": e.transform_type,
                "description": e.description,
            }
            for e in upstream_edges
        ]
        downstream = [
            {
                "target": e.target_table,
                "transform_type": e.transform_type,
                "description": e.description,
            }
            for e in downstream_edges
        ]

        return {
            "table": table_name,
            "upstream": upstream,
            "downstream": downstream,
        }
    finally:
        session.close()
