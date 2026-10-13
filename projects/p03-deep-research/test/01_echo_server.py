"""Demo 1：WebSocket 最小回显
====================

学完本节你要掌握 4 件事：
1. @app.websocket("/ws") 定义一个 WebSocket 路由
2. await websocket.accept()     —— 接受握手（必须，否则前端一直 pending）
3. await websocket.receive_text() —— 收一条文本消息（阻塞）
4. await websocket.send_text()    —— 回一条文本消息

运行：
    uvicorn 01_echo_server:app --port 8000
浏览器打开 01_echo_test.html 测试。
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Demo1 Echo")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # 1. 接受握手，建立连接
    #    只有调用 accept() 之后，下面的 receive/send 才可用
    await websocket.accept()
    print("[Server] 客户端已连接")

    try:
        # 2. 进入"一直监听"循环：只要有连接在，这个循环就不会退出
        while True:
            # 3. 阻塞等待客户端发来一条文本消息
            data = await websocket.receive_text()
            print(f"[Server] 收到: {data}")

            # 4. 回显：把收到的原样发回去
            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        # 5. 客户端主动断开时，FastAPI 会抛出这个异常
        #    在这里做清理工作（本 Demo 无需清理，只是打印）
        print("[Server] 客户端已断开连接")

    except Exception as e:
        # 6. 其他异常（例如连接被异常中断）
        print(f"[Server] 连接异常: {e}")


# 允许直接运行：python 01_echo_server.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)