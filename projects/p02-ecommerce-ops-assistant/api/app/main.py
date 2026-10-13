import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    agent_platform,
    agent_runs,
    auth,
    dashboard,
    health,
    model_settings,
    products,
    promotion_links,
    stores,
    users,
    workspace,
)
from app.core.config import API_DIR
from app.core.config import get_settings
from app.observability import configure_observability


settings = get_settings()
configure_observability()
uploads_dir = API_DIR / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
# 登记 webp 等媒体类型，避免 StaticFiles 以 application/octet-stream 返回导致浏览器不渲染。
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(agent_platform.router, prefix="/api/v1")
app.include_router(agent_runs.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(stores.router, prefix="/api/v1")
app.include_router(promotion_links.router, prefix="/api/v1")
app.include_router(model_settings.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
