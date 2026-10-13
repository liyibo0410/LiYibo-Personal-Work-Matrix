# P08 API 集成测试
# 覆盖验收门禁：打点结果可解释（每段给出得分构成）；批量任务队列可用，进度可见。

import app.main as m


def test_health_reports_mock_boundaries(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "p08-live-clip"
    # mock 边界必须在健康检查中声明（红线：mock 双处标注）
    assert len(data["mock_boundaries"]) == 3


def test_list_streams(client):
    r = client.get("/api/v1/streams")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    ids = {it["id"] for it in data["items"]}
    assert ids == {"stream-001", "stream-002", "stream-003"}


def test_list_streams_filter_platform(client):
    r = client.get("/api/v1/streams?platform=抖音")
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "stream-001"


def test_list_streams_filter_status(client):
    r = client.get("/api/v1/streams?status=completed")
    assert r.json()["total"] == 3


def test_get_stream_detail_with_asr(client):
    r = client.get("/api/v1/streams/stream-001")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "stream-001"
    assert data["title"] == "春季美妆新品发布会"
    assert isinstance(data["asr_segments"], list)
    assert len(data["asr_segments"]) >= 1
    assert data["clip_count"] >= 0


def test_get_stream_404(client):
    assert client.get("/api/v1/streams/nope").status_code == 404


def test_list_clips_and_score_breakdown_explainable(client):
    r = client.get("/api/v1/clips")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    clip = data["items"][0]
    sb = clip["score_breakdown"]
    # 可解释性门禁：每段给出得分构成 + 理由
    for key in ("keyword_density", "energy_level", "speech_rate", "interaction"):
        assert key in sb
        assert 0 <= sb[key] <= 95
    assert isinstance(sb["keyword_hits"], list)
    assert isinstance(sb["explanation"], str) and sb["explanation"]


def test_list_clips_filter_by_stream(client):
    r = client.get("/api/v1/clips?stream_id=stream-001&page_size=100")
    data = r.json()
    assert data["total"] >= 1
    assert all(c["stream_id"] == "stream-001" for c in data["items"])


def test_list_clips_min_score_excludes_all_when_impossible(client):
    # 分数上限 95，min_score=999 必然空
    r = client.get("/api/v1/clips?min_score=999")
    assert r.json()["total"] == 0


def test_list_clips_sort_desc(client):
    r = client.get("/api/v1/clips?sort_by=score&order=desc&page_size=100")
    scores = [c["score"] for c in r.json()["items"]]
    assert scores == sorted(scores, reverse=True)


def test_list_clips_pagination(client):
    r = client.get("/api/v1/clips?page=1&page_size=1")
    data = r.json()
    assert len(data["items"]) <= 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_pages"] == data["total"]  # 每页 1 条 -> 页数==总数


def test_get_clip_detail_and_404(client):
    lst = client.get("/api/v1/clips?page_size=1").json()["items"]
    assert lst, "seed 数据应至少有一个切片"
    cid = lst[0]["id"]
    r = client.get(f"/api/v1/clips/{cid}")
    assert r.status_code == 200
    assert r.json()["id"] == cid
    assert client.get("/api/v1/clips/nope").status_code == 404


def test_process_creates_completed_task(client):
    # 先取 stream-001 的切片数作为期望值
    expected = client.get("/api/v1/clips?stream_id=stream-001&page_size=100").json()["total"]
    r = client.post("/api/v1/process", json={"stream_ids": ["stream-001"], "name": "pytest 单场切片"})
    assert r.status_code == 200
    task = r.json()
    assert task["status"] == "completed"
    assert task["progress"] == 100.0
    assert task["total_streams"] == 1
    assert task["processed_streams"] == 1
    assert task["clips_generated"] == expected
    assert task["name"] == "pytest 单场切片"


def test_process_multi_stream(client):
    r = client.post("/api/v1/process", json={"stream_ids": ["stream-001", "stream-002", "stream-003"]})
    assert r.status_code == 200
    task = r.json()
    assert task["total_streams"] == 3
    assert task["processed_streams"] == 3
    # clips_generated 应等于三场直播的切片总数
    assert task["clips_generated"] == len(m._all_clips)


def test_process_invalid_stream_400(client):
    r = client.post("/api/v1/process", json={"stream_ids": ["does-not-exist"]})
    assert r.status_code == 400
    assert "不存在" in r.json()["detail"]


def test_tasks_list_includes_seed_and_new(client):
    # 新建一个任务
    client.post("/api/v1/process", json={"stream_ids": ["stream-002"], "name": "临时任务"})
    r = client.get("/api/v1/tasks")
    data = r.json()
    ids = {t["id"] for t in data["items"]}
    assert "task-001" in ids  # seed 任务
    assert data["total"] >= 2


def test_get_task_seed(client):
    r = client.get("/api/v1/tasks/task-001")
    assert r.status_code == 200
    assert r.json()["name"] == "3月直播批量切片"


def test_get_task_404(client):
    assert client.get("/api/v1/tasks/nope").status_code == 404


def test_stats(client):
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_streams"] == 3
    assert data["total_clips"] >= 1
    assert 0 <= data["avg_score"] <= 95
    assert 0 <= data["top_score"] <= 95
    assert data["completed_tasks"] >= 1
    assert isinstance(data["top_keywords"], list)
    # total_clips 与 /clips 一致
    assert data["total_clips"] == client.get("/api/v1/clips?page_size=100").json()["total"]
