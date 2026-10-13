import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as app_main  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """把 SQLite 与上传目录重定向到临时路径，保证测试与真实 data/assets.db 隔离。

    app.main 在 import 时已执行过一次 init_db()（针对真实 DB_PATH），
    这里改写 DB_PATH / UPLOAD_DIR 后再次 init_db()，在临时库里重建表并播种 demo 数据。
    get_db() 每次调用都读取模块级 DB_PATH，因此重定向对所有后续请求生效。
    """
    db_file = tmp_path / "assets_test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(app_main, "DB_PATH", db_file)
    monkeypatch.setattr(app_main, "UPLOAD_DIR", upload_dir)

    app_main.init_db()

    with TestClient(app_main.app) as test_client:
        yield test_client
