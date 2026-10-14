"""P07 集成测试：走真实 HTTP 层（TestClient），覆盖上传→打标→检索→生成→效果→跨模块链路。

模型与 P06 调用在 conftest 里被打桩，测试进程不发真实网络请求。
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app import config

def png_bytes(size=(320, 240)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "#3370FF").save(buf, "PNG")
    return buf.getvalue()


def upload(client, name="测试素材", tags="防晒,夏季", auto_tag="false", content=None,
           filename="a.png", ctype="image/png", description="户外清爽防晒"):
    return client.post(
        "/api/v1/assets",
        data={"name": name, "asset_type": "image", "tags": tags,
              "description": description, "auto_tag": auto_tag},
        files={"file": (filename, io.BytesIO(content if content is not None else png_bytes()), ctype)},
    )


# ── 基础与健康 ──

def test_health_and_llm_status_degraded(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["llm_configured"] is False
    s = client.get("/api/v1/llm/status").json()
    assert s["configured"] is False and s["reason"]


def test_stats_reflects_seed(client):
    s = client.get("/api/v1/stats").json()
    assert s["total_assets"] == 12
    assert s["by_type"]["image"] == 9
    assert s["with_preview_file"] == 11          # 文案类素材本就没有图
    assert 0 < s["coverage_rate"] < 1


def test_list_pagination_and_filters(client):
    page1 = client.get("/api/v1/assets?page=1&size=5").json()
    page3 = client.get("/api/v1/assets?page=3&size=5").json()
    assert page1["total"] == 12 and len(page1["items"]) == 5 and len(page3["items"]) == 2
    assert {i["asset_id"] for i in page1["items"]}.isdisjoint({i["asset_id"] for i in page3["items"]})
    assert client.get("/api/v1/assets?asset_type=copy").json()["total"] == 1
    assert client.get("/api/v1/assets?keyword=防晒").json()["items"][0]["asset_id"] == "AST-007"


def test_list_order_is_by_newest_first(client):
    items = client.get("/api/v1/assets?size=50").json()["items"]
    dates = [i["created_at"] for i in items]
    assert dates == sorted(dates, reverse=True)  # 旧版所有 demo 行同一时间戳，排序失效


# ── 上传 / 预览 / 删除 ──

def test_upload_reads_real_dimensions_and_timestamp(client):
    r = upload(client, name="测试竖版图", content=png_bytes((200, 400)))
    assert r.status_code == 201
    a = r.json()
    assert a["width"] == 200 and a["height"] == 400
    assert a["mime_type"] == "image/png" and a["file_size"] > 0
    assert a["created_at"].startswith("20") and a["created_at"] != "2026-10-12T10:00:00"
    assert a["file_url"] == f"/api/v1/assets/{a['asset_id']}/file"
    assert (config.UPLOAD_DIR / f"{a['asset_id']}.png").is_file()


def test_asset_file_route(client):
    a = upload(client).json()
    got = client.get(f"/api/v1/assets/{a['asset_id']}/file")
    assert got.status_code == 200 and got.headers["content-type"] == "image/png"
    assert got.content == png_bytes()


def test_upload_sniffs_mime_instead_of_trusting_client(client):
    r = upload(client, name="伪装成图片的脚本", filename="evil.png", ctype="image/png",
               content=b"\x7fELF" + b"0" * 100)
    assert r.status_code == 422 and "无法识别的文件类型" in r.json()["detail"]


def test_upload_rejects_oversize(client):
    r = upload(client, content=b"\x89PNG\r\n\x1a\n" + b"0" * (33 * 1024 * 1024))
    assert r.status_code == 422 and "超过上限" in r.json()["detail"]


def test_create_without_file_still_works(client):
    r = client.post("/api/v1/assets", data={"name": "纯文案素材", "asset_type": "copy",
                                             "tags": "文案", "description": "无附件"})
    assert r.status_code == 201
    a = r.json()
    assert a["file_size"] == 0 and a["file_url"] is None
    assert client.get(f"/api/v1/assets/{a['asset_id']}/file").status_code == 404


def test_tags_are_always_arrays(client):
    a = upload(client, tags="护肤,夏季，主图").json()   # 中英逗号混用 + 无 JSON
    assert a["tags"] == ["护肤", "夏季", "主图"]
    assert client.get(f"/api/v1/assets/{a['asset_id']}").json()["tags"] == ["护肤", "夏季", "主图"]


def test_delete_removes_row_and_file(client):
    a = upload(client).json()
    path = config.UPLOAD_DIR / f"{a['asset_id']}.png"
    assert path.is_file()
    r = client.delete(f"/api/v1/assets/{a['asset_id']}")
    assert r.status_code == 200 and r.json()["file_removed"] is True
    assert not path.exists()
    assert client.get(f"/api/v1/assets/{a['asset_id']}").status_code == 404
    assert client.get("/api/v1/assets").json()["total"] == 12


def test_patch_updates_fields(client):
    a = upload(client).json()
    r = client.patch(f"/api/v1/assets/{a['asset_id']}", json={"description": "改过的描述", "tags": ["新"]})
    assert r.status_code == 200 and r.json()["description"] == "改过的描述" and r.json()["tags"] == ["新"]
    assert client.patch(f"/api/v1/assets/{a['asset_id']}", json={}).status_code == 422


# ── 检索 ──

@pytest.mark.parametrize("query,expected", [
    ("夏天清爽的防晒霜", "AST-007"),
    ("有没有直播用的背景板", "AST-005"),
    ("双十一预售的海报", "AST-009"),
    ("科技感运动鞋详情", "AST-004"),
    ("以旧换新的活动图", "AST-012"),
])
def test_natural_language_queries_hit(client, query, expected):
    """旧实现（split + 子串包含）在这类中文长句上全部 0 命中。"""
    r = client.post("/api/v1/search", json={"query": query, "top_k": 5}).json()
    assert r["refused"] is False, r.get("reason")
    assert expected in [i["asset_id"] for i in r["items"]]


def test_search_refuses_when_no_match(client):
    r = client.post("/api/v1/search", json={"query": "库里没有的无人机航拍素材"}).json()
    assert r["refused"] is True and r["items"] == [] and "阈值" in r["reason"]


def test_search_explains_hits_with_surface_terms(client):
    r = client.post("/api/v1/search", json={"query": "直播背景板"}).json()
    hit = r["items"][0]
    assert 0 < hit["relevance_score"] <= 1
    terms = [m["term"] for m in hit["matched_terms"]]
    assert any("直播" in t for t in terms)
    assert not any(t.startswith("syn") for t in terms)   # 内部同义组号不外泄


def test_search_type_filter_and_empty_query(client):
    r = client.post("/api/v1/search", json={"query": "防晒", "asset_type": "copy"}).json()
    assert r["refused"] is True and r["reason"]
    bad = client.post("/api/v1/search", json={"query": ""})
    assert bad.status_code == 422


def test_search_hits_newly_uploaded_asset(client):
    a = upload(client, name="夜间修护精华露主图", tags="精华,修护",
               description="夜间修护抗老精华").json()
    r = client.post("/api/v1/search", json={"query": "夜间修护精华"}).json()
    assert a["asset_id"] in [i["asset_id"] for i in r["items"]]


# ── 智能打标 ──

def test_tagging_degrades_to_rule_and_says_so(client, env):
    r = client.post("/api/v1/assets/AST-001/tag", json={"overwrite": True})
    assert r.status_code == 200
    body = r.json()
    assert body["tag_source"] == "rule"
    assert "护肤" in body["tags"] and "主图" in body["tags"]
    assert "模型不可用" in body["degraded_reason"]
    assert client.get("/api/v1/assets/AST-001").json()["tag_source"] == "rule"


def test_tagging_uses_llm_when_available(client, fake_llm):
    fake_llm({"tags": ["精华", "抗老", "夜间修护"], "category": "美妆", "season": "全年"})
    r = client.post("/api/v1/assets/AST-006/tag", json={"overwrite": True}).json()
    assert r["tag_source"] == "llm" and r["tags"] == ["精华", "抗老", "夜间修护"]
    assert r["meta"]["model"] == "stub-model" and r["meta"]["latency_ms"] == 12.3


def test_tagging_appends_without_overwrite(client, fake_llm):
    fake_llm({"tags": ["新标签"]})
    before = client.get("/api/v1/assets/AST-005").json()["tags"]
    r = client.post("/api/v1/assets/AST-005/tag", json={"overwrite": False}).json()
    assert set(before) <= set(r["tags"]) and "新标签" in r["tags"]


def test_tagging_rejects_garbage_llm_output(client, fake_llm):
    fake_llm({"tags": ["含,逗号的坏标签", 1234567890, "", "正常标签"]})
    r = client.post("/api/v1/assets/AST-003/tag", json={}).json()
    assert "含,逗号的坏标签" not in r["tags"] and "正常标签" in r["tags"]


def test_upload_with_auto_tag(client, fake_llm):
    fake_llm({"tags": ["防晒", "户外", "喷雾"]})
    a = upload(client, name="自动打标素材", auto_tag="true").json()
    assert a["tag_source"] == "llm" and a["tags"] == ["防晒", "户外", "喷雾"]
    assert a["tagging"]["meta"]["source"] == "llm"


# ── 生成 ──

def test_generate_copy_uses_llm_and_saves_body(client, fake_llm):
    fake_llm({"title": "清爽一夏", "subtitle": "控油不紧绷",
                           "bullets": ["a", "b", "c"], "cta": "立即抢购", "tags": ["夏季"]})
    r = client.post("/api/v1/generate", json={"prompt": "夏季控油防晒", "asset_type": "copy",
                                              "style": "commercial", "save_to_library": True}).json()
    assert r["source"] == "llm" and r["result"]["title"] == "清爽一夏"
    saved = r["saved_asset"]
    assert saved["source"] == "generated" and "清爽一夏" in saved["content"]
    assert client.get(f"/api/v1/assets/{saved['asset_id']}").json()["content"].startswith("清爽一夏")


def test_generate_copy_falls_back_to_rule_template(client):
    r = client.post("/api/v1/generate", json={"prompt": "春季新品", "asset_type": "copy"}).json()
    assert r["source"] == "rule" and "规则模板兜底" in r["note"]


def test_generate_video_script_is_structured(client, fake_llm):
    fake_llm({"title": "15s 脚本", "total_seconds": 15,
                           "scenes": [{"time": "0-3s", "shot": "特写", "voice": "口播", "on_screen_text": "字"}],
                           "tags": ["短视频"]})
    r = client.post("/api/v1/generate", json={"prompt": "口红试色", "asset_type": "video"}).json()
    assert r["content_type"] == "video_script" and r["source"] == "llm"
    assert r["result"]["scenes"][0]["time"] == "0-3s"


def test_generate_image_writes_real_file(client):
    r = client.post("/api/v1/generate", json={"prompt": "618大促家电海报", "asset_type": "image",
                                              "style": "creative", "save_to_library": True}).json()
    assert r["source"] == "programmatic"
    assert r["file"]["width"] == 800 and r["file"]["size"] > 1000
    assert r["preview_data_url"].startswith("data:image/png;base64,")
    saved = r["saved_asset"]
    got = client.get(f"/api/v1/assets/{saved['asset_id']}/file")
    assert got.status_code == 200 and got.headers["content-type"] == "image/png"
    assert "非真实 AI 出图" in r["note"]


def test_generate_validates_prompt(client):
    assert client.post("/api/v1/generate", json={"prompt": "a"}).status_code == 422
    assert client.post("/api/v1/generate", json={"prompt": "合法提示词", "asset_type": "gif"}).status_code == 422


# ── 投放效果 ──

def test_performance_create_and_report(client):
    r = client.post("/api/v1/assets/AST-001/performance", json={
        "store_name": "云枢旗舰店", "platform": "kuaishou", "impressions": 10000, "clicks": 600,
        "conversions": 30, "spend": 1000, "revenue": 6000,
        "period_start": "2026-10-01", "period_end": "2026-10-10"})
    assert r.status_code == 201 and len(r.json()["performance"]) == 2
    row = next(i for i in client.get("/api/v1/reports/performance").json()["items"]
               if i["platform"] == "kuaishou")
    assert row["ctr"] == 0.06 and row["cvr"] == 0.05 and row["roi"] == 6.0


@pytest.mark.parametrize("payload", [
    {"store_name": "x", "impressions": 10, "clicks": 20, "conversions": 1, "spend": 1,
     "revenue": 1, "period_start": "2026-10-01", "period_end": "2026-10-02"},
    {"store_name": "x", "impressions": 10, "clicks": 5, "conversions": 9, "spend": 1,
     "revenue": 1, "period_start": "2026-10-01", "period_end": "2026-10-02"},
    {"store_name": "x", "impressions": 10, "clicks": 5, "conversions": 1, "spend": -1,
     "revenue": 1, "period_start": "2026-10-01", "period_end": "2026-10-02"},
])
def test_performance_funnel_validation(client, payload):
    assert client.post("/api/v1/assets/AST-001/performance", json=payload).status_code == 422


def test_performance_rejects_unknown_platform_and_asset(client):
    bad = {"store_name": "x", "platform": "wechat", "impressions": 1, "clicks": 0, "conversions": 0,
           "spend": 0, "revenue": 0, "period_start": "2026-10-01", "period_end": "2026-10-02"}
    assert client.post("/api/v1/assets/AST-001/performance", json=bad).status_code == 422
    ok_payload = {**bad, "platform": "douyin"}
    assert client.post("/api/v1/assets/AST-999/performance", json=ok_payload).status_code == 404


def test_report_carries_p06_availability(client):
    pm = client.get("/api/v1/reports/performance").json()["platform_metrics"]
    assert pm["available"] is False and "P06" in pm["reason"]


def test_report_platform_filter(client):
    items = client.get("/api/v1/reports/performance?platform=douyin").json()["items"]
    assert items and {i["platform"] for i in items} == {"douyin"}


# ── 跨模块推送 ──

def test_ingest_accepts_whitelisted_source(client):
    r = client.post("/api/v1/ingest", json={
        "source": "p02-ecommerce-ops", "name": "P02 推送文案", "asset_type": "copy",
        "tags": ["气垫"], "description": "来自 P02", "content": "正文", "origin_id": "p02-1"})
    assert r.status_code == 201
    a = r.json()["asset"]
    assert a["source"] == "ingest:p02-ecommerce-ops" and a["content"] == "正文"


def test_ingest_rejects_unknown_source(client):
    r = client.post("/api/v1/ingest", json={"source": "whoever", "name": "匿名"})
    assert r.status_code == 403 and "白名单" in r.json()["detail"]


def test_ingest_requires_token_when_configured(client, monkeypatch):
    settings = config.Settings(_env_file=None, P07_INGEST_TOKEN="secret-token")
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    body = {"source": "p02-ecommerce-ops", "name": "带来源的推送"}
    assert client.post("/api/v1/ingest", json=body).status_code == 401
    assert client.post("/api/v1/ingest", json=body, headers={"X-P07-Ingest-Token": "wrong"}).status_code == 401
    assert client.post("/api/v1/ingest", json=body, headers={"X-P07-Ingest-Token": "secret-token"}).status_code == 201


def test_ingest_with_auto_tag(client, fake_llm):
    fake_llm({"tags": ["种草", "底妆"]})
    r = client.post("/api/v1/ingest", json={"source": "manual", "name": "推送并打标",
                                            "asset_type": "copy", "auto_tag": True}).json()
    assert r["asset"]["tags"] == ["种草", "底妆"] and r["asset"]["tag_source"] == "llm"


# ── 404 与不存在 ──

def test_missing_asset_endpoints_return_404(client):
    for path in ("/api/v1/assets/AST-NOPE", "/api/v1/assets/AST-NOPE/file"):
        assert client.get(path).status_code == 404
    assert client.delete("/api/v1/assets/AST-NOPE").status_code == 404
    assert client.post("/api/v1/assets/AST-NOPE/tag", json={}).status_code == 404
    assert client.patch("/api/v1/assets/AST-NOPE", json={"name": "x"}).status_code == 404
