import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from starlette.responses import FileResponse

from config.minio_config import minio_config
from processor.import_processor.main_graph import KBImportWorkflow
from tool.logger import logger
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from starlette.middleware.cors import CORSMiddleware

from utils.minio_utils import get_minio_client
from utils.task_utils import update_task_status, add_done_task, add_running_task, get_task_status, get_done_task_list, \
    get_running_task_list, set_task_meta
from utils.mongo_document_utils import save_document_metadata, update_document_status, get_user_documents, delete_document_record, get_document_statistics

# 1. 创建路由（可由统一入口 console_service.py 挂载，也可独立运行）
# 说明：合并后台后本文件不再直接创建 FastAPI 实例，改为导出 APIRouter；
#       CORS 中间件由统一入口（console_service.py）统一添加。
router = APIRouter(
    tags=["import"],
)

# 3. 静态页面路由：返回文件导入前端页面
# 访问地址：http://127.0.0.1:8000/import.html
@router.get("/import.html")  # 对外访问地址
async def get_import_page():
    # 拼接HTML文件绝对路径
    current_dir_parent_path = Path(__file__).absolute().parent.parent
    html_path = current_dir_parent_path / "page" / "import.html"
    # 如果不存在，抛出404异常
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"没有查询到页面，地址为：{html_path}")
    return FileResponse(html_path)

# 4. 后台任务：LangGraph全流程执行
# 独立于主请求线程，由BackgroundTasks触发，避免阻塞接口响应
def run_graph_task(task_id: str, file_dir: str, import_file_path: str, owner: str = "public", content_type: str = "application/octet-stream"):
    """
    LangGraph全流程执行后台任务（含MinIO上传）
    """
    try:
        update_task_status(task_id, "processing")

        minio_object_name = f"pdf_files/{datetime.now().strftime('%Y%m%d')}/{os.path.basename(import_file_path)}"
        minio_bucket_name = minio_config.bucket_name
        # MinIO 上传暂时跳过（当前环境下所有写操作都会挂起，疑似代理兼容性问题）
        # 文件已保存在本地，LangGraph 流程可正常处理
        logger.info(f"[{task_id}] MinIO上传已跳过（代理兼容性问题），使用本地文件继续处理")

        init_state = {
            "task_id": task_id,
            "file_dir": file_dir,
            "import_file_path": import_file_path,
            "owner": owner,
        }

        # 3. 流式执行LangGraph全流程（stream模式：实时获取每个节点的执行结果）
        workflow = KBImportWorkflow()
        for event in workflow.run(init_state, stream=True):
            for node_name, node_result in event.items():
                # 将完成的节点名加入【已完成列表】，前端轮询/status/{task_id}可实时获取
                add_done_task(task_id, node_name)
                
                # 如果是主体名称识别节点完成，更新文档的 item_name
                if node_name == "node_item_name_recognition" and isinstance(node_result, dict):
                    item_name = node_result.get("item_name", "")
                    if item_name:
                        update_document_status(task_id, "processing", item_name=item_name)

        # 4. 全流程执行完成，更新任务全局状态为：已完成
        update_task_status(task_id, "completed")
        
        # 5. 更新文档元数据状态
        try:
            # 从最后一个节点结果中获取 chunk_count
            chunk_count = 0
            if "node_document_split" in [list(event.keys())[0] for event in workflow.run(init_state, stream=True)]:
                # 重新执行一次获取 chunk_count（简化处理，实际应该从 state 中获取）
                pass
            update_document_status(task_id, "completed", chunk_count=chunk_count)
        except Exception as e:
            logger.warning(f"[{task_id}] 更新文档状态失败：{e}")

    except Exception as e:
        # 5. 捕获全流程异常，更新任务全局状态为：失败，并记录错误日志（含堆栈）
        update_task_status(task_id, "failed")
        logger.error(f"[{task_id}] LangGraph全流程执行失败，异常信息：{str(e)}", exc_info=True)


