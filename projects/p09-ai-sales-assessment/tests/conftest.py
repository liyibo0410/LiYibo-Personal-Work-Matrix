"""Shared fixtures for P09 AI sales-assessment tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import main as app_main  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app_main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _restore_conversations():
    """The /evaluate and /import endpoints append to the module-level
    CONVERSATIONS list. Snapshot its length and truncate back after each test
    so global demo state never leaks between tests.
    """
    original_len = len(app_main.CONVERSATIONS)
    yield
    del app_main.CONVERSATIONS[original_len:]


@pytest.fixture(autouse=True)
def _isolate_human_labels(tmp_path):
    """真人评分是**会落盘**的（data/human_labels.json）。测试必须把路径改到 tmp_path，
    否则跑一次测试就会污染用户真实的质检标注。
    """
    original_path = app_main.LABELS_PATH
    original_labels = {k: dict(v) for k, v in app_main.HUMAN_LABELS.items()}
    original_scores = {c.id: c.human_score for c in app_main.CONVERSATIONS}
    app_main.LABELS_PATH = tmp_path / "human_labels.json"
    app_main.HUMAN_LABELS.clear()
    yield
    app_main.LABELS_PATH = original_path
    app_main.HUMAN_LABELS.clear()
    app_main.HUMAN_LABELS.update(original_labels)
    for conv in app_main.CONVERSATIONS:
        if conv.id in original_scores:
            conv.human_score = original_scores[conv.id]
