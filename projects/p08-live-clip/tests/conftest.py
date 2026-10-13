import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.main as app_main  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app_main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _restore_tasks():
    """/process 会向 _all_tasks 写入新任务；测试后清理新增项，避免污染其他用例。

    streams/clips/asr 在 import 时一次性生成且只读，无需快照。
    """
    original_ids = set(app_main._all_tasks.keys())
    yield
    for tid in list(app_main._all_tasks.keys()):
        if tid not in original_ids:
            del app_main._all_tasks[tid]
