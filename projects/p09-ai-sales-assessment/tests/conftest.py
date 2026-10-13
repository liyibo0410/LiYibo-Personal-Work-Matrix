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
