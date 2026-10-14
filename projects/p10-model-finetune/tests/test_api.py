"""Integration tests for the P10 model-finetune HTTP API.

Covers the platform lifecycle: dataset registry → start (mock) training →
loss curve → evaluation comparison → model registry → mock deployment of an
OpenAI-compatible endpoint. Every mock boundary must stay disclosed.
"""

from __future__ import annotations

import math


# ── Health & stats ───────────────────────────────────────────────

def test_health_declares_mock_mode(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True


def test_stats(client):
    data = client.get("/api/v1/stats").json()
    assert data["datasets"] == 3
    assert data["training_runs"] == 2
    assert data["completed_runs"] == 2
    assert data["model_versions"] == 3
    assert data["deployed_models"] == 1
    assert data["mock_mode"] is True
    assert 0 <= data["avg_accuracy"] <= 1


# ── Datasets ─────────────────────────────────────────────────────

def test_list_datasets(client):
    data = client.get("/api/v1/datasets").json()
    assert len(data) == 3
    assert {d["id"] for d in data} == {"ds-001", "ds-002", "ds-003"}


def test_get_dataset_detail(client):
    data = client.get("/api/v1/datasets/ds-001").json()
    assert data["id"] == "ds-001"
    assert "label_distribution" in data
    assert "token_histogram" in data
    assert data["format_validation"]["status"] == "valid"
    # 预置演示数据集没有真实样本，分布类字段必须是 null 而不是写死的占比
    assert data["label_distribution"] is None
    assert data["token_histogram"] is None
    assert data["duplicates_removed"] is None
    assert data["provenance"] == "seed_demo"
    assert data["unmeasured"], "未测量项必须显式列出来"


def test_get_unknown_dataset_404(client):
    assert client.get("/api/v1/datasets/nope").status_code == 404


def test_create_dataset(client):
    """不带文件的登记：不能声称自己是有效数据集。"""
    resp = client.post("/api/v1/datasets?name=my-dataset&format=jsonl")
    assert resp.status_code == 200
    ds = resp.json()
    assert ds["name"] == "my-dataset"
    assert ds["validation_status"] == "pending"
    assert ds["provenance"] == "metadata-only"
    assert ds["sample_count"] == 0
    assert ds["file_size_bytes"] is None
    # Newly created dataset is registered and retrievable.
    assert client.get(f"/api/v1/datasets/{ds['id']}").status_code == 200


def test_create_dataset_measures_the_uploaded_file_for_real(client):
    """上传了文件就必须真算：这条是防「用 random 造数据集统计」的回归测试。"""
    rows = [
        '{"messages": [{"role": "user", "content": "退货"}], "label": "退货申请"}',
        '{"messages": [{"role": "user", "content": "发货"}], "label": "咨询"}',
        '{"messages": [{"role": "user", "content": "退货"}], "label": "退货申请"}',
        '{"messages": [{"role": "user", "content": "投诉"}], "label": "投诉"}',
        '{"messages": [{"role": "user", "content": "退货"}], "label": "退货申请"}',
    ]
    payload = ("\n".join(rows) + "\n").encode("utf-8")

    resp = client.post(
        "/api/v1/datasets?name=real-measure&format=jsonl",
        files={"file": ("real.jsonl", payload, "application/x-ndjson")},
    )
    assert resp.status_code == 200
    ds = resp.json()
    assert ds["provenance"] == "measured-from-upload"
    assert ds["file_size_bytes"] == len(payload)
    assert ds["sample_count"] == 5
    assert ds["validation_status"] == "valid"
    # 没有 tokenizer，就不能给 Token 数
    assert ds["avg_tokens"] is None
    assert "duplicates_removed" in ds["measured_fields"]

    detail = client.get(f"/api/v1/datasets/{ds['id']}").json()
    # 5 行里有 2 行与前面的行完全相同
    assert detail["duplicates_removed"] == 2
    assert detail["label_distribution"] == {"退货申请": 0.6, "咨询": 0.2, "投诉": 0.2}
    assert detail["char_length_percentiles"]["p50"] > 0
    assert detail["token_histogram"] is None


# ── Training ─────────────────────────────────────────────────────

def test_start_training_computes_steps(client):
    payload = {
        "dataset_id": "ds-001",
        "name": "unit-test-run",
        "config": {"batch_size": 4, "gradient_accumulation_steps": 8, "num_epochs": 3},
    }
    resp = client.post("/api/v1/training/start", json=payload)
    assert resp.status_code == 200, resp.text
    t = resp.json()
    assert t["status"] == "completed"
    # ds-001 has 12500 samples → ceil(12500/32)*3 == 1173 steps
    assert t["total_steps"] == math.ceil(12500 / 32) * 3
    assert t["current_step"] == t["total_steps"]
    assert t["final_loss"] is not None
    assert len(t["loss_curve"]) > 1


def test_start_training_unknown_dataset_404(client):
    resp = client.post("/api/v1/training/start", json={"dataset_id": "nope", "config": {}})
    assert resp.status_code == 404


def test_get_training_and_loss(client):
    t = client.get("/api/v1/training/train-001").json()
    assert t["id"] == "train-001"
    loss = client.get("/api/v1/training/train-001/loss").json()
    assert loss["total_steps"] == t["total_steps"]
    assert len(loss["points"]) > 1


def test_get_unknown_training_404(client):
    assert client.get("/api/v1/training/nope").status_code == 404
    assert client.get("/api/v1/training/nope/loss").status_code == 404


# ── Evaluations & comparison ─────────────────────────────────────

def test_list_evaluations(client):
    data = client.get("/api/v1/evaluations").json()
    assert len(data) == 3


def test_compare_against_baseline(client):
    resp = client.post("/api/v1/evaluations/compare", json={"after_training_id": "train-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["before"] is not None  # baseline used when before_training_id omitted
    assert data["after"]["accuracy"] == 0.847
    # delta must equal after - before for every metric (verifies the maths, not a claim)
    for k in data["after"]:
        assert data["delta"][k] == round(data["after"][k] - data["before"][k], 4)


def test_compare_unknown_after_404(client):
    resp = client.post("/api/v1/evaluations/compare", json={"after_training_id": "nope"})
    assert resp.status_code == 404


# ── Model registry & deployment ──────────────────────────────────

def test_list_models(client):
    data = client.get("/api/v1/models").json()
    assert len(data) == 3


def test_get_model(client):
    data = client.get("/api/v1/models/model-001").json()
    assert data["status"] == "deployed_simulated"
    # 不允许出现「看起来能调但其实没服务」的地址：8101 是 P10 自己的 FastAPI 端口
    assert data["endpoint_url"] is None
    assert data["endpoint_status"] == "simulated"
    assert data["simulated"] is True
    assert data["metrics"]["accuracy"] == 0.847
    assert "模拟" in data["metrics_note"]


def test_get_unknown_model_404(client):
    assert client.get("/api/v1/models/nope").status_code == 404


def test_deploy_model_does_not_fabricate_an_endpoint(client):
    """模拟部署只能登记状态，不能编一个 OpenAI 兼容地址冒充可调用的服务。"""
    resp = client.post("/api/v1/models/model-002/deploy", json={"endpoint_name": "cs-qa-test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deployed_simulated"
    assert data["endpoint_url"] is None
    assert data["simulated"] is True
    assert data["openai_compatible"] is False
    assert data["inference_served"] is False
    assert "没有启动推理服务" in data["message"]
    # Registry reflects the simulated deployment state, and still exposes no URL.
    after = client.get("/api/v1/models/model-002").json()
    assert after["status"] == "deployed_simulated"
    assert after["endpoint_url"] is None


def test_stats_reports_no_real_served_model(client):
    data = client.get("/api/v1/stats").json()
    assert data["real_served_models"] == 0
    assert data["deployed_models"] == data["deployed_simulated_models"]
    assert "模拟" in data["metrics_provenance"]


def test_deploy_unknown_model_404(client):
    assert client.post("/api/v1/models/nope/deploy", json={}).status_code == 404
