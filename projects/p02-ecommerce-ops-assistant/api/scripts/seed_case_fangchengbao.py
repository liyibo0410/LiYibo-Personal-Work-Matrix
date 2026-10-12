# 通过运行中的后端 API 创建门店 + 商品（方程豹洛阳龙门大道店 / 方程豹钛7）。
import json
import urllib.request

BASE = "http://127.0.0.1:8000"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 不走沙箱代理


def call(method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with opener.open(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


status, auth = call(
    "POST", "/api/v1/auth/login",
    {"email": "admin@local.dev", "password": "LocalDev123!"},
)
print("login:", status)
token = auth.get("access_token")

# 1) 门店
store_payload = {
    "name": "方程豹洛阳龙门大道店",
    "platform": "douyin",
    "status": "active",
    "owner_name": "李奕波",
    "note": "方程豹（比亚迪旗下个性化品牌）洛阳授权门店，主营钛7/豹5/豹8；抖音为主要内容与线索渠道。",
}
s_status, store = call("POST", "/api/v1/stores", store_payload, token)
print("create store:", s_status)
store_id = store.get("id")
print("store_id =", store_id, "| name =", store.get("name"))

# 2) 商品：方程豹钛7（参数取自汽车之家/新浪汽车公开资料）
product_payload = {
    "store_id": store_id,
    "name": "方程豹 钛7",
    "platform": "douyin",
    "category": "汽车/中大型SUV",
    "price": 195800,
    "target_audience": "25-40岁家庭用户，看重空间与个性化表达的城市中产；钛7增换购用户中70%来自传统豪华品牌",
    "selling_points": [
        "中大型SUV大空间：车长4999mm、轴距2920mm，后排成员舱高度1364mm，全车47处储物空间",
        "纯电续航最高315km（CLTC），综合续航超1300km，城市通勤可当电车开",
        "四驱Ultra版零百加速4.5秒，电动四驱兼顾性能与通过性",
        "“城市方盒子”造型，硬派外观与家用舒适平衡，辨识度强",
        "整车质保六年或15万公里，用车安心",
    ],
    "platform_status": "在售",
    "external_product_id": "tai7-2026-315km-max",
}
p_status, product = call("POST", "/api/v1/products", product_payload, token)
print("create product:", p_status)
print("product_id =", product.get("id"), "| name =", product.get("name"))
print("product detail:", json.dumps(product, ensure_ascii=False, default=str)[:600])

report = {
    "store": {"status": s_status, "id": store_id, "name": store.get("name")},
    "product": {"status": p_status, "id": product.get("id"), "name": product.get("name")},
}
open("C:/Users/23329/AppData/Local/Temp/seed_case_report.json", "w", encoding="utf-8").write(
    json.dumps(report, ensure_ascii=False, indent=2)
)
