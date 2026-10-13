"""Integration tests for the P09 sales-assessment HTTP API.

Covers the acceptance gates: import → auto-score → leaderboard, per-agent
report, rule management, and the human-AI agreement statistics (Cohen's Kappa).
"""

from __future__ import annotations


# ── Health & stats ───────────────────────────────────────────────

def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "p09-ai-sales-assessment"


def test_stats_overview(client):
    data = client.get("/api/v1/stats").json()
    assert data["total_conversations"] == 22
    assert data["total_agents"] == 5
    assert 0 <= data["average_score"] <= 100
    # Distribution buckets must account for every scored conversation.
    assert sum(data["score_distribution"].values()) == 22
    assert set(data["dimension_averages"].keys()) == {
        "服务态度", "专业度", "需求挖掘", "促成转化", "合规性"
    }


# ── Leaderboard ──────────────────────────────────────────────────

def test_leaderboard_sorted_and_ranked(client):
    ranking = client.get("/api/v1/leaderboard").json()["leaderboard"]
    assert len(ranking) == 5
    scores = [r["average_score"] for r in ranking]
    assert scores == sorted(scores, reverse=True), "leaderboard must be sorted desc"
    assert [r["rank"] for r in ranking] == [1, 2, 3, 4, 5]
    for r in ranking:
        assert r["min_score"] <= r["average_score"] <= r["max_score"]
        assert r["conversation_count"] > 0


# ── Agent report ─────────────────────────────────────────────────

def test_agent_report(client):
    data = client.get("/api/v1/agents/agent-001").json()
    assert data["agent"]["id"] == "agent-001"
    assert data["summary"]["total_conversations"] == 6
    assert {r["dimension"] for r in data["radar"]} == {
        "服务态度", "专业度", "需求挖掘", "促成转化", "合规性"
    }
    assert len(data["score_trend"]) == 6
    assert isinstance(data["improvement_suggestions"], list)


def test_agent_report_unknown_404(client):
    assert client.get("/api/v1/agents/nope").status_code == 404


# ── Conversations list / detail ──────────────────────────────────

def test_list_conversations_pagination(client):
    data = client.get("/api/v1/conversations?page=1&page_size=5").json()
    assert data["total"] == 22
    assert data["page_size"] == 5
    assert len(data["items"]) == 5


def test_list_conversations_filter_by_agent(client):
    data = client.get("/api/v1/conversations?agent_id=agent-002").json()
    assert data["total"] == 5
    assert all(i["agent_id"] == "agent-002" for i in data["items"])


def test_list_conversations_filter_by_score(client):
    data = client.get("/api/v1/conversations?min_score=80").json()
    assert all(i["score"] >= 80 for i in data["items"])


def test_conversation_detail(client):
    first = client.get("/api/v1/conversations?page_size=1").json()["items"][0]["id"]
    data = client.get(f"/api/v1/conversations/{first}").json()
    assert data["id"] == first
    assert len(data["messages"]) > 0
    assert data["score"]["overall"] >= 0
    assert len(data["score"]["dimensions"]) == 5


def test_conversation_detail_unknown_404(client):
    assert client.get("/api/v1/conversations/does-not-exist").status_code == 404


# ── Live evaluation ──────────────────────────────────────────────

def test_evaluate_returns_mock_notice_and_score(client):
    # /evaluate takes `messages` as a raw JSON list body; agent_id/store are query params.
    messages = [
        {"role": "agent", "content": "您好，我很理解您的顾虑，这就帮您核实处理。"},
        {"role": "customer", "content": "谢谢"},
        {"role": "agent", "content": "感谢您选择我们，祝您生活愉快，再见！"},
    ]
    data = client.post("/api/v1/evaluate?agent_id=agent-001", json=messages).json()
    notice = data["mock_notice"]
    assert "并非真实 LLM 调用" in notice or "规则" in notice
    assert data["score"]["overall"] >= 0
    assert data["conversation_id"].startswith("conv-new-")


def test_evaluate_empty_messages_400(client):
    resp = client.post("/api/v1/evaluate", json=[])
    assert resp.status_code == 400


# ── Rules management ─────────────────────────────────────────────

def test_list_rules(client):
    data = client.get("/api/v1/rules").json()
    assert data["total"] == 8
    assert all("penalty" in r for r in data["rules"])


def test_update_rule_toggle_and_penalty(client):
    data = client.put("/api/v1/rules/rule-001", json={"enabled": False, "penalty": 25}).json()
    assert data["rule"]["enabled"] is False
    assert data["rule"]["penalty"] == 25.0


def test_update_unknown_rule_404(client):
    assert client.put("/api/v1/rules/nope", json={"enabled": True}).status_code == 404


# ── Human-AI agreement ───────────────────────────────────────────

def test_agreement_statistics(client):
    data = client.get("/api/v1/agreement").json()
    assert -1 <= data["kappa"] <= 1
    assert 0 <= data["observed_agreement"] <= 1
    assert 0 <= data["expected_agreement"] <= 1
    assert -1 <= data["pearson_correlation"] <= 1
    assert data["mean_absolute_error"] >= 0
    assert data["sample_size"] == 22
    assert data["kappa_interpretation"] in {
        "近乎完全一致", "高度一致", "中度一致", "一般一致", "微弱一致"
    }
    # Confusion matrix cells must sum to the sample size.
    total = sum(sum(row.values()) for row in data["confusion_matrix"].values())
    assert total == data["sample_size"]
    # The mock/demo boundary must be disclosed in the response.
    notice = data["mock_notice"]
    assert "演示数据" in notice or "模拟" in notice


# ── Import ───────────────────────────────────────────────────────

def test_import_json(client):
    payload = (
        '[{"agent_id": "agent-001", "topic": "导入会话 A", '
        '"messages": [{"role": "agent", "content": "您好，请问有什么可以帮您？"}, '
        '{"role": "customer", "content": "你好，想咨询一下商品"}]}]'.encode("utf-8")
    )
    data = client.post("/api/v1/import", files={"file": ("conv.json", payload, "application/json")}).json()
    assert data["imported"] == 1


def test_import_csv(client):
    csv_bytes = (
        "agent_id,agent_name,store,customer_name,topic,role,content,timestamp\n"
        "agent-002,测试坐席,旗舰店 B,赵女士,导入会话 CSV,agent,您好，请问有什么可以帮您,2025-03-15T10:00:00\n"
        "agent-002,测试坐席,旗舰店 B,赵女士,导入会话 CSV,customer,你好，想咨询商品,2025-03-15T10:00:15\n"
    ).encode("utf-8")
    data = client.post("/api/v1/import", files={"file": ("conv.csv", csv_bytes, "text/csv")}).json()
    assert data["imported"] == 1


def test_import_unsupported_format_400(client):
    resp = client.post("/api/v1/import", files={"file": ("data.txt", b"hello", "text/plain")})
    assert resp.status_code == 400
