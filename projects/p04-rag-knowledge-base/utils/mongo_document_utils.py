# utils/mongo_document_utils.py
"""
文档元数据管理工具类
负责文档上传记录的持久化存储和查询
"""
import os
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from dotenv import load_dotenv

from tool.logger import logger

load_dotenv()


class DocumentMongoTool:
    """MongoDB 文档元数据管理工具类"""

    def __init__(self):
        try:
            self.mongo_url = os.getenv("MONGO_URL")
            self.db_name = os.getenv("MONGO_DB_NAME")
            
            self.client = MongoClient(self.mongo_url)
            self.db = self.client[self.db_name]
            self.documents = self.db["documents"]
            
            # 创建索引：按上传者 + 时间排序
            self.documents.create_index([("owner", ASCENDING), ("created_at", DESCENDING)])
            # 按 task_id 查询的索引
            self.documents.create_index([("task_id", ASCENDING)], unique=True)
            
            logger.info(f"Document MongoDB initialized: {self.db_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Document MongoDB: {e}")
            raise

    def save_document(
        self,
        task_id: str,
        filename: str,
        owner: str,
        file_size: int,
        file_type: str,
        status: str = "processing",
        chunk_count: int = 0,
        item_name: str = "",
        file_path: str = "",
    ) -> str:
        """
        保存文档元数据
        :return: 文档 ID
        """
        doc = {
            "task_id": task_id,
            "filename": filename,
            "owner": owner,
            "file_size": file_size,
            "file_type": file_type,
            "status": status,
            "chunk_count": chunk_count,
            "item_name": item_name,
            "file_path": file_path,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = self.documents.insert_one(doc)
        logger.info(f"Document saved: {task_id} -> {result.inserted_id}")
        return str(result.inserted_id)

    def update_document_status(
        self,
        task_id: str,
        status: str,
        chunk_count: int = None,
        item_name: str = None,
    ):
        """更新文档状态"""
        update_fields = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if chunk_count is not None:
            update_fields["chunk_count"] = chunk_count
        if item_name is not None:
            update_fields["item_name"] = item_name
        
        self.documents.update_one({"task_id": task_id}, {"$set": update_fields})
        logger.info(f"Document status updated: {task_id} -> {status}")

    def get_documents_by_owner(self, owner: str, limit: int = 50) -> List[Dict]:
        """获取指定用户的所有文档"""
        cursor = self.documents.find({"owner": owner}).sort("created_at", DESCENDING).limit(limit)
        docs = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["created_at"] = doc["created_at"].isoformat()
            doc["updated_at"] = doc["updated_at"].isoformat()
            docs.append(doc)
        return docs

    def get_document_by_task_id(self, task_id: str) -> Optional[Dict]:
        """根据 task_id 获取文档"""
        doc = self.documents.find_one({"task_id": task_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            doc["created_at"] = doc["created_at"].isoformat()
            doc["updated_at"] = doc["updated_at"].isoformat()
        return doc

    def delete_document(self, task_id: str) -> bool:
        """删除文档记录"""
        result = self.documents.delete_one({"task_id": task_id})
        return result.deleted_count > 0

    def get_all_documents(self, limit: int = 100) -> List[Dict]:
        """获取所有文档（管理员用）"""
        cursor = self.documents.find().sort("created_at", DESCENDING).limit(limit)
        docs = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["created_at"] = doc["created_at"].isoformat()
            doc["updated_at"] = doc["updated_at"].isoformat()
            docs.append(doc)
        return docs

    def get_statistics(self, owner: Optional[str] = None) -> Dict:
        """获取文档统计信息。

        传 owner 就只统计该租户：文档列表按 owner 过滤，而统计原先数的是全库 ——
        库里有一条历史 test 记录时，页头「共 N 个文档」就和表格行数对不上，
        看起来像「删了却没少」。
        """
        flt = {"owner": owner} if owner else {}
        total_docs = self.documents.count_documents(flt)
        total_chunks = self.documents.aggregate([
            {"$match": flt},
            {"$group": {"_id": None, "total": {"$sum": "$chunk_count"}}}
        ])
        total_chunks = list(total_chunks)
        total_chunks = total_chunks[0]["total"] if total_chunks else 0

        recent_docs = self.documents.count_documents({
            **flt,
            "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
        })
        
        # 获取问答次数（从 chat_message 集合）
        total_qa = 0
        try:
            chat_messages = self.db["chat_message"]
            total_qa = chat_messages.count_documents({})
        except:
            pass
        
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "today_uploads": recent_docs,
            "total_qa": total_qa,
        }

    def search_documents(self, keyword: str, owner: str = "public") -> List[Dict]:
        """全文检索文档"""
        query = {
            "owner": owner,
            "$or": [
                {"filename": {"$regex": keyword, "$options": "i"}},
                {"item_name": {"$regex": keyword, "$options": "i"}},
            ]
        }
        cursor = self.documents.find(query).sort("created_at", DESCENDING).limit(50)
        docs = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["created_at"] = doc["created_at"].isoformat()
            doc["updated_at"] = doc["updated_at"].isoformat()
            docs.append(doc)
        return docs

    def add_tags(self, task_id: str, tags: List[str]):
        """为文档添加标签"""
        self.documents.update_one(
            {"task_id": task_id},
            {"$addToSet": {"tags": {"$each": tags}}, "$set": {"updated_at": datetime.utcnow()}}
        )

    def remove_tags(self, task_id: str, tags: List[str]):
        """移除文档标签"""
        self.documents.update_one(
            {"task_id": task_id},
            {"$pull": {"tags": {"$in": tags}}, "$set": {"updated_at": datetime.utcnow()}}
        )

    def get_all_tags(self, owner: str = "public") -> List[str]:
        """获取所有标签"""
        pipeline = [
            {"$match": {"owner": owner, "tags": {"$exists": True, "$ne": []}}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = list(self.documents.aggregate(pipeline))
        return [{"tag": r["_id"], "count": r["count"]} for r in results]


# 全局单例（懒加载）
_doc_mongo_tool: Optional[DocumentMongoTool] = None


def get_document_mongo_tool() -> DocumentMongoTool:
    """获取文档 MongoDB 工具单例"""
    global _doc_mongo_tool
    if _doc_mongo_tool is None:
        _doc_mongo_tool = DocumentMongoTool()
    return _doc_mongo_tool


# 便捷函数
def save_document_metadata(**kwargs) -> str:
    """保存文档元数据"""
    tool = get_document_mongo_tool()
    return tool.save_document(**kwargs)


def update_document_status(task_id: str, status: str, **kwargs):
    """更新文档状态"""
    tool = get_document_mongo_tool()
    tool.update_document_status(task_id, status, **kwargs)


def get_user_documents(owner: str, limit: int = 50) -> List[Dict]:
    """获取用户文档列表"""
    tool = get_document_mongo_tool()
    return tool.get_documents_by_owner(owner, limit)


def delete_document_record(task_id: str) -> bool:
    """删除文档记录"""
    tool = get_document_mongo_tool()
    return tool.delete_document(task_id)


def get_document_statistics(owner: Optional[str] = None) -> Dict:
    """获取文档统计"""
    tool = get_document_mongo_tool()
    return tool.get_statistics(owner)
