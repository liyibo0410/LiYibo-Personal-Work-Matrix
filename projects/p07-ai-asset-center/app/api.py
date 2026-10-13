"""P07 路由层：只做入参校验、编排 service/repository、出参组装。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile, status

from app import config, repository
from app.models import (
    AssetPatch,
    GenerateRequest,
    IngestRequest,
    PerformanceIn,
    SearchRequest,
    TagRequest,
)
from app.services import data_platform, generation, media, search, tagging

logger = logging.getLogger("p07")
router = APIRouter(prefix="/api/v1", tags=["p07-asset-center"])


@router.get("/stats")
def stats():
    return repository.stats()


@router.get("/llm/status")
def llm_status():
    """前端据此显示「LLM 已接入（模型名）」还是「规则兜底（原因）」，不再写死 Mock 徽章。"""
    from app.services import llm as llm_svc

    return llm_svc.status()


@router.get("/assets")
def list_assets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    asset_type: str | None = None,
    keyword: str | None = None,
):
    total, items = repository.list_assets(page, size, asset_type, keyword)
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def create_asset(
    name: str = Form(...),
    asset_type: str = Form("image"),
    tags: str = Form(""),
    description: str = Form(""),
    auto_tag: bool = Form(False),
    file: UploadFile | None = File(None),
):
    """上传素材：真实尺寸/MIME 嗅探落盘，`auto_tag=true` 时调用智能打标。"""
    stored = None
    asset_id = repository.new_asset_id()
    if file is not None:
        content = await file.read()
        try:
            stored = media.save_upload(content, file.content_type or "", file.filename or "", asset_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    fields: dict = {
        "name": name,
        "asset_type": (stored or {}).get("asset_type", asset_type),
        "tags": repository.normalize_tags(tags),
        "description": description,
        "source": "upload",
    }
    if stored:
        fields.update(
            file_path=stored["path"], file_size=stored["size"], mime_type=stored["mime_type"],
            width=stored["width"], height=stored["height"],
        )

    if auto_tag:
        result = tagging.tag_asset(name, description, fields["asset_type"])
        fields.update(tags=result["tags"], tag_source=result["tag_source"])
        asset = repository.create_asset(**fields)
        asset["tagging"] = result
        return asset

    asset = repository.create_asset(**fields)
    logger.info("asset created id=%s type=%s has_file=%s", asset["asset_id"], fields["asset_type"], bool(stored))
    return asset


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str):
    asset = repository.get_asset(asset_id)
    if not asset:
        raise HTTPException(404, "素材不存在")
    return asset


@router.patch("/assets/{asset_id}")
def patch_asset(asset_id: str, patch: AssetPatch):
    fields = {k: v for k, v in patch.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "没有需要更新的字段")
    asset = repository.update_asset(asset_id, fields)
    if not asset:
        raise HTTPException(404, "素材不存在")
    return asset


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: str):
    file_path = repository.delete_asset(asset_id)
    if file_path is None:
        raise HTTPException(404, "素材不存在")
    if file_path:
        Path(file_path).unlink(missing_ok=True)
    return {"ok": True, "asset_id": asset_id, "file_removed": bool(file_path)}


@router.get("/assets/{asset_id}/file")
def asset_file(asset_id: str):
    from fastapi.responses import FileResponse

    asset = repository.get_asset(asset_id)
    if not asset:
        raise HTTPException(404, "素材不存在")
    path = asset.get("file_path") or ""
    if not path or not Path(path).is_file():
        raise HTTPException(404, "该素材没有可预览的文件（演示文案类素材或文件已丢失）")
    return FileResponse(path, media_type=asset.get("mime_type") or None, filename=f"{asset_id}{Path(path).suffix}")


@router.post("/assets/{asset_id}/tag")
def tag_asset(asset_id: str, req: TagRequest):
    asset = repository.get_asset(asset_id)
    if not asset:
        raise HTTPException(404, "素材不存在")
    result = tagging.tag_asset(asset["name"], asset.get("description", ""), asset["asset_type"])
    tags = result["tags"] if req.overwrite else sorted(set(asset["tags"]) | set(result["tags"]))
    updated = repository.update_asset(asset_id, {"tags": tags, "tag_source": result["tag_source"]})
    return {"asset_id": asset_id, "tags": tags, "tag_source": result["tag_source"],
            "previous_tags": asset["tags"], "meta": result["meta"],
            "degraded_reason": result.get("degraded_reason", ""), "asset": updated}


@router.post("/assets/{asset_id}/performance", status_code=status.HTTP_201_CREATED)
def add_performance(asset_id: str, payload: PerformanceIn):
    if not repository.get_asset(asset_id):
        raise HTTPException(404, "素材不存在")
    return repository.add_performance(asset_id, payload.model_dump())


@router.post("/search")
def search_assets(req: SearchRequest):
    return search.search(repository.active_assets(), req.query, req.top_k, req.asset_type)


@router.post("/generate")
def generate_asset(req: GenerateRequest):
    result = generation.generate(req.prompt, req.asset_type, req.style)
    if not req.save_to_library:
        return result

    content = result["result"]
    if result["content_type"] == "image":
        file = result["file"]
        asset = repository.create_asset(
            name=content["title"], asset_type="image", tags=content["tags"],
            description=content["description"], file_path=file["path"], file_size=file["size"],
            width=file["width"], height=file["height"], mime_type=file["mime_type"],
            source="generated", tag_source="manual",
        )
    else:
        body = _content_to_text(result["content_type"], content)
        asset = repository.create_asset(
            name=content["title"], asset_type="copy", tags=content.get("tags", []),
            description=body[:200], content=body, source="generated",
            tag_source=result["source"],
        )
    asset["file_url"] = f"/api/v1/assets/{asset['asset_id']}/file" if asset.get("file_path") else None
    return {**result, "saved_asset": asset}


def _content_to_text(content_type: str, payload: dict) -> str:
    if content_type == "copy":
        lines = [payload.get("title", ""), payload.get("subtitle", "")]
        lines += [f"- {b}" for b in payload.get("bullets", [])]
        lines.append(payload.get("cta", ""))
        return "\n".join(line for line in lines if line)
    scenes = payload.get("scenes", [])
    lines = [payload.get("title", ""), f"总时长 {payload.get('total_seconds', '-')}s"]
    lines += [f"{s.get('time')}｜{s.get('shot')}｜口播：{s.get('voice')}｜字幕：{s.get('on_screen_text')}" for s in scenes]
    return "\n".join(line for line in lines if line)


@router.get("/reports/performance")
def performance_report(platform: str | None = None, with_platform_metrics: bool = True):
    items = repository.performance_report(platform)
    payload: dict = {"total": len(items), "items": items}
    if with_platform_metrics:
        payload["platform_metrics"] = data_platform.fetch_platform_metrics()
    return payload


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest(req: IngestRequest, request: Request,
           x_p07_ingest_token: str | None = Header(default=None, alias="X-P07-Ingest-Token")):
    """跨模块写入口：P02 等模块把生成的文案/素材推送到素材库。

    配置了 `P07_INGEST_TOKEN` 就必须带对；未配置时只放行白名单 source，避免匿名写入。
    """
    settings = config.get_settings()
    if settings.P07_INGEST_TOKEN:
        if x_p07_ingest_token != settings.P07_INGEST_TOKEN:
            raise HTTPException(401, "ingest 令牌缺失或不匹配")
    elif req.source not in config.INGEST_SOURCES:
        raise HTTPException(403, f"来源 {req.source!r} 不在白名单 {sorted(config.INGEST_SOURCES)} 内")

    tags = repository.normalize_tags(req.tags)
    tag_source = "manual"
    if req.auto_tag:
        result = tagging.tag_asset(req.name, req.description, req.asset_type)
        tags, tag_source = result["tags"], result["tag_source"]

    asset = repository.create_asset(
        name=req.name, asset_type=req.asset_type, tags=tags, description=req.description,
        content=req.content, source=f"ingest:{req.source}", tag_source=tag_source,
    )
    logger.info("ingest source=%s origin_id=%s asset_id=%s", req.source, req.origin_id, asset["asset_id"])
    return {"ok": True, "asset": asset, "caller": request.client.host if request.client else ""}
