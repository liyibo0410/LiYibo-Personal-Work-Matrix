"""Demo 2：连接管理器 —— 按 thread_id 定向推送
==========================================

对照你项目的 api/monitor.py 中的 ConnectionManager：
- connect()        → 对应 manager.connect(websocket, thread_id)
- disconnect()     → 对应 manager.disconnect(websocket, thread_id)
- send_to_thread() → 对应 manager.send_to_thread(message, thread_id)

学完本节掌握：
1. 用 Dict[str, WebSocket] 保存所有活跃连接
2. send_to_thread 实现"只推给指定 thread_id 的那个客户端"
3. 服务端任何地方都能拿到 manager 定向推送（这是关键设计）

运行：
    uvicorn 02_connection_manager:app --port 8000
浏览器打开 02_manager_test.html 测试。
"""
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Demo2 Connection Manager")


class ConnectionManager:
    """管理所有活跃 WebSocket 连接的核心类"""

    def __init__(self):
        # 保存所有连接的字典：thread_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, thread_id: str):
        """新连接注册：1. 接受握手  2. 登记到字典"""
        await websocket.accept()
        self.active_connections[thread_id] = websocket
        print(f"[Manager] 新连接注册: {thread_id}")

    def disconnect(self, thread_id: str):
        """连接断开：从字典中移除"""
        self.active_connections.pop(thread_id, None)
        print(f"[Manager] 连接移除: {thread_id}")

    async def send_to_thread(self, message: dict, thread_id: str):
        """定向推送：只把消息发给指定 thread_id 对应的连接"""
        if thread_id in self.active_connections:
            ws = self.active_connections[thread_id]
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        """广播：推送给所有已连接客户端"""
        for ws in self.active_connections.values():
            await ws.send_json(message)


# 全局唯一的连接管理器实例（对应你项目 api/monitor.py 里的 manager）
manager = ConnectionManager()


@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """每个客户端连上来时，thread_id 从 URL 路径里取"""
    # 1. 注册连接
    await manager.connect(websocket, thread_id)

    try:
        # 2. 监听消息：收到什么就原样回给这个 thread_id
        while True:
            data = await websocket.receive_text()
            # 3. 定向推送（只推给当前 thread_id，不广播）
            await manager.send_to_thread(
                {"type": "echo", "from": thread_id, "content": data},
                thread_id,
            )
    except WebSocketDisconnect:
        manager.disconnect(thread_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)