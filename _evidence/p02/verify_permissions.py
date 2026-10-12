"""P1 独立验证：权限体系 403 证据 + 三角色 token 生成（供前端验收）。

目的：
  ① 创建 owner / operator / viewer 三个角色账号
  ② 登录拿真实 token
  ③ 验证「客服(operator) / viewer 访问老板专属接口 → 403」
  ④ 把 token 写入文件，供前端页面级验收使用
运行：api/.venv/Scripts/python.exe _evidence/p02/verify_permissions.py
"""

import io
import json
import os
import sys

API = r"D:\software\PycharmProjects\面试项目\projects\p02-ecommerce-ops-assistant\api"
EV = r"D:\software\PycharmProjects\面试项目\_evidence\p02"

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(API, "local_dev.db")
os.environ["TASK_QUEUE_BACKEND"] = "inline"
os.environ["APP_ENV"] = "development"
os.environ.setdefault("AUTH_SECRET_KEY", "dev-change-me-but-use-a-long-random-32-char-secret")
sys.path.insert(0, API)

out = []


def w(s=""):
    out.append(str(s))
    print(s)


from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import UserRole  # noqa: E402
from app.services.bootstrap import ensure_bootstrap_user  # noqa: E402

ACCOUNTS = [
    ("owner", UserRole.OWNER, "owner@cloudpivot.demo", "CloudPivot@2026"),
    ("operator", UserRole.OPERATOR, "cs@cloudpivot.demo", "CloudPivot@2026"),
    ("viewer", UserRole.VIEWER, "viewer@cloudpivot.demo", "CloudPivot@2026"),
]

w("=" * 74)
w("【一】创建 / 确认三个角色账号")
w("=" * 74)
for name, role, email, pwd in ACCOUNTS:
    with SessionLocal() as db:
        user, created = ensure_bootstrap_user(
            db, email=email, display_name=f"云枢 {name}", password=pwd, role=role
        )
        info = (created, user.email, user.role.value)
    w(f"  [{name:8s}] created={info[0]!s:5s} email={info[1]:26s} role={info[2]}")

client = TestClient(app)

w()
w("=" * 74)
w("【二】登录并获取真实 token")
w("=" * 74)
tokens = {}
for name, _role, email, pwd in ACCOUNTS:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    if r.status_code == 200:
        d = r.json()
        tokens[name] = d["access_token"]
        perms = d["user"]["permissions"]
        w(f"  [{name:8s}] HTTP 200  role={d['user']['role']}")
        w(f"             permissions={json.dumps(perms, ensure_ascii=False)}")
    else:
        w(f"  [{name:8s}] HTTP {r.status_code}  {r.text[:120]}")

w()
w("=" * 74)
w("【三】★核心验收：角色权限对照（同一接口，不同角色）")
w("=" * 74)

# 老板专属接口（依赖 require_manage_users_permission）
PROTECTED = [
    ("GET", "/api/v1/users", "用户管理（老板专属）"),
]

results = []
for method, path, desc in PROTECTED:
    w(f"  --- {desc}  {method} {path}")
    for name in ("owner", "operator", "viewer"):
        tk = tokens.get(name)
        if not tk:
            w(f"      [{name:8s}] 无 token，跳过")
            continue
        r = client.request(method, path, headers={"Authorization": f"Bearer {tk}"})
        mark = ""
        if name == "owner":
            mark = "  ← 期望 200"
        elif r.status_code == 403:
            mark = "  ← ✅ 正确拒绝"
        else:
            mark = "  ← ⚠️ 期望 403"
        w(f"      [{name:8s}] HTTP {r.status_code}{mark}")
        results.append((name, path, r.status_code))

w()
w("  --- 无 token（权限基线）")
r = client.get("/api/v1/users")
w(f"      [anonymous] HTTP {r.status_code}  ← 期望 401/403")

w()
w("=" * 74)
w("【四】更细粒度：can_confirm_ad_actions 是否按角色区分")
w("=" * 74)
for name in ("owner", "operator", "viewer"):
    tk = tokens.get(name)
    if not tk:
        continue
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tk}"})
    if r.status_code == 200:
        p = r.json()["permissions"]
        w(f"  [{name:8s}] can_read={p['can_read']}  can_edit={p['can_edit']}  "
          f"can_manage_users={p['can_manage_users']}  can_confirm_ad_actions={p['can_confirm_ad_actions']}")

w()
w("=" * 74)
w("【结论】")
w("=" * 74)
owner_ok = all(sc == 200 for n, _p, sc in results if n == "owner")
others_403 = all(sc == 403 for n, _p, sc in results if n in ("operator", "viewer"))
if owner_ok and others_403:
    w("✅ 403 权限证据成立：老板可访问用户管理，运营/访客被拒")
else:
    w(f"⚠️ 未完全符合预期：owner_ok={owner_ok}  others_403={others_403}")

# 导出 token 供前端验收
os.makedirs(EV, exist_ok=True)
with io.open(os.path.join(EV, "role_tokens.json"), "w", encoding="utf-8") as fh:
    json.dump(tokens, fh, ensure_ascii=False, indent=2)
with io.open(os.path.join(EV, "permission_verify.log"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("WROTE_LOG")