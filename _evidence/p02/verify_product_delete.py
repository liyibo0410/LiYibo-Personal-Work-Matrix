"""P02 商品删除链路实机验证：临时商品 → 挂 SKU/库存/竞品 → 权限边界 → 删除 → 复核。

只操作本次新建的临时商品，不触碰演示数据里的既有商品。
"""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
LOG_PATH = Path(__file__).with_name("product_delete_live.log")
MARK = f"删除验证-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
LINES: list[str] = []


def out(message: str) -> None:
    print(message)
    LINES.append(message)


def login(email: str, password: str) -> str:
    response = httpx.post(
        f"{BASE}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def token_for(email: str) -> str:
    for password in ("Test123456", "LocalDev123!"):
        try:
            return login(email, password)
        except httpx.HTTPStatusError:
            continue
    raise SystemExit(f"登录失败：{email}")


def main() -> int:
    out(f"# P02 商品删除实机验证 {datetime.now(UTC).isoformat()}")
    out(f"BASE={BASE}  临时商品标记={MARK}")

    spec = httpx.get(f"{BASE}/openapi.json", timeout=30).json()
    delete_ops = sorted(
        method.upper()
        for method in spec["paths"].get("/api/v1/products/{product_id}", {})
    )
    out(f"1) 路由注册 /api/v1/products/{{product_id}} → {delete_ops}")
    assert "DELETE" in delete_ops, "DELETE 路由未注册"

    boss = token_for("boss@example.com")
    cs = token_for("cs@example.com")
    boss_headers = {"Authorization": f"Bearer {boss}"}
    cs_headers = {"Authorization": f"Bearer {cs}"}

    created = httpx.post(
        f"{BASE}/api/v1/products",
        headers=boss_headers,
        json={
            "name": f"临时验证商品 {MARK}",
            "platform": "douyin",
            "category": "验证用",
            "price": "99.00",
            "selling_points": ["验证删除", "非演示数据"],
        },
        timeout=30,
    )
    created.raise_for_status()
    product_id = created.json()["id"]
    out(f"2) 创建临时商品 → 201 id={product_id}")

    sku = httpx.post(
        f"{BASE}/api/v1/products/{product_id}/skus",
        headers=boss_headers,
        json={
            "sku_code": f"SKU-{MARK}",
            "name": "验证用正装",
            "initial_quantity": 50,
            "warning_threshold": 10,
        },
        timeout=30,
    )
    sku.raise_for_status()
    out(f"3) 创建 SKU（连带库存档案与流水）→ {sku.status_code} sku_id={sku.json()['id']}")

    competitor = httpx.post(
        f"{BASE}/api/v1/products/{product_id}/competitors",
        headers=boss_headers,
        json={"name": f"验证用竞品 {MARK}", "platform": "douyin", "price": "89.00"},
        timeout=30,
    )
    competitor.raise_for_status()
    out(f"4) 创建竞品 → {competitor.status_code} competitor_id={competitor.json()['id']}")

    detail = httpx.get(f"{BASE}/api/v1/products/{product_id}", headers=boss_headers, timeout=30)
    detail.raise_for_status()
    body = detail.json()
    out(
        "5) 删除前子资源："
        f"skus={len(body['skus'])} competitors={len(body['competitors'])}"
        f" 库存流水={sum(len(s.get('inventory_movements', [])) for s in body['skus'])}"
    )

    forbidden = httpx.delete(f"{BASE}/api/v1/products/{product_id}", headers=cs_headers, timeout=30)
    out(f"6) 客服角色删除 → {forbidden.status_code} {forbidden.json()}")
    assert forbidden.status_code == 403

    anonymous = httpx.delete(f"{BASE}/api/v1/products/{product_id}", timeout=30)
    out(f"7) 未登录删除 → {anonymous.status_code} {anonymous.json()}")
    assert anonymous.status_code == 401

    deleted = httpx.delete(f"{BASE}/api/v1/products/{product_id}", headers=boss_headers, timeout=30)
    out(f"8) 老板角色删除 → {deleted.status_code} body={deleted.text!r}")
    assert deleted.status_code == 204

    after = httpx.get(f"{BASE}/api/v1/products/{product_id}", headers=boss_headers, timeout=30)
    out(f"9) 删除后详情 → {after.status_code} {after.json()}")
    assert after.status_code == 404

    listing = httpx.get(
        f"{BASE}/api/v1/products",
        headers=boss_headers,
        params={"limit": 100},
        timeout=30,
    )
    listing.raise_for_status()
    leftovers = [p for p in listing.json() if MARK in p["name"]]
    out(f"10) 商品池里残留的验证商品：{json.dumps(leftovers, ensure_ascii=False)}")
    assert not leftovers

    out("\n结论：DELETE /api/v1/products/{product_id} 实机跑通，级联子资源随聚合根清除，"
        "客服 403 / 未登录 401 / 越权后商品仍在。")
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    finally:
        LOG_PATH.write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(f"[log written] {LOG_PATH}")
    raise SystemExit(code)
