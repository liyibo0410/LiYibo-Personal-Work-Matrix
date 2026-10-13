"""本地一键启动（开发模式，免外部依赖）。

使用 SQLite 作为业务库、inline 任务队列替代 Celery/Redis，
无需 MySQL、Redis、PostgreSQL 即可把后端跑起来做联调与验收。

用法：
    cd api
    ..\\venv\\Scripts\\python.exe scripts/run_local_dev.py
或（用项目 venv 的 python）：
    python scripts/run_local_dev.py

启动后访问 Swagger： http://127.0.0.1:8000/docs
首次启动会自动建表；首个管理员账号用 scripts/bootstrap_user.py 初始化。
"""

import os
import sys

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# API_DIR = .../面试项目/projects/p02-ecommerce-ops-assistant/api
# 向上 3 级到工作区根（面试项目/）
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(API_DIR)))
SHARED_LLM_GATEWAY = os.path.join(WORKSPACE_ROOT, "shared", "llm-gateway", "src")
if os.path.isdir(SHARED_LLM_GATEWAY):
    sys.path.insert(0, os.path.abspath(SHARED_LLM_GATEWAY))

# 开发模式环境变量：覆盖 api/.env 中的 MySQL / redis 配置。
os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL", "sqlite:///" + os.path.join(API_DIR, "local_dev.db")
)
os.environ["TASK_QUEUE_BACKEND"] = os.getenv("TASK_QUEUE_BACKEND", "inline")
os.environ["APP_ENV"] = os.getenv("APP_ENV", "development")
os.environ.setdefault(
    "AUTH_SECRET_KEY", "dev-change-me-but-use-a-long-random-32-char-secret"
)

# 接入用户在 api/.env.sqlite 中填入的真实模型密钥（阿里云 MaaS 等）。
# api/.env 中的 LLM/IMAGE/VIDEO 留空时，这里用 .env.sqlite 的真实值覆盖，
# 保证“本地开发一键启动”即可真实调用大模型；.env.sqlite 已加入 .gitignore，避免密钥入库。
_ENV_SQLITE = os.path.join(API_DIR, ".env.sqlite")
if os.path.exists(_ENV_SQLITE):
    _MODEL_KEYS = (
        "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
        "IMAGE_PROVIDER", "IMAGE_BASE_URL", "IMAGE_API_KEY", "IMAGE_MODEL",
        "IMAGE_SIZE", "IMAGE_WORKSPACE_ID",
        "VIDEO_PROVIDER", "VIDEO_BASE_URL", "VIDEO_API_KEY", "VIDEO_MODEL",
        "VIDEO_SIZE", "VIDEO_DURATION", "VIDEO_WORKSPACE_ID",
        "API_CORS_ORIGINS",
    )
    with open(_ENV_SQLITE, "r", encoding="utf-8") as _fh:
        for _line in _fh:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k in _MODEL_KEYS and _v:
                os.environ[_k] = _v

sys.path.insert(0, API_DIR)

import uvicorn  # noqa: E402


def main() -> int:
    """读取环境配置并启动本地开发服务器，返回进程退出码。"""
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    print(
        f"[local-dev] DATABASE_URL={os.environ['DATABASE_URL']} "
        f"TASK_QUEUE_BACKEND={os.environ['TASK_QUEUE_BACKEND']}"
    )
    print(f"[local-dev] Swagger: http://{host}:{port}/docs")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
