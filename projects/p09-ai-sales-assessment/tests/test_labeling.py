"""真人质检评分台（人工标注）与一致性计算的行为测试。

覆盖三件事：
1. 评分台是**盲评**（队列与单条视图都不返回 AI 分数）；
2. 人工综合分按与 AI 相同的五维权重算，且**落盘**（重启后一致性报告仍成立）；
3. `/api/v1/agreement` 的 Cohen's Kappa 与混淆矩阵自洽（用独立实现反算校验公式）。
"""

from __future__ import annotations

from app import main as app_main

DIMENSIONS = ("服务态度", "专业度", "需求挖掘", "促成转化", "合规性")
CATEGORIES = ("excellent", "good", "average", "poor")


def _first_unlabeled_id(client) -> str:
    queue = client.get("/api/v1/labeling/queue?limit=10").json()["queue"]
    pending = [q for q in queue if not q["labeled"]]
    assert pending, "队列里应当有未评会话"
    return pending[0]["id"]


def test_queue_is_blind(client):
    """评分台不能把 AI 分透出去，否则人工分就被锚定了，Kappa 失去意义。"""
    payload = client.get("/api/v1/labeling/queue?limit=5").json()
    for item in payload["queue"]:
        assert "score" not in item
        assert "ai_score" not in item
        assert "human_score" not in item
        assert "messages" in item and item["message_count"] == len(item["messages"])
    single = client.get("/api/v1/labeling/" + payload["queue"][0]["id"]).json()
    assert "score" not in single
    assert single["labeled"] is False
    assert single["existing_label"] is None


def test_submit_label_uses_shared_weights_and_persists(client, tmp_path):
    conv_id = _first_unlabeled_id(client)
    dims = {"服务态度": 90, "专业度": 80, "需求挖掘": 70, "促成转化": 60, "合规性": 100}

    resp = client.post(
        f"/api/v1/labeling/{conv_id}",
        json={"dimensions": dims, "note": "促成转化偏弱", "rater": "李奕波"},
    )
    assert resp.status_code == 200
    body = resp.json()

    expected = round(sum(dims[d] * app_main.HUMAN_WEIGHTS[d] for d in DIMENSIONS), 1)
    assert body["human_overall"] == expected
    assert body["ai_overall"] is not None
    assert body["diff"] == round(expected - body["ai_overall"], 1)
    assert body["labeled_count"] == 1
    assert body["pending_count"] == body["total_conversations"] - 1

    # 内存态回填 + 真实落盘（LABELS_PATH 已被 conftest 指到 tmp_path）
    conv = next(c for c in app_main.CONVERSATIONS if c.id == conv_id)
    assert conv.human_score == expected
    on_disk = app_main.LABELS_PATH
    assert on_disk.exists(), "真人评分必须落盘，否则重启后一致性报告归零"
    import json

    saved = json.loads(on_disk.read_text(encoding="utf-8"))
    assert saved[conv_id]["overall"] == expected
    assert saved[conv_id]["rater"] == "李奕波"
    assert saved[conv_id]["dimensions"] == dims


def test_label_validation_rejects_bad_payloads(client):
    conv_id = _first_unlabeled_id(client)

    missing = client.post(f"/api/v1/labeling/{conv_id}", json={"dimensions": {"服务态度": 80}})
    assert missing.status_code == 422
    assert "缺少维度评分" in missing.json()["detail"]

    unknown = client.post(
        f"/api/v1/labeling/{conv_id}",
        json={"dimensions": {**{d: 80 for d in DIMENSIONS}, "玄学": 10}},
    )
    assert unknown.status_code == 422
    assert "未知评分维度" in unknown.json()["detail"]

    out_of_range = client.post(
        f"/api/v1/labeling/{conv_id}",
        json={"dimensions": {**{d: 200 for d in DIMENSIONS}}},
    )
    assert out_of_range.status_code == 422

    assert client.post("/api/v1/labeling/conv-does-not-exist", json={"dimensions": {d: 80 for d in DIMENSIONS}}).status_code == 404
    assert client.get("/api/v1/labeling/conv-does-not-exist").status_code == 404


def test_delete_label_clears_state_and_file(client):
    conv_id = _first_unlabeled_id(client)
    client.post(f"/api/v1/labeling/{conv_id}", json={"dimensions": {d: 75 for d in DIMENSIONS}, "rater": "测试"})
    assert client.get("/api/v1/labeling").json()["labeled_count"] == 1

    assert client.delete(f"/api/v1/labeling/{conv_id}").json()["labeled_count"] == 0
    conv = next(c for c in app_main.CONVERSATIONS if c.id == conv_id)
    assert conv.human_score is None
    assert client.delete(f"/api/v1/labeling/{conv_id}").status_code == 404


def test_kappa_matches_confusion_matrix(client):
    """独立反算 Kappa，校验接口里的公式没有算错。"""
    # 造一批已知的人工分：一半评 90（excellent），一半评 60（average）
    queue = client.get("/api/v1/labeling/queue?limit=20").json()["queue"]
    pending = [q["id"] for q in queue if not q["labeled"]][:8]
    assert len(pending) == 8
    for i, cid in enumerate(pending):
        score = 90 if i % 2 == 0 else 60
        client.post(
            f"/api/v1/labeling/{cid}",
            json={"dimensions": {d: score for d in DIMENSIONS}, "rater": "测试评分员"},
        )

    data = client.get("/api/v1/agreement").json()
    assert data["sample_size"] == 8
    matrix = data["confusion_matrix"]
    n = sum(sum(row.values()) for row in matrix.values())
    assert n == 8

    observed = sum(matrix[c][c] for c in CATEGORIES) / n
    row_totals = {c: sum(matrix[c].values()) for c in CATEGORIES}
    col_totals = {c: sum(matrix[r][c] for r in CATEGORIES) for c in CATEGORIES}
    expected = sum((row_totals[c] / n) * (col_totals[c] / n) for c in CATEGORIES)
    recomputed = (observed - expected) / (1 - expected) if expected < 1 else 0.0

    assert data["observed_agreement"] == round(observed, 4)
    assert data["expected_agreement"] == round(expected, 4)
    assert abs(data["kappa"] - recomputed) < 1e-3
