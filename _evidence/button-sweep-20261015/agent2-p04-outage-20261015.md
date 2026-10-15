# P04 服务中断证据（测试期间实测，2026-10-15）

> 由 agent2（P01/P04 按钮点击测试）在测试过程中采集。**未修改任何代码/配置**。
> 采集时间：2026-10-15 09:43 ~ 09:50（本地时钟）

## 1. 时间线

| 时刻 | 事实 | 证据来源 |
|---|---|---|
| 09:27:36 | P04 在线：`GET /health` 返回 `ok:true`、依赖 milvus/mongo/minio/embedding/llm 全 `available:true` | curl `http://127.0.0.1:8041/health` |
| 09:39:55 | 浏览器进入公网 `http://39.96.200.45:8090/p04/`，全流程正常（健康条/Tab/上传/预览均可用） | `agent2-0N-p04-*.png` |
| 09:40:21 / 09:40:24 | 两次自建测试文档上传成功（`UI测试-可删-A.md`、`UI测试-可删-B.md`），进入 LangGraph 后台任务 | `_runtime/logs/p04.log` |
| 09:40:54 | 进程内加载 BGE-M3（`FlagEmbedding ... loading existing colbert_linear`），随后 `POST /query` 200 | `_runtime/logs/p04.log:9312-9313` |
| 09:41:04 | 最后一次成功写日志：`httpx2 - INFO - HTTP Request: POST …/chat/completions 200 OK` | `_runtime/logs/p04.log` 末尾 |
| 09:43:xx | 页面问答请求全部失败（UI 侧截图 `agent2-17/18/19-p04-qa-*.png`） | 浏览器实测 |
| 09:44:2x | `curl http://127.0.0.1:8041/documents…` → **exit 7（连接被拒）**；`netstat` 中 **无 8041 监听** | shell 实测 |
| 09:44~ | 公网 `curl -H "Cookie: cp_mod=p04" http://39.96.200.45:8090/health` → **502** | shell 实测 |
| 09:47 | `python _tools\supervisor.py status` → `p04 8041 未启动  P04 RAG 知识库`，`14/15 在线` | supervisor 输出（见下） |

## 2. 关键事实

- **p04.log 在 09:41:04 之后彻底静默**：无 traceback、无 `MemoryError`、无 `Killed`、无优雅退出日志 → 不是 Python 层异常路径，更像**进程被外部终止**（内存压力 / 被别的窗口停掉 / 进程崩溃）。
- **本机 8041 端口无监听**（`netstat -ano | findstr :8041` 无输出），公网侧经 nginx 反代后为 **502**。
- 该进程**不在** supervisor 托管下（supervisor 只把它标为「未启动」，没有自动拉起）。
- 09:40:54 的 BGE-M3 加载说明嵌入模型在**首次查询时**才加载进内存；本机 16GB 内存同时跑 15 个服务 + BGE-M3 + Milvus + MongoDB + 两个 headless Chrome，内存压力是首要嫌疑。

## 3. 原始命令与输出

```
$ curl.exe -s -o NUL -w "%{http_code}" -m 10 http://127.0.0.1:8041/health
000                      # 连接被拒

$ curl.exe -s -o NUL -w "%{http_code}" -m 15 -H "Cookie: cp_mod=p04" http://39.96.200.45:8090/health
502

$ netstat -ano | findstr /R ":8041"        # 无输出（无监听）

$ python -X utf8 _tools\supervisor.py status
服务             端口           状态      说明
--------------------------------------------------------------------
shell          8800         在线       统一外壳网关
p01-commerce   18081        在线       P01 商城中台
p01-api        18082        在线       P01 AI 客服后端
p01-web        5173         在线       P01 AI 客服前端
p02-api        8000         在线       P02 运营助手后端
p02-web        3001         在线       P02 运营助手前端
p03-api        8030         在线       P03 NL3SQL 问数 后端
p03-web        5174         在线       P03 NL2SQL 问数 前端
p04            8041         未启动     P04 RAG 知识库
p05            8770         在线       P05 合同审批
p06            8060         在线       P06 数据中台
p07            8070         在线       P07 AI 素材中心
p08            8080         在线       P08 直播切片
p09            8090         在线       P09 AI 销售考核
p10            8101         在线       P10 模型微调平台
--------------------------------------------------------------------
14/15 在线

$ python -X utf8 -c "...读取 _runtime/logs/p04.log 尾部..."
2026-10-15 09:40:54 - FlagEmbedding.finetune.embedder.encoder_only.m3.runner - INFO - loading existing colbert_linear and sparse_linear---------
2026-10-15 09:40:54 - FlagEmbedding.finetune.embedder.encoder_only.m3.runner - INFO - loading existing colbert_linear and sparse_linear---------
INFO:     36.99.220.216:0 - "POST /query HTTP/1.1" 200 OK
2026-10-15 09:40:56 - root - INFO - node_item_name_confirm 开始执行
INFO:     36.99.220.216:0 - "GET /stream/kb-console-mv8vfn6f-lqc356 HTTP/1.1" 200 OK
2026-10-15 09:40:57 - root - INFO - 步骤3：用户消息已初始保存, ID: 6ad02f29f8298230b3e8a5e3
2026-10-15 09:41:04 - httpx2 - INFO - HTTP Request: POST https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions "HTTP/1.1 200 OK"
<日志到此为止，之后无任何写入>
```

## 4. 判定

- 这是**演示环境可用性缺陷**（P04 单点进程无托管、崩溃后不自动恢复）：读者在演示时若恰好遇到，页面会持续报错且无人拉起 —— 严重度按 P0/P1 之间的「高」处理（已上报给测试报告）。
- 与本次按钮测试**无因果关系**：崩溃前的所有按钮操作（健康检查/切 Tab/上传/搜索/预览）均返回 200（见上方日志）。
- 恢复动作（若需要继续测试）：`python _tools\supervisor.py start p04`（只起 P04 一个服务；本次测试为避免干扰其他窗口，恢复前后均在报告中标注时间）。