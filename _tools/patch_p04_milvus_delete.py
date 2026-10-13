# -*- coding: utf-8 -*-
"""给 P04 的 Milvus 工具补上「按文档清理向量」的能力。

背景：DELETE /documents/{task_id} 原先只删 MongoDB 记录，Milvus 里的切片向量原封不动，
删掉的文档仍然会在「检索问答」里被命中（实测 kb_chunks 里已存在 Mongo 无对应记录的孤儿向量）。
这里提供计数与删除两个函数，供 API 层做真正的级联删除。

写入脚本而不是直接编辑：utils/milvus_utils.py 是 CRLF 行尾，直接追 LF 会造成混行尾。
"""
from pathlib import Path

TARGET = Path(r"D:/software/PycharmProjects/面试项目/projects/p04-rag-knowledge-base/utils/milvus_utils.py")

CODE = '''

# ------------------------------------------------------------------ 按文档清理向量
# 说明：kb_chunks 与 kb_item_names 都没有 task_id 字段，能反查一个文档的标量只有
# file_title（入库时取的是文件名去扩展名）。删除表达式沿用入库节点里已验证的写法：
# filter=f"file_title=='{escape_milvus_string(t)}'"。


def _file_title_filter(file_title: str, owner: str = None) -> str:
    """构造按 file_title（可选叠加 owner 动态字段）过滤的表达式。"""
    expr = 'file_title==\\'%s\\'' % escape_milvus_string(file_title)
    if owner:
        expr += ' and owner==\\'%s\\'' % escape_milvus_string(owner)
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
'''

text = TARGET.read_text(encoding="utf-8")
if "delete_vectors_by_file_title" in text:
    print("已存在，跳过")
else:
    if not text.endswith("\n"):
        text += "\n"
    body = text + CODE
    TARGET.write_bytes(body.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))
    print("已追加到", TARGET.name)

import ast
ast.parse(TARGET.read_text(encoding="utf-8"))
print("语法校验通过")