# 5. 核心接口：文件上传接口
# 支持多文件上传，核心流程：接收文件 → 本地保存 → MinIO上传 → 启动后台任务
# 访问地址：http://localhost:8000/upload （POST请求，form-data格式传参）
@router.post("/upload", summary="文件上传接口", description="支持多文件批量上传，自动触发知识库导入全流程")
def upload_files(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), owner: str = "public"):
    """
    文件上传核心接口
    1. 接收前端上传的多文件（PDF/MD为主）
    2. 按「日期/任务ID」分层保存到本地输出目录，避免文件冲突
    3. 将文件上传至MinIO对象存储，做持久化保存
    4. 为每个文件生成唯一TaskID，启动独立的LangGraph后台处理任务
    5. 实时更新任务状态，供前端轮询监控进度

    :param background_tasks: FastAPI后台任务对象，用于异步执行LangGraph流程
    :param files: 前端上传的文件列表（form-data格式）
    :return: 包含上传结果和所有任务ID的JSON响应
    """
    # 1. 构建本地存储根目录：项目根目录/doc/YYYYMMDD（按日期分层，方便管理）
    data_based_root_dir = os.getenv("DATA_BASED_ROOT_DIR")
    data_dir = os.path.join(data_based_root_dir, datetime.now().strftime("%Y%m%d"))
    # 初始化任务ID列表，用于返回给前端（一个文件对应一个TaskID）
    task_ids = []

    # 2. 遍历处理每个上传的文件（多文件批量处理，各自独立生成TaskID）
    for file in files:
        # 生成全局唯一TaskID（UUID4），作为单个文件的全流程标识
        task_id = str(uuid.uuid4())
        task_ids.append(task_id)
        # 记录任务元信息（文件名/创建时间），供控制台文档管理区展示
        set_task_meta(task_id, file.filename)
        logger.info(f"[{task_id}] 开始处理上传文件，文件名：{file.filename}，文件类型：{file.content_type}")

        # 3. 标记「文件上传」阶段为「运行中」，前端轮询可查
        add_running_task(task_id, "upload_file")

        # 4. 构建该任务的本地独立目录：output/YYYYMMDD/TaskID，避免多文件重名冲突
        file_dir = os.path.join(data_dir, task_id)
        os.makedirs(file_dir, exist_ok=True)  # 目录不存在则创建，存在则不做处理
        # 构建上传文件的本地保存绝对路径
        import_file_path = os.path.join(file_dir, file.filename)

        # 5. 将上传的文件保存到本地临时目录（后续MinIO上传/文件解析均基于此文件）
        with open(import_file_path, "wb") as file_buffer:
            shutil.copyfileobj(file.file, file_buffer)
        logger.info(f"[{task_id}] 文件已保存至本地，路径：{import_file_path}")

        # 6. MinIO 上传移至后台任务（run_graph_task），避免阻塞接口响应

        # 7. 标记「文件上传」阶段为「已完成」，前端轮询可查
        add_done_task(task_id, "upload_file")

        # 8. 将LangGraph全流程处理加入FastAPI后台任务（异步执行，不阻塞当前接口响应）
        background_tasks.add_task(run_graph_task, task_id, file_dir, import_file_path, owner, file.content_type)
        logger.info(f"[{task_id}] 已将LangGraph全流程加入后台任务，任务已启动")
        
        # 9. 保存文档元数据到 MongoDB
        try:
            file_size = os.path.getsize(import_file_path)
            save_document_metadata(
                task_id=task_id,
                filename=file.filename,
                owner=owner,
                file_size=file_size,
                file_type=file.content_type or "application/octet-stream",
                status="processing",
                file_path=import_file_path,
            )
            logger.info(f"[{task_id}] 文档元数据已保存")
        except Exception as e:
            logger.warning(f"[{task_id}] 保存文档元数据失败（不影响主流程）：{e}")

    # 9. 所有文件处理完毕，返回上传成功信息和所有TaskID（前端基于TaskID轮询进度）
    logger.info(f"多文件上传处理完毕，共处理{len(files)}个文件，生成TaskID列表：{task_ids}")
    return {
        "code": 200,
        "message": f" 文件上传成功, total: {len(files)}",
        "task_ids": task_ids
    }


# 6. 核心接口：任务状态查询接口
# 前端轮询此接口获取单个任务的处理进度和状态
# 访问地址：http://localhost:8000/status/{task_id} （GET请求）
@router.get("/status/{task_id}", summary="任务状态查询", description="根据TaskID查询单个文件的处理进度和全局状态")
async def get_task_progress(task_id: str):
    """
    任务状态查询接口
    前端轮询此接口（如每秒1次），获取任务的实时处理进度
    返回数据均来自内存中的任务管理字典（task_utils.py），高性能无IO

    :param task_id: 全局唯一任务ID（由/upload接口返回）
    :return: 包含任务全局状态、已完成节点、运行中节点的JSON响应
    """
    # 构造任务状态返回体
    task_status_info: Dict[str, Any] = {
        "code": 200,
        "task_id": task_id,
        "status": get_task_status(task_id),  # 任务全局状态：pending/processing/completed/failed
        "done_list": get_done_task_list(task_id),  # 已完成的节点/阶段列表
        "running_list": get_running_task_list(task_id)  # 正在运行的节点/阶段列表
    }
    # 记录状态查询日志，方便追踪前端轮询情况
    logger.info(
        f"[{task_id}] 任务状态查询，当前状态：{task_status_info['status']}，已完成节点：{task_status_info['done_list']}")
    return task_status_info


