"""P07 上传文件处理：白名单校验、真实尺寸读取、落盘路径受控。

原实现只写 file_path/file_size，既不读图片宽高（前端尺寸分布全是「未标注」），
也没有任何路由能把文件读回来（预览 404）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app import config

# 素材中心接收的媒体类型 → 入库 asset_type
_ALLOWED: dict[str, str] = {
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
    "image/gif": "image",
    "video/mp4": "video",
    "video/quicktime": "video",
    "video/webm": "video",
}
_EXT_BY_MIME = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif",
    "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
}
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_MAX_BYTES = 32 * 1024 * 1024


def save_upload(content: bytes, declared_type: str, filename: str, asset_id: str) -> dict[str, Any]:
    """校验并落盘。返回 path/size/mime_type/width/height/asset_type。

    以文件头嗅探出的 MIME 为准，客户端声明的 Content-Type 不可信。
    """
    if not content:
        raise ValueError("空文件")
    if len(content) > _MAX_BYTES:
        raise ValueError(f"文件超过上限 {_MAX_BYTES // 1024 // 1024}MB")

    mime = _sniff(content) or declared_type or ""
    if mime not in _ALLOWED:
        raise ValueError(f"不支持的文件类型：{mime or '未知'}（仅接受 png/jpeg/webp/gif/mp4/mov/webm）")

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = (config.UPLOAD_DIR / f"{asset_id}{_EXT_BY_MIME.get(mime, '.bin')}").resolve()
    if config.UPLOAD_DIR.resolve() not in path.parents:
        raise ValueError("落盘路径越界")
    path.write_bytes(content)

    width = height = None
    if mime in _IMAGE_MIMES:
        width, height = _read_size(path)
    return {
        "path": str(path), "size": len(content), "mime_type": mime,
        "width": width, "height": height, "asset_type": _ALLOWED[mime],
        "original_name": Path(filename or "").name,
    }


def _sniff(content: bytes) -> str:
    head = content[:12]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if content[:4] == b"\x1a\x45\xdf\xa3":
        return "video/webm"
    if content[4:8] == b"ftyp":
        return "video/quicktime" if content[8:12].startswith(b"qt") else "video/mp4"
    return ""


def _read_size(path: Path) -> tuple[int | None, int | None]:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as img:  # 只读文件头，不解码整图
            return img.width, img.height
    except (UnidentifiedImageError, OSError, ValueError):
        return None, None  # 截断/损坏的图片：文件仍入库，尺寸按「未标注」处理
