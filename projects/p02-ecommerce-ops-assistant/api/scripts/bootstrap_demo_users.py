"""创建四个角色的演示用户。"""
import os
import sys

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(API_DIR)))
SHARED_LLM_GATEWAY = os.path.join(WORKSPACE_ROOT, "shared", "llm-gateway", "src")
if os.path.isdir(SHARED_LLM_GATEWAY):
    sys.path.insert(0, os.path.abspath(SHARED_LLM_GATEWAY))
sys.path.insert(0, API_DIR)

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(API_DIR, "local_dev.db"))
os.environ.setdefault("AUTH_SECRET_KEY", "dev-change-me-but-use-a-long-random-32-char-secret")

from app.db.session import SessionLocal
from app.models import UserRole
from app.services.bootstrap import ensure_bootstrap_user

DEMO_USERS = [
    {"email": "boss@example.com", "display_name": "张总(老板)", "password": "Test123456", "role": UserRole.OWNER},
    {"email": "ops@example.com", "display_name": "李运营", "password": "Test123456", "role": UserRole.OPERATOR},
    {"email": "design@example.com", "display_name": "王美工", "password": "Test123456", "role": UserRole.DESIGNER},
    {"email": "cs@example.com", "display_name": "赵客服", "password": "Test123456", "role": UserRole.CS},
]

def main():
    with SessionLocal() as db:
        for u in DEMO_USERS:
            user, created = ensure_bootstrap_user(db, **u)
            action = "Created" if created else "Exists"
            print(f"[{action}] {user.email} role={user.role.value}")

if __name__ == "__main__":
    main()
