# 视频生成端到端实测：走项目服务函数 + 数据库解析的配置，测量真实耗时。
import json
import os
import sys
import time
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

for line in (API_DIR / ".env.sqlite").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
os.environ["DATABASE_URL"] = "sqlite:///./local_dev.db"

from app.services.model_settings import get_runtime_settings  # noqa: E402
from app.services.video_generation import (  # noqa: E402
    _extract_dashscope_video_url,
    create_dashscope_video_task,
    poll_dashscope_video_task,
)

report: dict = {}
try:
    settings = get_runtime_settings()
    report["config"] = {
        "provider": settings.video_provider,
        "model": settings.video_model,
        "size": settings.video_size,
        "duration": settings.video_duration,
        "interval": settings.video_poll_interval_seconds,
        "max_attempts": settings.video_poll_max_attempts,
    }
    # 测试用 9 分钟预算（不占用用户配置的 15 分钟上限）
    import copy

    probe_settings = copy.copy(settings)
    probe_settings.video_poll_max_attempts = 54
    started = time.time()
    task_id = create_dashscope_video_task(
        "一只橘猫在窗台伸懒腰，阳光洒进来，温馨治愈的氛围", probe_settings
    )
    report["task_id"] = task_id
    result = poll_dashscope_video_task(task_id, probe_settings)
    video_url = _extract_dashscope_video_url(result)
    report["ok"] = True
    report["elapsed_seconds"] = round(time.time() - started, 1)
    report["url"] = video_url
except Exception as exc:  # noqa: BLE001
    report["ok"] = False
    report["error"] = str(exc)[:400]

out = Path("C:/Users/23329/AppData/Local/Temp/verify_video_report.json")
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False)[:1200])
