# P07 AI 素材中心 API 集成测试
# 覆盖验收门禁：上传素材→打标→以文搜图命中；素材与投放效果关联报表可查看。

import io


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats_has_demo_seed(client):
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_assets"] == 12
    assert data["by_type"]["image"] >= 1
    assert data["linked_performance"] == 7
    # ROI = 收入 / 花费，demo 数据花费>0
    assert data["roi"] > 0


def test_list_assets_pagination(client):
    r = client.get("/api/v1/assets?page=1&size=5")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 12
    assert len(data["items"]) == 5
    assert data["page"] == 1

    r2 = client.get("/api/v1/assets?page=3&size=5")
    assert len(r2.json()["items"]) == 2  # 12 = 5+5+2


def test_list_assets_filter_by_type(client):
    r = client.get("/api/v1/assets?asset_type=video")
    data = r.json()
    assert data["total"] == 2
    assert all(it["asset_type"] == "video" for it in data["items"])


def test_list_assets_keyword_filter(client):
    r = client.get("/api/v1/assets?keyword=防晒")
    data = r.json()
    assert data["total"] >= 1
    assert any("防晒" in it["name"] or "防晒" in it["tags"] for it in data["items"])


def test_get_asset_with_performance(client):
    r = client.get("/api/v1/assets/AST-001")
    assert r.status_code == 200
    data = r.json()
    assert data["asset_id"] == "AST-001"
    assert isinstance(data["performance"], list)
    assert len(data["performance"]) >= 1
    assert data["performance"][0]["platform"] == "douyin"


def test_get_asset_404(client):
    r = client.get("/api/v1/assets/NOT-EXIST")
    assert r.status_code == 404


def test_create_asset_upload_and_delete(client):
    # 上传：multipart/form-data，file 字段
    files = {"file": ("test.png", io.BytesIO(b"fake-image-bytes"), "image/png")}
    form = {"name": "测试素材", "asset_type": "image", "tags": '["测试","上传"]', "description": "pytest 上传"}
    r = client.post("/api/v1/assets", data=form, files=files)
    assert r.status_code == 200
    created = r.json()
    asset_id = created["asset_id"]
    assert created["name"] == "测试素材"
    assert created["source"] == "upload"
    assert created["file_size"] == len(b"fake-image-bytes")

    # 新素材可被查到，总数 +1
    r2 = client.get("/api/v1/stats")
    assert r2.json()["total_assets"] == 13

    # 删除
    r3 = client.delete(f"/api/v1/assets/{asset_id}")
    assert r3.status_code == 200
    assert r3.json()["ok"] is True

    # 删除后 404
    assert client.get(f"/api/v1/assets/{asset_id}").status_code == 404
    assert client.get("/api/v1/stats").json()["total_assets"] == 12


def test_create_asset_without_file(client):
    form = {"name": "纯文案素材", "asset_type": "copy", "tags": '["文案"]', "description": "无文件"}
    r = client.post("/api/v1/assets", data=form)
    assert r.status_code == 200
    created = r.json()
    assert created["file_size"] == 0
    assert created["file_path"] == ""


def test_delete_asset_404(client):
    r = client.delete("/api/v1/assets/NOT-EXIST")
    assert r.status_code == 404


def test_search_by_text_hits(client):
    # 以文搜图：查询「防晒 夏天」应命中 AST-007（防晒霜对比图，tags 含 防晒/夏天）
    r = client.post("/api/v1/search", json={"query": "防晒 夏天", "top_k": 5})
    assert r.status_code == 200
    data = r.json()
    assert "mock_note" in data  # mock 边界标注
    assert data["total"] >= 1
    ids = [it["asset_id"] for it in data["items"]]
    assert "AST-007" in ids
    # relevance_score 归一化，最高分为 1
    assert max(it["relevance_score"] for it in data["items"]) == 1.0


def test_search_filter_by_type(client):
    r = client.post("/api/v1/search", json={"query": "短视频", "top_k": 5, "asset_type": "video"})
    data = r.json()
    assert all(it["asset_type"] == "video" for it in data["items"])


def test_search_no_match_returns_empty(client):
    r = client.post("/api/v1/search", json={"query": "zzzznomatch", "top_k": 5})
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []


def test_generate_image_mock(client):
    r = client.post("/api/v1/generate", json={"prompt": "春季护肤海报", "asset_type": "image", "style": "commercial"})
    assert r.status_code == 200
    data = r.json()
    assert "mock_note" in data  # mock 边界标注
    assert data["asset_type"] == "image"
    assert "result" in data
    assert "title" in data["result"]


def test_generate_video_mock(client):
    r = client.post("/api/v1/generate", json={"prompt": "口红试色", "asset_type": "video"})
    data = r.json()
    assert data["result"].get("mock_script")


def test_generate_copy_mock(client):
    r = client.post("/api/v1/generate", json={"prompt": "面膜保湿", "asset_type": "copy"})
    data = r.json()
    assert data["result"].get("mock_copy")


def test_performance_report(client):
    r = client.get("/api/v1/reports/performance")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 7
    item = data["items"][0]
    # 关联报表字段：CTR/CVR/ROI 由 SQL 计算
    for key in ("ctr", "cvr", "roi", "asset_id", "platform", "revenue"):
        assert key in item
    # 按 revenue 降序
    revenues = [it["revenue"] for it in data["items"]]
    assert revenues == sorted(revenues, reverse=True)


def test_performance_report_filter_platform(client):
    r = client.get("/api/v1/reports/performance?platform=douyin")
    data = r.json()
    assert data["total"] == 3
    assert all(it["platform"] == "douyin" for it in data["items"])
