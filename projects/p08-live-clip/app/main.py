"""
P08 直播切片系统 - 云枢智能 (CloudPivot)
FastAPI backend with mock ASR, scoring, and batch task management.

MOCK BOUNDARIES:
- ASR: simulated transcripts, not real speech recognition
- Scoring: rule-based mock algorithm, not real ML model
- Video processing: no actual ffmpeg operations
"""

from __future__ import annotations

import math
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    keyword_density: float = Field(..., description="关键词密度得分 (0-100)")
    energy_level: float = Field(..., description="能量/音量峰值得分 (0-100)")
    speech_rate: float = Field(..., description="语速变化得分 (0-100)")
    interaction: float = Field(..., description="互动热度得分 (0-100)")
    keyword_hits: list[str] = Field(default_factory=list, description="命中的关键词列表")
    explanation: str = Field(..., description="评分理由说明")


class ASRSegment(BaseModel):
    id: str
    start: float = Field(..., description="开始时间(秒)")
    end: float = Field(..., description="结束时间(秒)")
    text: str
    speaker: str = "主播"
    confidence: float = Field(0.95, description="识别置信度 (mock)")


class ClipOut(BaseModel):
    id: str
    stream_id: str
    stream_title: str
    title: str
    start_time: float
    end_time: float
    duration: float
    score: float
    score_breakdown: ScoreBreakdown
    transcript_excerpt: str
    tags: list[str]
    status: str
    created_at: str


class StreamOut(BaseModel):
    id: str
    title: str
    platform: str
    streamer: str
    duration_seconds: int
    start_time: str
    status: str
    description: str
    viewer_peak: int
    asr_segments: list[ASRSegment]
    clip_count: int
    thumbnail_color: str


class StreamListItem(BaseModel):
    id: str
    title: str
    platform: str
    streamer: str
    duration_seconds: int
    start_time: str
    status: str
    viewer_peak: int
    clip_count: int
    thumbnail_color: str


class TaskOut(BaseModel):
    id: str
    name: str
    stream_ids: list[str]
    status: str
    progress: float
    total_streams: int
    processed_streams: int
    created_at: str
    completed_at: Optional[str] = None
    clips_generated: int = 0


class StatsOut(BaseModel):
    total_streams: int
    total_clips: int
    avg_score: float
    top_score: float
    processing_tasks: int
    completed_tasks: int
    pending_tasks: int
    total_duration_minutes: float
    top_keywords: list[dict]


class ProcessRequest(BaseModel):
    stream_ids: list[str]
    name: str = "批量切片任务"


class HealthOut(BaseModel):
    status: str
    version: str
    service: str
    mock_boundaries: list[str]


# ---------------------------------------------------------------------------
# Mock data generation
# ---------------------------------------------------------------------------

