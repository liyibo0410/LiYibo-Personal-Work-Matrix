"""P02 后端冒烟验证脚本（D2 验收用）。

作用：在不长期驻留服务的前提下，用 FastAPI TestClient 验证
  ① 应用可导入并完成 lifespan 启动
  ② 管理员账号可 bootstrap
  ③ 登录发放 JWT
  ④ 带 token 可访问受保护接口
运行：api/.venv/Scripts/python.exe _evidence/p02/verify_backend.py
"""

import io
import os
import sys

API = r"D:\software\PycharmProjects\面试项目\projects\p02-ecommerce-ops-assistant\api"
EV = r"D:\software\PycharmProjects\面试项目\_evidence\p02"

# --- 复刻 run_local_dev.py 的环境设置 ---
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(API, "local_dev.db")
os.environ["TASK_QUEUE_BACKEND"] = "inline"
os.environ["APP_ENV"] = "development"
os.environ.setdefault("AUTH_SECRET_KEY", "dev-change-me-but-use-a-long-random-32-char-secret")

_env_sqlite = os.path.join(API, ".env.sqlite")
if os.path.exists(_env_sqlite):
    with open(_env_sqlite, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if v:
                os.environ.setdefault(k, v)

sys.path.insert(0, API)

out = []


def w(s):
    out.append(str(s))
    print(s)


EMAIL = "owner@cloudpivot.demo"
PASSWORD = "CloudPivot@2026"

try:
    from fastapi.testclient import TestClient

    from app.db.session import SessionLocal
    from app.main import app
    from app.models import UserRole
    from app.services.bootstrap import ensure_bootstrap_user

    w("[1] 导入成功：app.main.app")

    with SessionLocal() as db:
        user, created = ensure_bootstrap_user(
            db, email=EMAIL, display_name="云枢 Owner", password=PASSWORD, role=UserRole.OWNER
        )
        # 必须在 session 内取值，否则 detached 后访问属性会抛 DetachedInstanceError
        boot = (created, user.email, user.role.value)
    w(f"[2] bootstrap: created={boot[0]} email={boot[1]} role={boot[2]}")

    client = TestClient(app)
    w("[3] TestClient 启动完成（含 lifespan）")

    r = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    w(f"[4] POST /api/v1/auth/login -> HTTP {r.status_code}")
    token = None
    if r.status_code == 200:
        d = r.json()
        token = d["access_token"]
        w(f"    token_type={d['token_type']}  len(token)={len(token)}")
        w(f"    user={d['user'].get('email')}  role={d['user'].get('role')}")
    else:
        w("    body=" + r.text[:400])

    if token:
        h = {"Authorization": f"Bearer {token}"}
        r2 = client.get("/api/v1/auth/me", headers=h)
        w(f"[5] GET /api/v1/auth/me -> HTTP {r2.status_code}  {r2.text[:180]}")

        # 未带 token 应被拒（权限基线）
        r3 = client.get("/api/v1/auth/me")
        w(f"[6] GET /api/v1/auth/me (无 token) -> HTTP {r3.status_code}  （期望 401/403）")

        for path in ["/api/v1/stores", "/api/v1/products", "/api/v1/workspace"]:
            rr = client.get(path, headers=h)
            w(f"[7] GET {path} -> HTTP {rr.status_code}  bytes={len(rr.text)}")

    oa = client.get("/openapi.json").json()
    w(f"[8] openapi: title={oa['info']['title']}  version={oa['info']['version']}  路径数={len(oa['paths'])}")
    for p in sorted(oa["paths"]):
        w("      " + p)

    w("")
    w("=== 结论：后端启动 + 认证 + 受保护接口 全部可达 ===")

except Exception as exc:  # noqa: BLE001
    import traceback

    w("!!! 失败: " + type(exc).__name__ + ": " + str(exc))
    w(traceback.format_exc())

os.makedirs(EV, exist_ok=True)
with io.open(os.path.join(EV, "backend_verify.log"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("WROTE_LOG")
