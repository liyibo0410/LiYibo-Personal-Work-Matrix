"""Demo 3：HTTP 启动后台任务 + WebSocket 实时推送进度
================================================

这是与"深度搜索项目"最接近的一个 Demo！

它复刻了项目里这三块的核心交互：
- api/server.py 的 @app.post("/api/task")        → 提交任务
- api/server.py 的 @app.websocket("/ws/{thread_id}") → 订阅进度
- agent/main_agent.py 的 run_deep_agent()       → 后台长任务（这里用 sleep 模拟 Agent 思考）
- api/monitor.py 的 send_to_thread()            → 实时推送

流程（对照项目）：
1. 前端 POST /api/task {"query": "..."} 
2. 服务端生成 thread_id，asyncio.create_task 启动后台任务，立即返回
   {"status": "started", "thread_id": "..."}
3. 前端拿到 thread_id 后，建立 WebSocket 连接 ws://.../ws/thread_id
4. 后台任务每执行一步，就调 manager.send_to_thread() 推一条进度
5. 前端通过 WebSocket 实时收到进度，直到收到 task_result

运行：
    uvicorn 03_task_push:app --port 8000
浏览器打开 03_task_push_test.html 测试。
"""
import asyncio
import uuid
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="Demo3 Task Push")
# =========加上这一段CORS=========
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 1. 连接管理器 ====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, thread_id: str):
        await websocket.accept()
        self.active_connections[thread_id] = websocket

    def disconnect(self, thread_id: str):
        self.active_connections.pop(thread_id, None)

    async def send_to_thread(self, message: dict, thread_id: str):
        """定向推送进度（对应项目 monitor.send_to_thread）"""
        if thread_id in self.active_connections:
            await self.active_connections[thread_id].send_json(message)


manager = ConnectionManager()


# ==================== 2. 后台长任务（对应 run_deep_agent） ====================
async def run_long_task(query: str, thread_id: str):
    """模拟 Agent 的思考过程：分步骤执行并逐步推送进度。"""
    try:
        steps = [
            ("assistant_call", "正在分析任务需求..."),
            ("tool_start",     "正在调用网络搜索助手..."),
            ("tool_start",     "正在查询数据库..."),
            ("tool_end",       "工具执行完成，正在汇总结果..."),
        ]
        for step_type, msg in steps:
            await asyncio.sleep(1)
            await manager.send_to_thread(
                {"type": "monitor_event", "step": step_type, "message": msg},
                thread_id,
            )
        # 单独发送最终结果 type=task_result，匹配前端判断
        await asyncio.sleep(1)
        await manager.send_to_thread(
            {"type": "task_result", "message": f"任务完成！你的问题是: {query}"},
            thread_id,
        )
    except Exception as e:
        await manager.send_to_thread({"type":"error","msg":repr(e)}, thread_id)


# ==================== 3. HTTP 接口：提交任务，立即返回 ====================
class TaskRequest(BaseModel):
    query: str
    thread_id: str | None = None


@app.post("/api/task")
async def run_task(request: TaskRequest):
    # 1. 生成或复用 thread_id（对应项目：request.thread_id or str(uuid.uuid4())）
    thread_id = request.thread_id or str(uuid.uuid4())

    # 2. 把后台任务放进事件循环执行，不阻塞当前请求！
    #    （对应项目：asyncio.create_task(run_deep_agent(request.query, thread_id))）
    asyncio.create_task(run_long_task(request.query, thread_id))

    # 3. 立即返回，让前端拿到 thread_id 去连 WebSocket
    return {"status": "started", "thread_id": thread_id}


# ==================== 4. WebSocket：订阅 thread_id 的进度 ====================
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(websocket, thread_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(thread_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)