def _ts(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _gen_asr_segments(stream_id: str, theme: str, duration: int) -> list[ASRSegment]:
    """Generate mock ASR segments for a livestream."""
    scripts: dict[str, list[dict]] = {
        "beauty": [
            {"t": 0, "text": "哈喽大家好，欢迎来到直播间！今天给大家带来我们春季新品发布会"},
            {"t": 15, "text": "第一款产品，是我们研发了整整一年的精华液，含有高浓度烟酰胺"},
            {"t": 35, "text": "大家看这个质地，非常清透，上脸完全不黏腻"},
            {"t": 55, "text": "现在下单立减50元！而且买一送一，只有今天有这个活动"},
            {"t": 80, "text": "我看到弹幕有宝宝问敏感肌能不能用，完全可以！我们做了人体斑贴测试"},
            {"t": 105, "text": "来，三二一，上链接！赶紧拍，库存只有500单"},
            {"t": 130, "text": "哇，已经卖了200单了，大家手速太快了"},
            {"t": 155, "text": "接下来这款面膜是我们的王牌产品，一盒30片，平均下来一片才3块钱"},
            {"t": 180, "text": "成分表第一位就是玻尿酸，保湿效果拉满"},
            {"t": 205, "text": "有宝宝说之前买过觉得好用，今天回购的扣1！哇好多1"},
            {"t": 230, "text": "这款防晒霜是我们的爆款，SPF50+ PA++++，户外完全够用"},
            {"t": 260, "text": "重点来了！今天直播间专属价，原价199，今天只要99！"},
            {"t": 290, "text": "最后再给大家争取了一波福利，关注直播间加粉丝团，送小样三件套"},
            {"t": 320, "text": "感谢大家今天的陪伴，下次直播我们不见不散！"},
        ],
        "food": [
            {"t": 0, "text": "各位吃货宝宝们晚上好！今天带大家云品尝我们家的招牌菜"},
            {"t": 18, "text": "第一道菜，秘制红烧肉，用的是五花肉，肥瘦相间"},
            {"t": 40, "text": "大家看这个色泽，酱香浓郁，入口即化"},
            {"t": 62, "text": "这道菜的关键在于火候控制，大火收汁，小火慢炖两个小时"},
            {"t": 88, "text": "弹幕有人问能不能真空包装发货，可以的！顺丰冷链，48小时到达"},
            {"t": 115, "text": "接下来是酸辣粉！我们的红薯粉是手工制作的，Q弹爽滑"},
            {"t": 140, "text": "这个汤底是用大骨熬了8小时的，绝对不是调料包能比的"},
            {"t": 168, "text": "现在下单三盒装只要59.9，平均一盒不到20块"},
            {"t": 195, "text": "我看到有宝宝说上次买的特别好吃，今天又来回购了，感谢支持！"},
            {"t": 220, "text": "最后给大家上一个硬菜，麻辣小龙虾！每只都刷得干干净净"},
            {"t": 250, "text": "这个麻辣程度刚刚好，不会特别辣但是很入味"},
            {"t": 278, "text": "今天下单送啤酒两罐，夏天配小龙虾绝了！"},
            {"t": 305, "text": "好了今天的直播就到这里，没抢到的宝宝下次早点来哦"},
        ],
        "fashion": [
            {"t": 0, "text": "Hello everyone! 欢迎来到2024春夏新品预览直播间"},
            {"t": 20, "text": "今天给大家展示我们设计师系列的五套look，每一套都是限量款"},
            {"t": 45, "text": "第一套，这件西装外套用的是意大利进口面料，剪裁非常利落"},
            {"t": 72, "text": "大家看这个肩线，完全贴合身形，不会显得过于宽大"},
            {"t": 98, "text": "搭配这条高腰阔腿裤，整体比例拉到最优，显腿长"},
            {"t": 125, "text": "这套适合通勤场景，干练又不失时尚感"},
            {"t": 152, "text": "第二套来了！这条连衣裙是我们本季的明星单品"},
            {"t": 180, "text": "印花是独家设计的，灵感来自莫奈的睡莲，非常浪漫"},
            {"t": 210, "text": "面料是真丝混纺，垂坠感特别好，走起路来飘逸感十足"},
            {"t": 240, "text": "弹幕有人问尺码，这款S到XL都有，模特穿的是M码"},
            {"t": 268, "text": "第三套是休闲风，这件oversize卫衣搭配工装裤，街头感拉满"},
            {"t": 298, "text": "这套限量500件，喜欢的宝宝赶紧下单"},
            {"t": 328, "text": "最后两套我们快速过一下，这套小香风外套适合约会场景"},
            {"t": 358, "text": "感谢大家观看，新品首发期间全场8折，不要错过"},
        ],
    }

    segments = []
    raw = scripts.get(theme, scripts["beauty"])
    for i, seg in enumerate(raw):
        start = seg["t"]
        if start > duration:
            break
        end = min(start + random.uniform(8, 18), duration)
        segments.append(
            ASRSegment(
                id=f"{stream_id}-asr-{i:03d}",
                start=round(start, 1),
                end=round(end, 1),
                text=seg["text"],
                speaker="主播" if i % 3 != 2 else "助播",
                confidence=round(random.uniform(0.88, 0.99), 2),
            )
        )
    return segments


def _score_clip(
    text: str,
    start: float,
    end: float,
    theme: str,
) -> ScoreBreakdown:
    """Mock scoring algorithm with deterministic results based on content."""
    keyword_map: dict[str, list[str]] = {
        "beauty": ["精华", "面膜", "防晒", "烟酰胺", "玻尿酸", "买一送一", "立减", "链接", "敏感肌", "回购", "福利", "下单"],
        "food": ["红烧肉", "酸辣粉", "小龙虾", "手工", "大骨", "真空", "冷链", "下单", "回购", "好吃", "顺丰", "福利"],
        "fashion": ["限量", "设计师", "进口面料", "真丝", "明星单品", "独家", "8折", "下单", "S到XL", "通勤", "街头"],
    }
    keywords = keyword_map.get(theme, keyword_map["beauty"])
    hits = [kw for kw in keywords if kw in text]

    # Deterministic-ish scoring based on content
    seed = hash(text[:30]) % 100
    kw_density = min(95, 40 + len(hits) * 12 + (seed % 15))
    energy = min(95, 50 + (seed * 7 % 40))
    rate = min(95, 45 + (seed * 13 % 35))
    interaction = min(95, 35 + (seed * 11 % 45))

    # Boost if interaction words present
    interaction_words = ["宝宝", "弹幕", "扣1", "赶紧", "抢", "下单", "链接"]
    if any(w in text for w in interaction_words):
        interaction = min(95, interaction + 15)

    # Boost if price/promo words present
    promo_words = ["立减", "买一送一", "只要", "折扣", "福利", "8折"]
    if any(w in text for w in promo_words):
        kw_density = min(95, kw_density + 10)

    overall = round(kw_density * 0.3 + energy * 0.2 + rate * 0.2 + interaction * 0.3, 1)

    # Build explanation
    parts = []
    if hits:
        parts.append(f"命中关键词: {', '.join(hits[:5])}")
    if interaction > 70:
        parts.append("高互动片段(观众参与度高)")
    if energy > 70:
        parts.append("主播情绪高涨")
    if rate > 70:
        parts.append("语速节奏变化明显")
    if promo_words and any(w in text for w in promo_words):
        parts.append("包含促销/价格信息(高转化潜力)")
    if not parts:
        parts.append("综合表现中等")

    return ScoreBreakdown(
        keyword_density=round(kw_density, 1),
        energy_level=round(energy, 1),
        speech_rate=round(rate, 1),
        interaction=round(interaction, 1),
        keyword_hits=hits,
        explanation="；".join(parts),
    )


def _generate_clips(stream_id: str, stream_title: str, theme: str, segments: list[ASRSegment]) -> list[dict]:
    """Generate mock clips from ASR segments."""
    clips = []
    # Group every 2-3 consecutive segments into potential clips
    i = 0
    clip_idx = 0
    while i < len(segments) - 1:
        group_size = min(random.choice([2, 3]), len(segments) - i)
        group = segments[i : i + group_size]
        combined_text = "，".join(s.text for s in group)
        start = group[0].start
        end = group[-1].end
        duration = end - start

        if duration < 15:
            i += 1
            continue

        breakdown = _score_clip(combined_text, start, end, theme)
        if breakdown.keyword_density * 0.3 + breakdown.energy_level * 0.2 + breakdown.speech_rate * 0.2 + breakdown.interaction * 0.3 < 50:
            i += 1
            continue

        overall = round(
            breakdown.keyword_density * 0.3
            + breakdown.energy_level * 0.2
            + breakdown.speech_rate * 0.2
            + breakdown.interaction * 0.3,
            1,
        )

        tags = []
        if any(w in combined_text for w in ["下单", "链接", "买一送一", "立减"]):
            tags.append("促销转化")
        if any(w in combined_text for w in ["宝宝", "弹幕", "扣1"]):
            tags.append("高互动")
        if any(w in combined_text for w in ["成分", "面料", "手工"]):
            tags.append("产品卖点")
        if any(w in combined_text for w in ["回购", "好评", "好用"]):
            tags.append("口碑背书")
        if not tags:
            tags.append("精彩片段")

        clip_id = f"{stream_id}-clip-{clip_idx:03d}"
        clips.append(
            {
                "id": clip_id,
                "stream_id": stream_id,
                "stream_title": stream_title,
                "title": f"{stream_title} - 片段{clip_idx + 1}",
                "start_time": start,
                "end_time": end,
                "duration": round(duration, 1),
                "score": overall,
                "score_breakdown": breakdown,
                "transcript_excerpt": combined_text[:200],
                "tags": tags,
                "status": "completed",
                "created_at": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
            }
        )
        clip_idx += 1
        i += group_size

    return clips


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

STREAMS_SEED = [
    {
        "id": "stream-001",
        "title": "春季美妆新品发布会",
        "platform": "抖音",
        "streamer": "小美老师",
        "duration_seconds": 360,
        "start_time": "2024-03-15T19:00:00",
        "status": "completed",
        "description": "春季护肤新品首发直播，涵盖精华液、面膜、防晒三大品类，含多轮促销与互动环节",
        "viewer_peak": 12580,
        "thumbnail_color": "#FF6B9D",
        "theme": "beauty",
    },
    {
        "id": "stream-002",
        "title": "深夜食堂 - 招牌菜专场",
        "platform": "快手",
        "streamer": "美食老王",
        "duration_seconds": 330,
        "start_time": "2024-03-16T21:00:00",
        "status": "completed",
        "description": "美食直播专场，展示红烧肉、酸辣粉、小龙虾等招牌菜品，含冷链发货说明",
        "viewer_peak": 8920,
        "thumbnail_color": "#FF8C42",
        "theme": "food",
    },
    {
        "id": "stream-003",
        "title": "2024春夏新品预览",
        "platform": "淘宝直播",
        "streamer": "时尚Coco",
        "duration_seconds": 400,
        "start_time": "2024-03-17T14:00:00",
        "status": "completed",
        "description": "设计师系列限量款预览，展示五套春夏穿搭，涵盖通勤、休闲、约会多场景",
        "viewer_peak": 15340,
        "thumbnail_color": "#7B68EE",
        "theme": "fashion",
    },
]

# Pre-generate all data
_all_streams: dict[str, dict] = {}
_all_clips: dict[str, dict] = {}
_all_asr: dict[str, list[ASRSegment]] = {}
_all_tasks: dict[str, dict] = {}

random.seed(42)  # Deterministic mock data

for s in STREAMS_SEED:
    sid = s["id"]
    theme = s["theme"]
    asr_segs = _gen_asr_segments(sid, theme, s["duration_seconds"])
    clips = _generate_clips(sid, s["title"], theme, asr_segs)

    _all_asr[sid] = asr_segs
    for c in clips:
        _all_clips[c["id"]] = c

    stream_out = {**s}
    stream_out["asr_segments"] = asr_segs
    stream_out["clip_count"] = len(clips)
    _all_streams[sid] = stream_out

# Seed a completed batch task
_all_tasks["task-001"] = {
    "id": "task-001",
    "name": "3月直播批量切片",
    "stream_ids": ["stream-001", "stream-002", "stream-003"],
    "status": "completed",
    "progress": 100.0,
    "total_streams": 3,
    "processed_streams": 3,
    "created_at": "2024-03-17T20:00:00",
    "completed_at": "2024-03-17T20:15:00",
    "clips_generated": len(_all_clips),
}

random.seed()  # Re-randomize


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="P08 直播切片系统",
    description="云枢智能 (CloudPivot) - 直播切片提取与管理平台",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# 统一设计系统：挂载仓库根 shared/ 到 /shared，前端引用 tokens.css（配色唯一真源）+ ui-kit.js（主题桥接）
_SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"
if _SHARED_DIR.exists():
    app.mount("/shared", StaticFiles(directory=str(_SHARED_DIR)), name="shared")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthOut)
