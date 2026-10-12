# config/reranker_config.py

"""
重排器配置模块。

支持两种后端：
  - local：本地 BGE-reranker-large 交叉编码器（敏感文档不出网，零 API 费用）
  - cloud：DashScope TextReRank 云端 API

通过 RERANK_BACKEND 环境变量切换，默认 local。
当 local 不可用时（缺依赖 / 模型缺失 / CUDA 异常），会自动降级到 cloud；
cloud 也不可用时，降级为「不重排」（返回保序递减分数），绝不阻断检索主流程。
"""

from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _auto_device(requested: str | None) -> str:
    """
    根据 CUDA 可用性自动选择设备。
    用户指定了 cuda:0 但 torch 不可用或无 GPU 时，自动退回 cpu，
    避免后续加载模型时报错。
    :param requested: .env 中配置的设备字符串（如 cuda:0 / cpu）
    :return: 实际可用的设备字符串
    """
    if not requested or requested.strip().lower() == "cpu":
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            return requested
        return "cpu"
    except ImportError:
        return "cpu"


@dataclass
class RerankerConfig:
    """
    重排器统一配置。
    cloud 字段（text_rerank_*）与 local 字段（bge_reranker_*）共存，
    由 backend 决定优先使用哪一组。
    """
    # ── 后端选择 ──
    backend: str  # local | cloud

    # ── cloud 通道（DashScope TextReRank）──
    text_rerank_api_key: str  # DashScope API Key
    text_rerank_model: str  # 云端模型名称
    text_rerank_instruct: str  # 云端重排指令

    # ── local 通道（BGE-reranker-large 交叉编码器）──
    bge_reranker_path: str  # 本地模型路径
    bge_reranker_device: str  # 运行设备（cuda:0 / cpu，会自动检测可用性）
    bge_reranker_fp16: bool  # 是否使用半精度


reranker_config = RerankerConfig(
    # 步骤1：读取后端选择，默认 local（全链路私有化部署）
    backend=os.getenv("RERANK_BACKEND", "local").strip().lower(),

    # 步骤2：cloud 通道配置（保留原有字段，不删除）
    text_rerank_api_key=os.getenv("MCP_API_KEY"),
    text_rerank_model=os.getenv("TEXT_RERANK_MODEL"),
    text_rerank_instruct=os.getenv("TEXT_RERANK_INSTRUCT"),

    # 步骤3：local 通道配置（复用 .env 中已有的 BGE_RERANKER_* 变量）
    bge_reranker_path=os.getenv("BGE_RERANKER_LARGE", ""),
    bge_reranker_device=_auto_device(os.getenv("BGE_RERANKER_DEVICE")),
    bge_reranker_fp16=os.getenv("BGE_RERANKER_FP16") in ("1", "True", "true", 1),
)