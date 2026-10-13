# P09 → P01 跨模块真实 HTTP 调用验证

时间: 2026-10-13 08:43:12

## 数据流闭环
P01 客服会话 → P09 销售考核质检评分（架构规范要求的跨模块真实调用）

## 架构规范落实
- 地址由 cloudpivot_config.api_url('p01','/chat/history') 从 shared/config/services.json 解析，**未硬编码端口**
- P01 health 探针在根路径 /health，用 service_url 拼接（不在 /api 前缀下）
- 支持 CP_P01_HISTORY_URL 显式覆盖（降级演练用）
- 角色映射：P01 user/bot → P09 customer/agent；按 session_id 聚合

## 1. P01 真实接口（先向 P01 播种两轮真实会话，再直接拉取原始历史）
```
P01 /health: {"status":"ok"}
P01 history sender_id=p09-demo-user-1 messages=5
  [user] session=088152dd text=你好，我买的护肤品套装想问下成分
  [bot] session=088152dd text=亲，您同时提到了几个问题，咱们先处理一个，您是想先办业务还是咨询信息呢？
  [user] session=088152dd text=订单三天了还没到，帮我查下
  [bot] session=088152dd text=好的，我们先处理物流查询。
```

## 2. P09 客户端解析地址 + 拉取聚合（真实调用）
```
history_url: http://127.0.0.1:18082/api/chat/history
health: {'ok': True, 'status_code': 200, 'url': 'http://127.0.0.1:18082/health'}
ok=True source=p01-live conversations=2 fetched=['p09-demo-user-1', 'p09-demo-user-2']
```

## 3. P09 端点 POST /api/v1/import/from-p01（导入并评分）
```
GET /api/v1/p01/status -> {'ok': True, 'status_code': 200, 'url': 'http://127.0.0.1:18082/health'}
ok=True degraded=False source=p01-live imported=2
url: http://127.0.0.1:18082/api/chat/history
  conv-p01-p09-demo-user-1-088152dd score=65.5 msgs=5 roles=['agent', 'customer']
  conv-p01-p09-demo-user-2-eaa74914 score=70.5 msgs=5 roles=['agent', 'customer']
```

## 4. 降级演练（CP_P01_HISTORY_URL 指向死端口 59998）
```
ok=False degraded=True source=unavailable
error: P01 客服不可达：timed out
conversations key present: False -> 降级不伪造会话
```

## 5. pytest（含新增跨模块集成测试，monkeypatch 不依赖 P01 在线）
```
  D:\software\PycharmProjects\面试项目\projects\p09-ai-sales-assessment\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
34 passed, 1 warning in 0.10s
```

## 结论
- 正常路径: P09 真实拉取 P01 的 2 段会话（MySQL 持久化），映射角色后规则引擎评分（65.5 / 70.5），source=p01-live
- 降级路径: ok=False/degraded=True/source=unavailable/imported=0，不伪造任何会话
- 34 项 pytest 全绿（含 4 项跨模块集成测试）
- 说明: P01 bot 回复本身受 P01 自有 LLM mock 边界约束（dashscope 免费额度耗尽时降级），但 **P09→P01 的传输与会话数据是真实的**
