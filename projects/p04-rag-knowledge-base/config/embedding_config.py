# config/embedding_config.py

"""
BGE-M3 嵌入模型配置。

设备选择逻辑：
    .env 中 BGE_DEVICE 可配 cuda:0 / cpu；
    加载时自动检测 CUDA 可用性 —— 配了 cuda 但没有 GPU 时自动退回 cpu，
    避免后续模型加载报错。
"""

from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _auto_device(requested: str | None) -> str:
    """
    根据 CUDA 可用性自动选择设备。
    :param requested: .env 中配置的设备字符串
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
class EmbeddingConfig:
    bge_m3_path: str
    bge_m3: str
    bge_device: str
    bge_fp16: bool

embedding_config = EmbeddingConfig(
    bge_m3_path=os.getenv("BGE_M3_PATH"),
    bge_m3=os.getenv("BGE_M3"),
    # 自动检测 CUDA 可用性：配了 cuda:0 但无 GPU 时退回 cpu
    bge_device=_auto_device(os.getenv("BGE_DEVICE")),
    # 特殊处理：将.env中的1/0转为布尔值，兼容常见的数字/字符串格式
    bge_fp16=os.getenv("BGE_FP16") in ("1", "True", "true", 1)
)
if __name__ == '__main__':
    print(embedding_config.bge_fp16)
    print(embedding_config.bge_m3)
    print(embedding_config.bge_m3_path)
    print(embedding_config.bge_device)