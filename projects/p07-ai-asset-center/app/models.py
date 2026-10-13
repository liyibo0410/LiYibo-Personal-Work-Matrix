"""P07 请求模型（Pydantic v2）：校验只做在系统边界（入站 API），内部层信任自己。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ASSET_TYPES = ("image", "video", "copy")
PLATFORMS = ("douyin", "taobao", "tmall", "pinduoduo", "jd", "kuaishou", "other")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    top_k: int = Field(5, ge=1, le=50)
    asset_type: Literal["image", "video", "copy"] | None = None


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=200)
    asset_type: Literal["image", "video", "copy"] = "image"
    style: Literal["commercial", "creative", "minimal"] = "commercial"
    save_to_library: bool = False


class TagRequest(BaseModel):
    overwrite: bool = True


class AssetPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    tags: list[str] | str | None = None
    asset_type: Literal["image", "video", "copy"] | None = None
    content: str | None = Field(default=None, max_length=5000)


class PerformanceIn(BaseModel):
    store_name: str = Field(min_length=1, max_length=60)
    platform: Literal["douyin", "taobao", "tmall", "pinduoduo", "jd", "kuaishou", "other"] = "douyin"
    impressions: int = Field(0, ge=0)
    clicks: int = Field(0, ge=0)
    conversions: int = Field(0, ge=0)
    spend: float = Field(0, ge=0)
    revenue: float = Field(0, ge=0)
    period_start: str = Field(min_length=10, max_length=10)
    period_end: str = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def _funnel_consistency(self) -> "PerformanceIn":
        if self.clicks > self.impressions:
            raise ValueError("点击数不能大于曝光数")
        if self.conversions > self.clicks:
            raise ValueError("转化数不能大于点击数")
        return self


class IngestRequest(BaseModel):
    """跨模块推送（P02 生成的文案/素材落到 P07 素材库）。"""

    source: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    asset_type: Literal["image", "video", "copy"] = "copy"
    tags: list[str] | str = Field(default_factory=list)
    description: str = Field("", max_length=500)
    content: str = Field("", max_length=5000)
    origin_id: str = Field("", max_length=60)
    auto_tag: bool = False
