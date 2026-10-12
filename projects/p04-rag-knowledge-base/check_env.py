"""
环境自检脚本：验证 P04 RAG 知识库的中间件、配置、依赖是否就绪。
输出每项检查结果，方便定位问题。
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# mock vertexai 防止 ragas 导入时崩溃（与 eval_compare.py 保持一致）
if "langchain_community.chat_models.vertexai" not in sys.modules:
    sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

results = []

# 1. .env 文件
env_exists = (PROJECT_ROOT / ".env").exists()
results.append((".env 文件存在", env_exists, ""))

# 2. 关键环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

required_vars = [
    "OPENAI_API_KEY", "OPENAI_API_BASE", "LLM_DEFAULT_MODEL",
    "BGE_M3_PATH", "BGE_RERANKER_LARGE",
    "MILVUS_URL", "MONGO_URL", "MINIO_ENDPOINT",
    "MCP_API_KEY", "TEXT_RERANK_MODEL",
    "EMBEDDING_DIM", "RERANK_BACKEND",
]
for var in required_vars:
    val = os.getenv(var, "")
    ok = bool(val)
    display = val[:20] + "..." if len(val) > 20 else val
    results.append((f"ENV: {var}", ok, display))

# 3. BGE-M3 模型路径
bge_path = os.getenv("BGE_M3_PATH", "")
bge_exists = Path(bge_path).exists() if bge_path else False
results.append(("BGE-M3 模型路径存在", bge_exists, bge_path))

# 4. BGE-reranker 模型路径
reranker_path = os.getenv("BGE_RERANKER_LARGE", "")
reranker_exists = Path(reranker_path).exists() if reranker_path else False
results.append(("BGE-reranker 模型路径存在", reranker_exists, reranker_path))

# 5. EMBEDDING_DIM 值检查
emb_dim = os.getenv("EMBEDDING_DIM", "")
dim_ok = emb_dim == "1024"
results.append(("EMBEDDING_DIM=1024（匹配 BGE-M3）", dim_ok, f"当前值: {emb_dim}"))

# 6. EMBEDDING_MODEL 已移除
emb_model = os.getenv("EMBEDDING_MODEL", "")
results.append(("EMBEDDING_MODEL 已移除（死配置）", not emb_model, f"当前值: '{emb_model}'" if emb_model else "已清除"))

# 7. Docker 容器连通性
try:
    from pymilvus import connections
    connections.connect(uri=os.getenv("MILVUS_URL", ""))
    milvus_ok = True
    connections.disconnect("default")
except Exception as e:
    milvus_ok = False
results.append(("Milvus 连接", milvus_ok, str(e) if not milvus_ok else "OK"))

try:
    import pymongo
    client = pymongo.MongoClient(os.getenv("MONGO_URL", ""), serverSelectionTimeoutMS=3000)
    client.server_info()
    mongo_ok = True
    client.close()
except Exception as e:
    mongo_ok = False
results.append(("MongoDB 连接", mongo_ok, str(e) if not mongo_ok else "OK"))

try:
    from minio import Minio
    minio_client = Minio(
        os.getenv("MINIO_ENDPOINT", ""),
        access_key=os.getenv("MINIO_ACCESS_KEY", ""),
        secret_key=os.getenv("MINIO_SECRET_KEY", ""),
        secure=False,
    )
    minio_client.list_buckets()
    minio_ok = True
except Exception as e:
    minio_ok = False
results.append(("MinIO 连接", minio_ok, str(e) if not minio_ok else "OK"))

# 8. 关键依赖
for pkg in ["FlagEmbedding", "dashscope", "langgraph", "pymilvus", "ragas"]:
    try:
        __import__(pkg)
        results.append((f"依赖: {pkg}", True, ""))
    except ImportError:
        results.append((f"依赖: {pkg}", False, "未安装"))

# 输出结果
print("\n" + "=" * 60)
print("P04 RAG 知识库 环境自检")
print("=" * 60)
pass_count = 0
fail_count = 0
for name, ok, detail in results:
    status = "PASS" if ok else "FAIL"
    if ok:
        pass_count += 1
    else:
        fail_count += 1
    detail_str = f" ({detail})" if detail else ""
    print(f"  [{status}] {name}{detail_str}")

print(f"\n总计: {pass_count} 通过, {fail_count} 失败")
print("=" * 60)