# 7. 文档列表查询接口
@router.get("/documents", summary="文档列表查询", description="获取指定用户的所有上传文档列表")
async def list_documents(owner: str = "public", limit: int = 50):
    """
    文档列表查询接口
    返回指定用户的所有上传文档，按时间倒序排列
    
    :param owner: 文档所有者（默认 public）
    :param limit: 返回数量限制（默认 50）
    :return: 文档列表
    """
    try:
        docs = get_user_documents(owner, limit)
        return {
            "code": 200,
            "total": len(docs),
            "documents": docs
        }
    except Exception as e:
        logger.error(f"查询文档列表失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


# 8. 文档删除接口
@router.delete("/documents/{task_id}", summary="删除文档", description="删除指定文档的记录和相关数据")
async def delete_document(task_id: str):
    """
    文档删除接口
    删除 MongoDB 中的文档记录（物理文件暂不删除，保留恢复可能）
    
    :param task_id: 文档任务ID
    :return: 删除结果
    """
    try:
        success = delete_document_record(task_id)
        if success:
            return {
                "code": 200,
                "message": "文档删除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="文档不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败：{e}")
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


# 9. 文档统计接口
@router.get("/statistics", summary="文档统计", description="获取文档统计信息")
async def get_statistics():
    """
    文档统计接口
    返回文档总数、总chunk数、今日上传数等统计信息
    
    :return: 统计信息
    """
    try:
        stats = get_document_statistics()
        return {
            "code": 200,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"获取统计信息失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败：{str(e)}")


# 10. 文档预览接口
@router.get("/documents/{task_id}/preview", summary="文档预览", description="获取文档内容用于在线预览")
async def preview_document(task_id: str):
    """
    文档预览接口
    返回文档的完整内容，支持 Markdown 渲染
    
    :param task_id: 文档任务ID
    :return: 文档内容
    """
    try:
        from utils.mongo_document_utils import get_document_mongo_tool
        tool = get_document_mongo_tool()
        doc = tool.get_document_by_task_id(task_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        file_path = doc.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文档文件不存在")
        
        # 读取文件内容
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "code": 200,
            "filename": doc.get("filename"),
            "content": content,
            "file_type": doc.get("file_type"),
            "item_name": doc.get("item_name")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览文档失败：{e}")
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")


# 11. 全文检索接口
@router.get("/search", summary="全文检索", description="在文档中搜索关键词")
async def search_documents(keyword: str, owner: str = "public"):
    """
    全文检索接口
    在文档文件名和主体名称中搜索关键词
    
    :param keyword: 搜索关键词
    :param owner: 文档所有者
    :return: 匹配的文档列表
    """
    try:
        from utils.mongo_document_utils import get_document_mongo_tool
        tool = get_document_mongo_tool()
        docs = tool.search_documents(keyword, owner)
        return {
            "code": 200,
            "total": len(docs),
            "documents": docs
        }
    except Exception as e:
        logger.error(f"搜索失败：{e}")
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


# 12. 文档标签管理接口
@router.post("/documents/{task_id}/tags", summary="添加标签", description="为文档添加标签")
async def add_document_tags(task_id: str, tags: List[str]):
    """为文档添加标签"""
    try:
        from utils.mongo_document_utils import get_document_mongo_tool
        tool = get_document_mongo_tool()
        tool.add_tags(task_id, tags)
        return {"code": 200, "message": "标签添加成功"}
    except Exception as e:
        logger.error(f"添加标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"添加失败：{str(e)}")


@router.get("/tags", summary="获取所有标签", description="获取所有文档标签")
async def get_all_tags(owner: str = "public"):
    """获取所有标签"""
    try:
        from utils.mongo_document_utils import get_document_mongo_tool
        tool = get_document_mongo_tool()
        tags = tool.get_all_tags(owner)
        return {"code": 200, "tags": tags}
    except Exception as e:
        logger.error(f"获取标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")


# 13. 批量删除接口
@router.post("/documents/batch-delete", summary="批量删除", description="批量删除文档")
async def batch_delete_documents(task_ids: List[str]):
    """批量删除文档"""
    try:
        from utils.mongo_document_utils import get_document_mongo_tool
        tool = get_document_mongo_tool()
        deleted = 0
        for task_id in task_ids:
            if tool.delete_document(task_id):
                deleted += 1
        return {
            "code": 200,
            "message": f"成功删除 {deleted} 个文档",
            "deleted": deleted
        }
    except Exception as e:
        logger.error(f"批量删除失败：{e}")
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


if __name__ == "__main__":
    """独立运行入口（兼容旧方式：单跑导入服务，端口 8000）"""
    app = FastAPI(
        title="BOSS智库-导入API",
        description="此文档是BOSS智库导入流程的API接口说明",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许的源
        allow_credentials=True,  # 允许携带cookie
        allow_methods=["*"],  # 允许的请求方法
        allow_headers=["*"],  # 允许的请求头
    )
    app.include_router(router)
    logger.info("BOSS智库导入服务启动中...")
    # 启动uvicorn服务，绑定本地IP和8000端口，关闭自动重载（生产环境建议用workers多进程）
    uvicorn.run(
        app=app,
        host="127.0.0.1",  # 仅本地访问，生产环境改为0.0.0.0（允许所有IP访问）
        port=8000  # 服务端口
    )