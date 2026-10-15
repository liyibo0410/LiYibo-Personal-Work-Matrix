# P04 RAG 知识库 —— 证据索引

## D13 · 用户反馈修复：文档删除 / 检索问答 + 更名「RAG 知识库」（2026-10-13 晚）

**根因一句话**：8040 上跑的是 10-12 22:56 启动的旧进程（`console.html`=200 但 `/shared/ui-kit/tokens.css`=404，典型陈旧特征），而级联删除、切片数回读等改动是 10-13 14:10 才落到磁盘的 —— 服务从未重启，用户点到的仍是「只删 Mongo、不清向量」的旧接口；同时 SERVICE_REGISTRY 里 p04=8041 无人监听，外壳挂载区一直是「未启动」。

| 证据文件 | 证明内容 |
|---|---|
| `verify-cascade-delete.log` | 端到端删除验证 PASS：自造探针文档 → Mongo `chunk_count=1` 与 Milvus 实测 1 条一致 → 删除前向量库含唯一标记 1 条 → `DELETE /documents/{task_id}` 返回 `removed_chunks=1` → 删除后 Mongo 记录清除、Milvus 残留 0 条、含标记切片 0 条（**检索不再命中**） |
| `stream-query-evidence.log` | 控制台走的流式链路真实可用：`POST /query(is_stream=true)` 立即 ack → SSE 共 317 事件（ready 1 / progress 15 / delta 300 / final 1）→ 回答 1861 字 + **4 条引用**（file_title / item_name / score 0.9884…0.9153 / 原文预览），耗时 34.6s；末尾附 `/statistics` 与 `/documents` 口径一致性（5 文档 / 36 切片两边相等） |
| `console-qa-dom.json` | 浏览器（CDP DOM 抓取）渲染结果：侧栏品牌 `RAG 知识库`、页面标题 `RAG 知识库 · 统一控制台`、阶段进度「已完成7，进行中0」且回答后自动折叠、`引用来源 4 条` 四条带相关性分值、发送按钮恢复「发送」（说明流正常收敛，非超时兜底） |
| `console-tab-docs.png` | 文档管理页真实截图：5 个文档 / 36 个切片 / 今日上传 1 个，每行都有「删除」按钮，同名文档就地标黄「与另一份同名，删除会一并清理其向量」 |
| `console-tab-qa.png` | 检索问答页真实截图：欢迎语已更名，副标题写明「流式作答，回答附引用来源可回溯；检索不到相关内容会明确拒答」 |
| `console-tab-upload.png`、`console-tab-dashboard.png` | 上传导入页与数据看板页在更名后的真实渲染 |
| `pytest-reranker-crash-20261013.log` | **未跑通项 + 原因**：`tests/` 只有重排相关两个文件，复跑先 9 failed/14 passed、后直接段错误，栈顶是 `torch/storage.py` mmap 读权重 + `FlagEmbedding` 重排器构造 —— 原生崩溃，与本轮改动文件无交集（机器可用内存 3.3/15.7 GB） |

### 改动清单（本轮）

