import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    """把 SQLite / 上传目录重定向到 tmp_path，并把模型与跨模块调用打桩。

    测试进程**绝不发出真实网络请求**：`llm.chat_json` 默认桩成「未配置」，
    P06 取数桩成「不可用」；需要走成功路径的用例显式覆盖这两个桩。
    """
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "assets.db")
    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)

    from app.services import data_platform, llm

    monkeypatch.setattr(
        data_platform, "fetch_platform_metrics",
        lambda timeout=4.0: {"available": False, "metrics": [], "source_url": "http://stub",
                             "fetched_at": "2026-10-13T00:00:00", "reason": "测试桩：未启动 P06"},
    )
    monkeypatch.setattr(llm, "chat_json", lambda *a, **kw: llm.LLMResult(
        ok=False, source="mock", reason="not_configured", prompt_version="stub"))

    # 凭证置空：/llm/status 在任何开发机 .env 下都应报「降级」而不是误读真实 Key
    empty = config.Settings(_env_file=None, LLM_BASE_URL="", LLM_API_KEY="", LLM_MODEL="",
                            LLM_MODEL_FAST="", LLM_BASE_URL_FALLBACK="", LLM_API_KEY_FALLBACK="",
                            LLM_MODEL_ALT="", P07_INGEST_TOKEN="")
    monkeypatch.setattr(config, "get_settings", lambda: empty)
    return tmp_path


@pytest.fixture
def client(env):
    from app.main import app

    with TestClient(app) as c:  # with → 触发 lifespan → 在临时库上建表播种
        yield c


def _stub_llm(monkeypatch, payload: dict):
    """让 llm.chat_json 返回给定的「模型成功」结果，用于覆盖 LLM 分支。"""
    from app.services import llm

    def fake(prompt_file, user_content, **kw):
        return llm.LLMResult(ok=True, data=payload, source="llm", model="stub-model",
                             endpoint="stub", latency_ms=12.3, prompt_tokens=10,
                             completion_tokens=20, total_tokens=30, prompt_version=prompt_file)

    monkeypatch.setattr(llm, "chat_json", fake)


@pytest.fixture
def fake_llm(monkeypatch):
    """`fake_llm({"tags": [...]})` —— 在本条测试里把模型调用换成成功返回。"""
    return lambda payload: _stub_llm(monkeypatch, payload)
