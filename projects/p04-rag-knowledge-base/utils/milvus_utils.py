# knowledge_base\utils\milvus_utils.py
from pymilvus import MilvusClient, AnnSearchRequest, WeightedRanker
from tool.logger import logger
from config.milvus_config import milvus_config

# 单例
_milvus_client = None

def get_milvus_client():

    global _milvus_client
    if _milvus_client is not None:
        return _milvus_client# 存在直接返回

    # 创建对象
    _milvus_client = MilvusClient(milvus_config.milvus_url)# 不存在就创建  客户端 只会创建一次
    return _milvus_client


def escape_milvus_string(value: str) -> str:
    """
    Milvus数据库过滤表达式中字符串的安全转义函数（防止解析失败）
    作用：
        转义特殊字符（反斜杠、双引号），避免Milvus解析filter时报错
    参数：
        value: 需要转义的原始字符串
    返回：
        str: 转义后的安全字符串
    """
    # 转义反斜杠（\ → \\） 双引号（" → \"） 单引号（' → \'）
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return value

# utils/milvus_utils.py
# 在这个文件中添加如下方法
# 创建了2个请求
def create_hybrid_search_requests(dense_vector, sparse_vector, dense_params=None, sparse_params=None, expr=None,
                                  limit=5):
    """
    构建Milvus混合搜索请求对象
    分别创建稠密/稀疏向量的搜索请求，用于后续混合搜索融合
    :param dense_vector: 文本生成的稠密向量
    :param sparse_vector: 文本生成的稀疏向量
    :param dense_params: 稠密向量搜索参数，默认使用余弦相似度
    :param sparse_params: 稀疏向量搜索参数，默认使用内积相似度
    :param expr: 搜索过滤表达式，用于精准筛选数据
    :param limit: 单向量搜索返回结果数量，默认5
    :return: 搜索请求列表，包含[dense_req, sparse_req]
    """
    # 稠密向量默认搜索参数：余弦相似度（COSINE），适配BGE-M3稠密向量
    if dense_params is None:
        dense_params = {"metric_type": "COSINE"}
    # 稀疏向量默认搜索参数：内积（IP），适配BGE-M3稀疏向量
    if sparse_params is None:
        sparse_params = {"metric_type": "IP"}

    # 构建稠密向量搜索请求，关联Milvus的dense_vector字段 近似最近邻（ANN）检索请求的核心类
    dense_req = AnnSearchRequest(
        data=[dense_vector],# 数据（稠密向量）
        anns_field="dense_vector",# 要查的字段 名称
        param=dense_params,#相似度规则
        expr=expr,
        limit=limit # 召回条数
    )

    # 构建稀疏向量搜索请求，关联Milvus的sparse_vector字段
    sparse_req = AnnSearchRequest(
        data=[sparse_vector],
        anns_field="sparse_vector",
        param=sparse_params,
        expr=expr,
        limit=limit
    )
    # 配置参数
    return [dense_req, sparse_req]

# 开始 相应向量数据库的检索
# 两路检索  稠密向量检索：近似检索   稀疏向量检索：精确（关键字）检索
def hybrid_search(client, collection_name, reqs, ranker_weights=(0.5, 0.5), norm_score=False, limit=5,
                  output_fields=None, search_params=None):
    """
    执行Milvus稠密+稀疏向量混合搜索
    基于WeightedRanker实现双向量搜索结果加权融合，提升检索准确性
    :param client: MilvusClient实例
    :param collection_name: 集合名称
    :param reqs: 搜索请求列表，固定为[dense_req, sparse_req]
    :param ranker_weights: 加权融合权重，默认(0.5,0.5)，依次对应稠密/稀疏向量
    :param norm_score: 是否归一化评分后再融合，避免评分量级差异导致权重失效
    :param limit: 混合搜索最终返回结果数量，默认5
    :param output_fields: 需要返回的字段列表，默认返回item_name
    :param search_params: 搜索参数，如ef/topk等，默认None
    :return: 混合搜索结果列表，搜索失败返回None
    """
    try:
        # 初始化加权排名器：按权重融合稠密/稀疏向量的搜索结果
        # norm_score=True：先将两个向量评分归一化到0~1区间，再加权计算，避免一个得分特别大、另一个特别小导致权重失效。
        # 版本：V2.4
        # 创建排名器（加权排名）   RRF 倒排融合
        rerank = WeightedRanker(ranker_weights[0], ranker_weights[1], norm_score=norm_score)
        # 默认返回字段：文档标识字段
        if output_fields is None:
            output_fields = ["item_name"]

        # 执行混合搜索：融合稠密+稀疏向量结果，按权重重新排序
        # 开始执行  去向量数据库  里面去找 相似的片段 然后 融合这些结果（近似、关键字查询的结果） 重新排序
        res = client.hybrid_search(
            collection_name=collection_name,# 集合名称 表
            reqs=reqs,# 请求
            ranker=rerank,# 使用排序器
            limit=limit,# 返回条数限制
            output_fields=output_fields,# 输出的内容
            search_params=search_params# 搜索参数
        )

        logger.info(f"Milvus混合搜索完成，集合[{collection_name}]共检索到{len(res[0])}条结果")
        return res
    except Exception as e:
        logger.error(f"Milvus混合搜索执行失败，集合[{collection_name}]：{str(e)}", exc_info=True)
        return None


