"""P03 问数端到端真调用验证：POST /api/task + WebSocket 事件流，落盘为验收证据。

用法：projects/p03-deep-research/.venv 内执行
    python _evidence/p03/verify_llm_e2e.py ["要问的问题"]
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import websockets

API = "http://127.0.0.1:8030/api/task"
WS = "ws://127.0.0.1:8030/ws/{tid}"
OUT_DIR = Path(__file__).resolve().parent
TIMEOUT_S = 300.0


def post_task(query: str, thread_id: str) -> dict:
    body = json.dumps({"query": query, "thread_id": thread_id}).encode()
    req = urllib.request.Request(API, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


async def collect(query: str, thread_id: str) -> list[dict]:
    events: list[dict] = []
    async with websockets.connect(WS.format(tid=thread_id), max_size=None) as ws:
        await asyncio.sleep(0.5)
        post_task(query, thread_id)
        deadline = time.monotonic() + TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(1.0, deadline - time.monotonic()))
            except asyncio.TimeoutError:
                break
            ev = json.loads(raw)
            events.append(ev)
            kind = ev.get("event")
            if kind in ("task_result", "error"):
                await asyncio.sleep(1.0)
                break
    return events


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "2024年国内新能源车企销量排名前三是哪些？简要说明依据。"
    thread_id = uuid.uuid4().hex[:12]
    t0 = time.perf_counter()
    events = asyncio.run(collect(query, thread_id))
    elapsed = time.perf_counter() - t0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"e2e-{stamp}.json").write_text(
        json.dumps({"query": query, "thread_id": thread_id, "elapsed_s": round(elapsed, 1),
                    "events": events}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"query: {query}", f"thread_id: {thread_id}",
             f"events: {len(events)}  elapsed: {elapsed:.1f}s", ""]
    for ev in events:
        d = ev.get("data") or {}
        summary = d.get("result") or d.get("tool_name") or d.get("assistant_name") or ""
        lines.append(f"[{ev.get('event')}] {ev.get('message')} {str(summary)[:300]}")
    text = "\n".join(lines)
    (OUT_DIR / f"e2e-{stamp}.log").write_text(text + "\n", encoding="utf-8")

    # 控制台只用 ASCII，避免 GBK 码页把中文打成乱码
    kinds = [str(ev.get("event")) for ev in events]
    print("EVENTS=" + ",".join(kinds))
    print("TERMINAL=" + (kinds[-1] if kinds else "none"))
    print("REAL_ANSWER=" + str(any(k == "task_result" for k in kinds)).lower())
    print("MOCK=" + str(any("mock" in json.dumps(ev, ensure_ascii=False).lower() for ev in events)).lower())
    print(f"FILES=e2e-{stamp}.json | e2e-{stamp}.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
