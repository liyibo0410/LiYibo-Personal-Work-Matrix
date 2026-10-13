# -*- coding: utf-8 -*-
"""P09 → P01 跨模块集成测试。

验证「P09 消费 P01 会话数据走真实 HTTP 调用 + 降级不伪造」这条数据流闭环。
测试用 monkeypatch 替换 p01_client 的网络函数，使其不依赖 P01 是否在线，
但保留真实的端点装配、角色映射、评分与降级标注逻辑。
"""
from __future__ import annotations

from app import main as app_main


def _fake_ok(sender_ids):
    """模拟 P01 在线、返回两段真实结构会话（user/bot → customer/agent 已映射）。"""
    return {
        "ok": True, "degraded": False, "source": "p01-live",
        "url": "http://127.0.0.1:18082/api/chat/history",
        "conversations": [
            {"sender_id": "u1", "session_id": "sess-aaaa1111", "messages": [
                {"role": "customer", "content": "包装破损了要退货", "timestamp": ""},
                {"role": "agent", "content": "非常抱歉给您带来困扰，我马上帮您处理退款", "timestamp": ""},
            ]},
            {"sender_id": "u2", "session_id": "sess-bbbb2222", "messages": [
                {"role": "customer", "content": "有什么优惠", "timestamp": ""},
                {"role": "agent", "content": "不关我的事，您自己处理。", "timestamp": ""},
            ]},
        ],
        "fetched_senders": list(sender_ids), "empty_senders": [], "error": None,
    }


def _fake_degraded(sender_ids):
    return {"ok": False, "degraded": True, "source": "unavailable",
            "url": "http://127.0.0.1:59998/api/chat/history",
            "error": "P01 客服不可达：timed out", "requested_senders": list(sender_ids)}


def test_p01_status_endpoint(client, monkeypatch):
    monkeypatch.setattr(app_main.p01_client, "health",
                        lambda: {"ok": True, "status_code": 200, "url": "http://127.0.0.1:18082/health"})
    body = client.get("/api/v1/p01/status").json()
    assert body["ok"] is True
    assert body["status_code"] == 200


def test_import_from_p01_happy_path(client, monkeypatch):
    monkeypatch.setattr(app_main.p01_client, "fetch_conversations", _fake_ok)
    before = len(app_main.CONVERSATIONS)
    r = client.post("/api/v1/import/from-p01",
                    json={"sender_ids": ["u1", "u2"], "agent_id": "agent-002", "store": "旗舰店 A"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["degraded"] is False
    assert body["source"] == "p01-live"
    assert body["imported"] == 2
    # 真实追加到会话池并被评分
    assert len(app_main.CONVERSATIONS) == before + 2
    cid = body["conversation_ids"][0]
    detail = client.get(f"/api/v1/conversations/{cid}").json()
    assert detail["score"] is not None
    assert detail["customer_name"] in ("u1", "u2")
    assert len(detail["messages"]) == 2
    # 角色映射正确：P01 的 user/bot → P09 的 customer/agent
    roles = {m["role"] for m in detail["messages"]}
    assert roles == {"customer", "agent"}


def test_import_from_p01_degradation_does_not_fabricate(client, monkeypatch):
    monkeypatch.setattr(app_main.p01_client, "fetch_conversations", _fake_degraded)
    before = len(app_main.CONVERSATIONS)
    r = client.post("/api/v1/import/from-p01", json={"sender_ids": ["u1"]})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["degraded"] is True
    assert body["source"] == "unavailable"
    assert body["imported"] == 0
    # 红线：降级不伪造任何会话
    assert len(app_main.CONVERSATIONS) == before
    assert "notice" in body


def test_import_from_p01_empty_sender_ids_rejected(client):
    r = client.post("/api/v1/import/from-p01", json={"sender_ids": []})
    assert r.status_code == 400