# ------------------------------------------------------------------ 按文档清理向量
# 说明：kb_chunks 与 kb_item_names 都没有 task_id 字段，能反查一个文档的标量只有
# file_title（入库时取的是文件名去扩展名）。删除表达式沿用入库节点里已验证的写法：
# filter=f"file_title=='{escape_milvus_string(t)}'"。


def _file_title_filter(file_title: str, owner: str = None) -> str:
    """构造按 file_title（可选叠加 owner 动态字段）过滤的表达式。"""
    expr = 'file_title==\'%s\'' % escape_milvus_string(file_title)
    if owner:
        expr += ' and owner==\'%s\'' % escape_milvus_string(owner)
    return expr


def count_chunks_by_file_title(file_title: str, owner: str = None) -> int:
    """统计某文档在 kb_chunks 里的切片条数。

    用于两处：入库完成后把真实 chunk_count 回写 MongoDB；删除前给调用方一个可核对的数字。
    单次 query 上限按 Milvus 的 16384 取，超出时只统计到 16384（并在日志里说明）。
    """
    if not file_title:
        return 0
    try:
        client = get_milvus_client()
        rows = client.query(
            collection_name=milvus_config.chunks_collection,
            filter=_file_title_filter(file_title, owner),
            output_fields=["chunk_id"],
            limit=16384,
        )
        return len(rows or [])
    except Exception as e:
        logger.error("统计 kb_chunks 切片数失败 file_title=%s：%s" % (file_title, e), exc_info=True)
        return 0


def delete_vectors_by_file_title(file_title: str, owner: str = None) -> dict:
    """删除某文档在两个集合里的全部向量，返回各自删除条数。

    先删向量、后删 MongoDB 记录：Milvus 删除不可回滚，但反过来会留下永远查不回来的孤儿向量。
    """
    removed = {"chunks": 0, "item_names": 0}
    if not file_title:
        return removed
    client = get_milvus_client()
    expr = _file_title_filter(file_title, owner)

    try:
        rows = client.query(
            collection_name=milvus_config.chunks_collection,
            filter=expr, output_fields=["chunk_id"], limit=16384)
        removed["chunks"] = len(rows or [])
        client.delete(collection_name=milvus_config.chunks_collection, filter=expr)
    except Exception as e:
        logger.error("删除 kb_chunks 失败 file_title=%s：%s" % (file_title, e), exc_info=True)
        raise

    try:
        rows = client.query(
            collection_name=milvus_config.item_name_collection,
            filter=expr, output_fields=["pk"], limit=16384)
        removed["item_names"] = len(rows or [])
        client.delete(collection_name=milvus_config.item_name_collection, filter=expr)
    except Exception as e:
        # 主体名称集合删不掉时不阻断：切片已清，检索不会再命中该文档，这里只记警告
        logger.warning("删除 kb_item_names 失败 file_title=%s：%s" % (file_title, e))

    try:
        client.flush(collection_name=milvus_config.chunks_collection)
        client.flush(collection_name=milvus_config.item_name_collection)
    except Exception as e:
        logger.warning("Milvus flush 失败（不影响删除结果）：%s" % e)

    logger.info("已清理文档向量 file_title=%s：切片 %d 条、主体 %d 条"
                % (file_title, removed["chunks"], removed["item_names"]))
    return removed