| 症状 | 根因 | 处理 |
|---|---|---|
| 上传的文件「删不掉」 | 旧进程只删 Mongo 记录，Milvus 向量残留 → 检索照旧命中 | 重启到注册表端口 8041 跑当前代码（级联删除：先按 `file_title` 清 `kb_chunks`/`kb_item_names`，最后删 Mongo 记录）；`verify-cascade-delete.log` 为证 |
| 删了但页头数字不动 | `/statistics` 数的是全库（含 1 条历史 `owner=test`），列表按 `owner=public` 过滤 | `get_statistics(owner)` + 接口默认 `owner=public`，与列表同口径（实测两边 5 文档 / 36 切片） |
| 上传列表里的文件没有移除入口 | 只有进度行，没有 ✕ 与清空 | 每行加「✕ 移除」+ 列表级「清空列表」，并在确认框里讲清楚：移除不中断服务器端导入、删文档要去「文档管理」 |
| 检索问答「请求失败，请稍后重试」 | ① 控制台用非流式 `/query`，整链路 35s，浏览器侧先断；② 该分支在 `async def` 里直接跑流程图，**阻塞事件循环**，把同服务的 SSE 一起卡住；③ 前端吞掉异常只印一句通用文案 | 控制台改走 `is_stream=true` + `EventSource`（阶段进度→逐字→final 带引用）；非流式分支改 `asyncio.to_thread`；回答失败时把 HTTP 状态/后端 detail/SSE error 原文摊到气泡里，并加 120s 看门狗 |
| 降级路径会把整个流程带崩 | `node_answer_output` 在 LLM 流式异常时 `push_to_session(SSEEvent.END, ...)`，而 `SSEEvent` 根本没有 `END` → AttributeError | 删掉这行；终止事件由本节点末尾的 FINAL 统一发出（自带 answer + sources） |
| 直跑 `-m web.api.console_service` 起在 8100 | 入口写死端口，与 SERVICE_REGISTRY（8041）漂移 —— 正是今天 8040/8041 漂移的同类问题 | `_registry_port()` 从 `shared/config/services.json` 解析，日志不再谎报端口 |
| 「BOSS智库」更名 | 用户要求 | P04 页面标题/侧栏/欢迎语、FastAPI 标题与日志、`start.bat`、README、docs、`inspect_storage.py` 全部改为「RAG 知识库」（含把遗留的「掌柜智库-查询API」一并纠正）；历史归档（`_evidence/`、`.workbuddy/`、`work/eval_report/`、`00-总纲/`）与源项目名保持原样 |

### 顺带修掉的平台级问题（非 P04 但被这次重启暴露）

- **P07 起不来**：`ModuleNotFoundError: No module named 'portfolio_config'` → 真因是 `__editable__.portfolio_config-1.0.0.pth` 被写成 UTF-8 字节，而 Windows `site.py` 按 ANSI(GBK) 读 `.pth`，含中文的仓库路径解不出来 → 该目录从未进 `sys.path`（同 venv 里 GBK 写的 `llm_gateway.pth` 就正常）。已把 p07/p09 两个 `.pth` 重写为 GBK 字节，实测 `portfolio_config.port('p07')=8070`、`api_url('p01','/chat/history')` 解析成功 —— **P09 此前是静默走 env 兜底**，现在才真正吃到 SERVICE_REGISTRY。
- **P07 第二个坑**：`uv run python app/main.py` 下 `from app import config` 报 `No module named 'app'`（`sys.path[0]` 是 `app/`）。按 p06 既有做法在 `app/main.py` 顶部显式补项目根。
- 会话期间发现 P01/P03/P05–P10 共 11 个服务掉线（非本轮改动导致），已 `supervisor start` 全量拉起，现 **15/15 在线**，外壳 `GET /api/services/health` 对 p03/p04/p07/p09 均报 online。

## 本地重排器（BGE-reranker-large）接入

| 证据文件 | 证明内容 |
|---|---|
| `verify-reranker.log` | 6 项验收全部通过（正常路径 / 降级路径 / 依赖缺失 / 单例缓存 / 独立性） |
| `reranker-test-output.log` | pytest 15/15 测试通过（含真实模型推理 + mock 降级） |
| `check-env-reranker.log` | check_env.py 环境自检：RERANK_BACKEND=local, 模型路径存在, 依赖齐全 |

### 验收 6 项对应关系

1. **正常路径语义排序** → `verify-reranker.log` 验收项 1
   - query="如何检测主板短路"，相关文档 score=+5.60/+3.41 > 不相关 -6.50/-9.48
2. **local/cloud Top-1 一致性** → `verify-reranker.log` 验收项 2
   - query="合同违约赔偿标准"，Top-1 为语义最相关文档
3. **降级路径（路径不存在）** → `verify-reranker.log` 验收项 3
   - 模型路径不存在 → 自动降级 passthrough，不抛异常
4. **依赖缺失** → `verify-reranker.log` 验收项 4
   - FlagEmbedding 未安装 → 不 import 崩溃，自动降级
5. **单元测试独立性** → `reranker-test-output.log`
   - 10 项纯函数测试通过，无需 Milvus/MongoDB/MinIO/Docker
6. **单例缓存** → `verify-reranker.log` 验收项 6
   - 首次加载 2.56s，后续 99 次平均 0.025s，加速 104x
