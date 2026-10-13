"""P07 AI 素材中心 · FastAPI 装配层。

分层：`api.py`（路由）→ `services/`（检索/打标/生成/媒体/跨模块）→ `repository.py`（数据）→ `db.py`（schema）。
配置与端口：模型凭证读仓库根 `.env`，跨模块地址从 `shared/config` 的 SERVICE_REGISTRY 解析。
"""
from __future__ import annotations

import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# `python app/main.py` 时 sys.path[0] 是 app/ 而不是项目根，`from app import ...` 必炸；
# 与 p06 同样的做法：显式把项目根补进 sys.path，让两种启动方式都能跑。
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from cloudpivot_config import port as service_port
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config, db
from app.api import router
from app.services import llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("p07")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    state = llm.status()
    logger.info(
        "[startup] P07 就绪 db=%s llm=%s model=%s endpoint=%s",
        config.DB_PATH, "已接入" if state["configured"] else "降级",
        state["model"] or "-", state["endpoint"] or "-",
    )
    yield
    logger.info("[shutdown] P07 关闭")


app = FastAPI(title="P07 AI 素材中心", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.middleware("http")
async def trace_and_timing(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:10]
    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    if request.url.path.startswith(("/api/", "/health")):
        logger.info(
            "[trace=%s] %s %s -> %s %.1fms",
            trace_id, request.method, request.url.path,
            response.status_code, (time.perf_counter() - t0) * 1000,
        )
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("未处理异常 path=%s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "P07_INTERNAL", "message": str(exc), "path": request.url.path}},
    )


# 统一设计系统：仓库根 shared/ 挂到 /shared（tokens.css 是配色唯一真源）
if (config.REPO_ROOT / "shared").is_dir():
    app.mount("/shared", StaticFiles(directory=str(config.REPO_ROOT / "shared")), name="shared")


@app.get("/health")
def health():
    state = llm.status()
    return {
        "status": "ok",
        "service": "P07 AI 素材中心",
        "version": app.version,
        "llm_configured": state["configured"],
        "llm_model": state["model"],
    }


if config.WEB_DIR.is_dir():
    @app.get("/")
    def index():
        return FileResponse(config.WEB_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    listen_port = int(service_port("p07"))
    logger.info("P07 AI 素材中心启动中 http://127.0.0.1:%s", listen_port)
    uvicorn.run(app, host="0.0.0.0", port=listen_port)
