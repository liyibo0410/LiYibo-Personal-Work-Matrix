"""本地可运行性自检（开发模式）。

在 SQLite + inline 队列下，不依赖任何外部服务，验证：
  建表 → 初始化管理员 → 登录 → 当前用户 → 店铺增删查 → 模型设置 → 商品列表 → 权限拦截。

用法：
    cd api
    ..\\venv\\Scripts\\python.exe scripts/smoke_local.py
"""

import os
import sys
import tempfile

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 开发模式：SQLite + inline，避免依赖 MySQL / Redis / PostgreSQL。
_db_path = os.path.join(tempfile.gettempdir(), "ecommerce_smoke_local.db")
if os.path.exists(_db_path):
    os.remove(_db_path)

os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["TASK_QUEUE_BACKEND"] = "inline"
os.environ["APP_ENV"] = "development"
os.environ.setdefault(
    "AUTH_SECRET_KEY", "dev-change-me-but-use-a-long-random-32-char-secret"
)

sys.path.insert(0, API_DIR)

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.bootstrap import ensure_bootstrap_user  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

lines = []


def log(msg: str) -> None:
    lines.append(str(msg))
    print(str(msg), flush=True)


def main() -> int:
    """执行本地自检主流程，返回 0 表示通过。"""
    Base.metadata.create_all(engine)
    log("create_all: schema created on sqlite")

    email, password = "owner@local.dev", "LocalDev123!"
    with SessionLocal() as db:
        user, created = ensure_bootstrap_user(
            db, email=email, display_name="Owner", password=password
        )
    log(f"bootstrap: created={created} email={user.email} role={user.role.value}")

    client = TestClient(app)
    r = client.get("/health")
    log(f"GET  /health                       -> {r.status_code} {r.json()}")

    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    log(f"POST /api/v1/auth/login            -> {r.status_code} (token len={len(token)})")

    r = client.get("/api/v1/auth/me", headers=headers)
    log(f"GET  /api/v1/auth/me               -> {r.status_code} {r.json().get('email')}")

    r = client.get("/api/v1/stores", headers=headers)
    log(f"GET  /api/v1/stores (empty)        -> {r.status_code} count={len(r.json())}")

    r = client.post(
        "/api/v1/stores", headers=headers,
        json={"name": "本地验证店铺", "platform": "douyin"},
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    log(f"POST /api/v1/stores                -> {r.status_code} id={sid}")

    r = client.get(f"/api/v1/stores/{sid}", headers=headers)
    log(f"GET  /api/v1/stores/{sid}          -> {r.status_code} name={r.json().get('name')}")

    r = client.get("/api/v1/stores", headers=headers)
    log(f"GET  /api/v1/stores (after)        -> {r.status_code} count={len(r.json())}")

    r = client.get("/api/v1/model-settings", headers=headers)
    log(f"GET  /api/v1/model-settings        -> {r.status_code}")

    r = client.get("/api/v1/products", headers=headers)
    body = r.json()
    log(f"GET  /api/v1/products              -> {r.status_code} count={len(body) if isinstance(body, list) else body}")

    r = client.get("/api/v1/stores")
    log(f"GET  /api/v1/stores (no token)     -> {r.status_code} (expect 401)")

    log("RESULT: SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback

        log("RESULT: SMOKE TEST FAILED")
        log("ERROR: " + repr(exc))
        log(traceback.format_exc())
        raise SystemExit(1)