async def health():
    return HealthOut(
        status="ok",
        version="1.0.0",
        service="p08-live-clip",
        mock_boundaries=[
            "ASR: 模拟语音转文字，非真实语音识别",
            "评分: 基于规则的模拟算法，非真实ML模型",
            "视频处理: 无实际ffmpeg操作",
        ],
    )


@app.get("/api/v1/streams")
async def list_streams(
    platform: Optional[str] = Query(None, description="按平台筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
):
    results = []
    for s in _all_streams.values():
        if platform and s["platform"] != platform:
            continue
        if status and s["status"] != status:
            continue
        results.append(
            StreamListItem(
                id=s["id"],
                title=s["title"],
                platform=s["platform"],
                streamer=s["streamer"],
                duration_seconds=s["duration_seconds"],
                start_time=s["start_time"],
                status=s["status"],
                viewer_peak=s["viewer_peak"],
                clip_count=s["clip_count"],
                thumbnail_color=s["thumbnail_color"],
            )
        )
    return {"items": results, "total": len(results)}


@app.get("/api/v1/streams/{stream_id}")
async def get_stream(stream_id: str):
    if stream_id not in _all_streams:
        raise HTTPException(status_code=404, detail="直播记录不存在")
    s = _all_streams[stream_id]
    return StreamOut(
        id=s["id"],
        title=s["title"],
        platform=s["platform"],
        streamer=s["streamer"],
        duration_seconds=s["duration_seconds"],
        start_time=s["start_time"],
        status=s["status"],
        description=s["description"],
        viewer_peak=s["viewer_peak"],
        asr_segments=s["asr_segments"],
        clip_count=s["clip_count"],
        thumbnail_color=s["thumbnail_color"],
    )


@app.get("/api/v1/clips")
async def list_clips(
    stream_id: Optional[str] = Query(None, description="按直播场次筛选"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    min_score: Optional[float] = Query(None, description="最低评分"),
    sort_by: str = Query("score", description="排序字段: score / created_at / duration"),
    order: str = Query("desc", description="排序方向: asc / desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    results = list(_all_clips.values())

    if stream_id:
        results = [c for c in results if c["stream_id"] == stream_id]
    if tag:
        results = [c for c in results if tag in c["tags"]]
    if min_score is not None:
        results = [c for c in results if c["score"] >= min_score]

    reverse = order == "desc"
    if sort_by == "score":
        results.sort(key=lambda x: x["score"], reverse=reverse)
    elif sort_by == "created_at":
        results.sort(key=lambda x: x["created_at"], reverse=reverse)
    elif sort_by == "duration":
        results.sort(key=lambda x: x["duration"], reverse=reverse)

    total = len(results)
    start_idx = (page - 1) * page_size
    page_items = results[start_idx : start_idx + page_size]

    return {
        "items": [ClipOut(**c) for c in page_items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


@app.get("/api/v1/clips/{clip_id}")
async def get_clip(clip_id: str):
    if clip_id not in _all_clips:
        raise HTTPException(status_code=404, detail="切片不存在")
    return ClipOut(**_all_clips[clip_id])


@app.post("/api/v1/process")
async def start_processing(req: ProcessRequest):
    # Validate stream IDs
    for sid in req.stream_ids:
        if sid not in _all_streams:
            raise HTTPException(status_code=400, detail=f"直播记录 {sid} 不存在")

    task_id = f"task-{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "name": req.name,
        "stream_ids": req.stream_ids,
        "status": "completed",  # Mock: instant completion
        "progress": 100.0,
        "total_streams": len(req.stream_ids),
        "processed_streams": len(req.stream_ids),
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "clips_generated": sum(
            1 for c in _all_clips.values() if c["stream_id"] in req.stream_ids
        ),
    }
    _all_tasks[task_id] = task
    return TaskOut(**task)


@app.get("/api/v1/tasks")
async def list_tasks():
    raw = sorted(_all_tasks.values(), key=lambda x: x["created_at"], reverse=True)
    results = [TaskOut(**t) for t in raw]
    return {"items": results, "total": len(results)}


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in _all_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskOut(**_all_tasks[task_id])


@app.get("/api/v1/stats")
async def get_stats():
    all_clips = list(_all_clips.values())
    scores = [c["score"] for c in all_clips]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    top_score = round(max(scores), 1) if scores else 0

    # Collect all keyword hits
    kw_counter: dict[str, int] = {}
    for c in all_clips:
        sb = c["score_breakdown"]
        hits = sb.keyword_hits if hasattr(sb, "keyword_hits") else sb["keyword_hits"]
        for kw in hits:
            kw_counter[kw] = kw_counter.get(kw, 0) + 1
    top_keywords = sorted(kw_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    total_duration = sum(s["duration_seconds"] for s in _all_streams.values()) / 60.0

    completed = sum(1 for t in _all_tasks.values() if t["status"] == "completed")
    processing = sum(1 for t in _all_tasks.values() if t["status"] == "processing")
    pending = sum(1 for t in _all_tasks.values() if t["status"] == "pending")

    return StatsOut(
        total_streams=len(_all_streams),
        total_clips=len(all_clips),
        avg_score=avg_score,
        top_score=top_score,
        processing_tasks=processing,
        completed_tasks=completed,
        pending_tasks=pending,
        total_duration_minutes=round(total_duration, 1),
        top_keywords=[{"keyword": kw, "count": cnt} for kw, cnt in top_keywords],
    )


# Serve frontend
@app.get("/")
async def serve_index():
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="前端页面不存在")
    return FileResponse(index_path, media_type="text/html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  P08 直播切片系统 - 云枢智能 (CloudPivot)")
    print("  http://127.0.0.1:8080")
    print()
    print("  [MOCK] ASR: 模拟语音转文字")
    print("  [MOCK] 评分: 基于规则的模拟算法")
    print("  [MOCK] 视频处理: 无实际ffmpeg操作")
    print("=" * 60)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info",
    )
