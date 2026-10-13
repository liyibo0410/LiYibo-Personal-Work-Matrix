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


def test_get_unknown_dataset_404(client):
    assert client.get("/api/v1/datasets/nope").status_code == 404


def test_create_dataset(client):
    resp = client.post("/api/v1/datasets?name=my-dataset&format=jsonl")
    assert resp.status_code == 200
    ds = resp.json()
    assert ds["name"] == "my-dataset"
    assert ds["validation_status"] == "valid"
    # Newly created dataset is registered and retrievable.
    assert client.get(f"/api/v1/datasets/{ds['id']}").status_code == 200


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
    assert data["status"] == "deployed"
    assert data["endpoint_url"] is not None
    assert data["metrics"]["accuracy"] == 0.847


def test_get_unknown_model_404(client):
    assert client.get("/api/v1/models/nope").status_code == 404


def test_deploy_model_registers_openai_endpoint(client):
    resp = client.post("/api/v1/models/model-002/deploy", json={"endpoint_name": "cs-qa-test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deployed"
    assert data["openai_compatible"] is True
    assert data["mock"] is True
    assert data["endpoint_url"].startswith("http://127.0.0.1:")
    assert data["endpoint_url"].endswith("/v1")
    # Registry reflects the deployment.
    assert client.get("/api/v1/models/model-002").json()["status"] == "deployed"


def test_deploy_unknown_model_404(client):
    assert client.post("/api/v1/models/nope/deploy", json={}).status_code == 404
