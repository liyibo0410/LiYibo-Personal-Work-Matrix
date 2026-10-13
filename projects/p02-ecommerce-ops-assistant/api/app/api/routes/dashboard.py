from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user, require_owner_permission
from app.db.session import get_db
from app.models import Product, Store, StoreStatus, User
from app.services import data_platform_client

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
SessionDep = Annotated[Session, Depends(get_db)]


@router.get("/overview")
def boss_dashboard(
    db: SessionDep,
    _current_user: Annotated[User, Depends(require_owner_permission)],
) -> dict:
    """老板经营总览，仅 OWNER 可访问。

    店铺/商品数来自 P02 自身库；核心经营指标（GMV/订单量/转化率/客单价等）
    **跨模块真实调用 P06 数据中台指标 API**（端口由 SERVICE_REGISTRY 解析）。
    P06 不可达时降级：metrics 为空 + metrics_source="unavailable"，前端明确标注。
    """
    total_stores = db.scalar(select(func.count(Store.id))) or 0
    active_stores = (
        db.scalar(select(func.count(Store.id)).where(Store.status == StoreStatus.ACTIVE)) or 0
    )
    total_products = db.scalar(select(func.count(Product.id))) or 0

    p06 = data_platform_client.fetch_metrics_summary()

    return {
        "total_stores": total_stores,
        "active_stores": active_stores,
        "total_products": total_products,
        "summary": "经营数据概览（仅老板可见）",
        # ---- P06 数据中台跨模块指标 ----
        "metrics": p06.get("metrics", []) if p06.get("ok") else [],
        "metrics_source": p06.get("source", "unavailable"),
        "metrics_degraded": bool(p06.get("degraded")),
        "metrics_error": p06.get("error", ""),
    }

