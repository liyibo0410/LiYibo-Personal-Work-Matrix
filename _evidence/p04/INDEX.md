# P04 RAG 知识库 —— 证据索引

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
