# 验证：商品主图生成改用「商品自身的真车图」作为参考图（图生图），不再让模型凭空想象商品。
import json
import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

for line in (API_DIR / ".env.sqlite").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
os.environ["DATABASE_URL"] = "sqlite:///./local_dev.db"

from app.db.session import SessionLocal  # noqa: E402
from app.models import CreativePlan, Product  # noqa: E402
from app.services.image_generation import generate_main_image_asset  # noqa: E402

report: dict = {}
try:
    with SessionLocal() as db:
        plan = db.get(CreativePlan, 41)
        product = db.get(Product, 4) if plan else None
        report["plan_id"] = 41
        report["plan_title"] = plan.title if plan else None
        report["product_images"] = list(product.images) if product and product.images else []
        reference = report["product_images"][0] if report["product_images"] else None
        report["reference_used"] = reference
        if plan is None:
            raise RuntimeError("creative plan 41 not found")
        asset = generate_main_image_asset(plan, reference_image=reference)
        report["ok"] = True
        report["asset_url"] = asset.get("url")
        report["source_url"] = (asset.get("source_url") or "")[:160]
        report["model"] = asset.get("model")
except Exception as exc:  # noqa: BLE001
    report["ok"] = False
    report["error"] = str(exc)[:500]

out = Path("C:/Users/23329/AppData/Local/Temp/verify_ref_image.json")
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False)[:1200])
