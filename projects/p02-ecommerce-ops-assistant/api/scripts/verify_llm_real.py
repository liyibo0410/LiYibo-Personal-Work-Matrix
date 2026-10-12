"""真实大模型链路验证（开发模式，SQLite + inline）。

目标：用用户在 api/.env.sqlite 中填入的真实阿里云 MaaS 密钥，
端到端跑通「商品诊断」接口，证明大模型功能确实打通：

    建表 -> 初始化管理员 -> 登录 -> 建店铺 -> 建商品 -> 调用诊断 -> 断言 source=="llm"

脚本把 .env.sqlite 的键值注入 os.environ（仅覆盖 LLM/IMAGE/VIDEO 与基础开发项），
随后走 FastAPI TestClient 全链路。结果同时打印并写入 /tmp/verify_llm_report.json，
便于在无法读取 stdout 的环境下回看。

用法：
    cd api
    ..\\.venv\\Scripts\\python.exe scripts/verify_llm_real.py
"""

import json
import os
import sys
import tempfile

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_SQLITE = os.path.join(API_DIR, ".env.sqlite")
REPORT_PATH = os.path.join(tempfile.gettempdir(), "verify_llm_report.json")

# ---------------------------------------------------------------------------
# 1) 加载 .env.sqlite 到环境变量（覆盖 LLM/IMAGE/VIDEO 等真实密钥）
# ---------------------------------------------------------------------------
def load_env_sqlite(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env[key] = value
    return env


loaded = load_env_sqlite(ENV_SQLITE)
for k, v in loaded.items():
    os.environ.setdefault(k, v)

# 开发模式：临时 SQLite + inline 队列，避免依赖 MySQL / Redis / PostgreSQL。
_db_path = os.path.join(tempfile.gettempdir(), "ecommerce_verify_llm.db")
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


def write_report(data: dict) -> None:
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)


def main() -> int:
    report: dict = {"steps": [], "ok": False}
    Base.metadata.create_all(engine)
    report["steps"].append("create_all: schema created on sqlite")

    email, password = "verify@local.dev", "Verify123!"
    with SessionLocal() as db:
        user, created = ensure_bootstrap_user(
            db, email=email, display_name="Verify", password=password
        )
    report["steps"].append(f"bootstrap: created={created} role={user.role.value}")

    client = TestClient(app)
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    report["steps"].append("login: token acquired")

    r = client.post(
        "/api/v1/stores", headers=headers,
        json={"name": "验证店铺-数码配件", "platform": "douyin"},
    )
    assert r.status_code == 201, r.text
    store_id = r.json()["id"]
    report["steps"].append(f"store created: id={store_id}")

    r = client.post(
        "/api/v1/products", headers=headers,
        json={
            "store_id": store_id,
            "name": "无线蓝牙耳机 Pro",
            "platform": "douyin",
            "category": "数码配件/耳机",
            "price": "199.00",
            "cost": "79.00",
            "target_audience": "18-35 岁学生与年轻白领，通勤运动场景",
            "selling_points": ["主动降噪", "30 小时续航", "低延迟游戏模式"],
        },
    )
    assert r.status_code == 201, r.text
    product_id = r.json()["id"]
    report["steps"].append(f"product created: id={product_id}")

    # 关键一步：真实调用阿里云 qwen3.8-flash 生成诊断
    r = client.post(
        f"/api/v1/products/{product_id}/diagnoses/generate", headers=headers
    )
    report["steps"].append(f"diagnosis generate: HTTP {r.status_code}")
    if r.status_code != 201:
        report["error"] = r.text
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str), flush=True)
        return 1

    diag = r.json()
    report["diagnosis_source"] = diag.get("source")
    report["diagnosis_keys"] = sorted(diag.keys())
    report["diagnosis_sample"] = {
        k: diag.get(k)
        for k in ("positioning", "price_band", "audience_insights", "risks", "recommendations")
        if k in diag
    }
    report["steps"].append(f"diagnosis source={diag.get('source')}")

    # 断言：必须真正走大模型，而非规则回退
    ok = diag.get("source") == "llm"
    report["ok"] = ok
    report["result"] = "REAL LLM CHAIN VERIFIED" if ok else "LLM NOT USED (rules fallback)"
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback

        report = {"steps": ["FAILED"], "ok": False, "error": repr(exc), "trace": traceback.format_exc()}
        try:
            write_report(report)
        except Exception:  # noqa: BLE001
            pass
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str), flush=True)
        raise SystemExit(1)
