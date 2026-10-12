# 端到端验证：图像（wan2.7-image 同步多模态）+ 视频（happyhorse-1.1-t2v 异步任务）。
# 直接调用项目服务函数，配置来自 api/.env.sqlite；结果写入临时 JSON 报告（沙箱 stdout 不可靠）。
import json
import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

# 注入 .env.sqlite（不覆盖已有环境变量）
env_path = API_DIR / ".env.sqlite"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    os.environ.setdefault(key.strip(), value.strip())

# 用独立 sqlite，避免读到 local_dev.db 里可能残留的旧 provider 设置行
os.environ["DATABASE_URL"] = "sqlite:///./verify_av_tmp.db"

from app.services.image_generation import (  # noqa: E402
    _create_dashscope_wan26_image,
    _extract_dashscope_wan26_image_url,
)
from app.services.model_settings import get_runtime_settings  # noqa: E402
from app.services.video_generation import (  # noqa: E402
    _extract_dashscope_video_url,
    create_dashscope_video_task,
    poll_dashscope_video_task,
)

settings = get_runtime_settings()
report = {
    "image_provider": settings.image_provider,
    "image_model": settings.image_model,
    "image_base_url": settings.image_base_url,
    "video_provider": settings.video_provider,
    "video_model": settings.video_model,
    "video_base_url": settings.video_base_url,
}

# --- 图像：同步多模态生成（走项目真实函数） ---
try:
    result = _create_dashscope_wan26_image(
        "电商主图：纯白背景上一副无线蓝牙耳机，商业摄影质感，柔和布光",
        settings,
    )
    image_url = _extract_dashscope_wan26_image_url(result)
    report["image"] = {"ok": True, "url": image_url}
except Exception as exc:  # noqa: BLE001
    report["image"] = {"ok": False, "error": str(exc)[:400]}

# --- 视频：异步任务 + 轮询（走项目真实函数） ---
try:
    task_id = create_dashscope_video_task(
        "一只橘猫在窗台伸懒腰，阳光洒进来，温馨治愈的氛围",
        settings,
    )
    result = poll_dashscope_video_task(task_id, settings)
    video_url = _extract_dashscope_video_url(result)
    report["video"] = {"ok": True, "task_id": task_id, "url": video_url}
except Exception as exc:  # noqa: BLE001
    report["video"] = {"ok": False, "error": str(exc)[:400]}

out = Path("C:/Users/23329/AppData/Local/Temp/verify_av_report.json")
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False)[:2000])
