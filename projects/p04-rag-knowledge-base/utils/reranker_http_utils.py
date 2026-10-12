# utils/reranker_http_utils.py

"""
重排器工具模块 —— 双后端（local / cloud）+ 三级降级。

降级链路：
    local（本地 BGE-reranker-large）
      → 失败时自动降级 cloud（DashScope TextReRank API）
        → 也失败时降级「不重排」（返回保序递减分数，主流程不中断）

设计原则：
    - rerank_documents() 签名不变，调用方无感知
    - 本地模型单例缓存，首次加载后常驻显存
    - 所有异常路径都有日志记录，绝不向上抛异常阻断检索
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Optional

from config.reranker_config import reranker_config

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 降级状态追踪（供调用方 / 测试查询最近一次调用的实际后端）
# ──────────────────────────────────────────────
_last_backend: str = "none"       # 最近一次调用实际使用的后端：local / cloud / passthrough
_last_degrade_reason: str = ""    # 最近一次降级的原因，空字符串表示未降级

# ──────────────────────────────────────────────
# 本地模型单例（延迟加载，避免 import 时就占显存）
# ──────────────────────────────────────────────
_local_reranker = None
_local_reranker_load_error: Optional[str] = None


def _try_import_flag_reranker():
    """
    尝试导入 FlagReranker，缺依赖时返回 None 而非崩溃。
    FlagEmbedding 与 BGE 系列同源，是加载 bge-reranker-large 最省事的方式。
    :return: FlagReranker 类，或 None（表示未安装）
    """
    try:
        from FlagEmbedding import FlagReranker
        return FlagReranker
    except ImportError:
        logger.warning("FlagEmbedding 未安装，local 重排不可用，将降级到 cloud")
        return None


def _get_local_reranker():
    """
    获取本地 BGE-reranker-large 单例。
    首次调用时加载模型（约 1.2GB），后续复用同一实例。
    加载失败时记录错误并返回 None，下次调用会重试（不缓存失败状态）。

    :return: FlagReranker 实例，或 None（不可用）
    """
    global _local_reranker, _local_reranker_load_error

    if _local_reranker is not None:
        return _local_reranker

    # 步骤1：检查依赖
    FlagReranker = _try_import_flag_reranker()
    if FlagReranker is None:
        _local_reranker_load_error = "FlagEmbedding 未安装"
        return None

    # 步骤2：检查模型路径
    model_path = reranker_config.bge_reranker_path
    if not model_path or not Path(model_path).exists():
        _local_reranker_load_error = f"本地模型路径不存在: {model_path}"
        logger.warning("本地重排模型路径无效: %s，将降级到 cloud", model_path)
        return None

    # 步骤3：加载模型（耗时操作，约 5-15 秒）
    device = reranker_config.bge_reranker_device
    use_fp16 = reranker_config.bge_reranker_fp16
    try:
        logger.info(
            "正在加载本地重排模型: path=%s, device=%s, fp16=%s",
            model_path, device, use_fp16
        )
        t0 = time.time()
        _local_reranker = FlagReranker(
            model_path,
            device=device,
            use_fp16=use_fp16,
        )
        elapsed = time.time() - t0
        logger.info("本地重排模型加载完成，耗时 %.1f 秒", elapsed)
        _local_reranker_load_error = None
        return _local_reranker
    except Exception as exc:
        _local_reranker_load_error = f"模型加载失败: {exc}"
        logger.warning("本地重排模型加载异常，将降级到 cloud: %s", exc)
        return None


def _rerank_local(query: str, documents: list[str]) -> list[float]:
    """
    使用本地 BGE-reranker-large 做交叉编码打分。
    :param query: 用户查询
    :param documents: 候选文档列表
    :return: 与 documents 等长的分数列表（越高越相关）
    :raises RuntimeError: 推理过程出错时抛出，由调用方捕获并降级
    """
    reranker = _get_local_reranker()
    if reranker is None:
        raise RuntimeError(_local_reranker_load_error or "本地重排模型不可用")

    # 步骤1：构造 [query, document] 对
    pairs = [[query, doc] for doc in documents]

    # 步骤2：交叉编码打分
    # FlagReranker.compute_score 对 list[pair] 返回 list[float]
    try:
        scores = reranker.compute_score(pairs)
    except Exception as exc:
        raise RuntimeError(f"本地重排推理失败: {exc}") from exc

    # 步骤3：确保返回格式一致
    # compute_score 对单个 pair 可能返回标量而非列表
    if isinstance(scores, (int, float)):
        scores = [float(scores)]
    else:
        scores = [float(s) for s in scores]

    if len(scores) != len(documents):
        raise RuntimeError(
            f"本地重排返回分数数量不匹配: 期望 {len(documents)}, 实际 {len(scores)}"
        )

    # 步骤4：sigmoid 归一到 0~1（BGE 输出 logits 跨度大，断崖阈值按 0~1 设计）
    raw_scores = scores
    scores = [1.0 / (1.0 + math.exp(-s)) for s in scores]
    logger.debug(
        "sigmoid 归一: raw=%s → normalized=%s",
        [f"{s:.4f}" for s in raw_scores],
        [f"{s:.4f}" for s in scores],
    )

    return scores


def _rerank_cloud(query: str, documents: list[str]) -> list[float]:
    """
    使用 DashScope TextReRank 云端 API 做重排（原有逻辑，保持不变）。
    :param query: 用户查询
    :param documents: 候选文档列表
    :return: 与 documents 等长的分数列表（越高越相关）
    :raises RuntimeError: API 调用失败时抛出
    """
    import dashscope

    api_key = reranker_config.text_rerank_api_key
    if not api_key:
        raise RuntimeError("未配置 MCP_API_KEY（DashScope API Key）")
    if not reranker_config.text_rerank_model:
        raise RuntimeError("未配置 TEXT_RERANK_MODEL")

    dashscope.api_key = api_key
    response = dashscope.TextReRank.call(
        model=reranker_config.text_rerank_model,
        query=query,
        documents=documents,
        top_n=len(documents),
        return_documents=False,
        instruct=reranker_config.text_rerank_instruct,
    )

    status_code = response.get("status_code")
    if status_code != 200:
        message = response.get("message")
        raise RuntimeError(f"DashScope rerank 调用失败: {message}")

    results = response.output.get("results", [])
    scores = [0.0] * len(documents)
    for item in results:
        index = item.get("index")
        score = item.get("relevance_score")
        scores[int(index)] = float(score)
    return scores


def _rerank_passthrough(documents: list[str]) -> list[float]:
    """
    降级兜底：不重排，返回保序的递减分数。
    分数设计为 [1.0, 0.99, 0.98, ...]，确保排序后保持原始顺序，
    且后续断崖检测不会误触发截断（相邻差距极小）。
    :param documents: 候选文档列表
    :return: 与 documents 等长的保序递减分数
    """
    return [max(0.01, 1.0 - 0.01 * i) for i in range(len(documents))]


def rerank_documents(query: str, documents: list[str]) -> list[float]:
    """
    对候选文档进行重排序打分（双后端 + 三级降级）。

    降级链路：
        1. backend=local → 本地 BGE-reranker-large 交叉编码
        2. local 失败 → 自动降级 cloud（DashScope TextReRank API）
        3. cloud 也失败 → 降级「不重排」，返回保序递减分数

    函数签名保持不变，调用方（node_rerank.py）无需任何修改。
    通过模块级变量 _last_backend / _last_degrade_reason 可查询实际使用的后端。

    :param query: 用户查询文本
    :param documents: 候选文档文本列表
    :return: 与 documents 等长的分数列表（分数越高越相关）
    """
    global _last_backend, _last_degrade_reason

    if not documents:
        _last_backend = "passthrough"
        _last_degrade_reason = "空文档列表"
        return []

    preferred = reranker_config.backend

    # ── 第一级：尝试首选后端 ──
    if preferred == "local":
        try:
            scores = _rerank_local(query, documents)
            _last_backend = "local"
            _last_degrade_reason = ""
            return scores
        except Exception as exc:
            reason = f"local 失败（{exc}），降级到 cloud"
            logger.warning("重排降级: %s", reason)
            _last_degrade_reason = reason
    elif preferred == "cloud":
        try:
            scores = _rerank_cloud(query, documents)
            _last_backend = "cloud"
            _last_degrade_reason = ""
            return scores
        except Exception as exc:
            reason = f"cloud 失败（{exc}），降级到 passthrough"
            logger.warning("重排降级: %s", reason)
            _last_degrade_reason = reason
            # cloud 为首选时，降级直接到 passthrough（不再尝试 local）
            _last_backend = "passthrough"
            return _rerank_passthrough(documents)
    else:
        logger.warning("未知的 RERANK_BACKEND=%s，降级到 passthrough", preferred)
        _last_backend = "passthrough"
        _last_degrade_reason = f"未知 backend 配置: {preferred}"
        return _rerank_passthrough(documents)

    # ── 第二级：local 失败后降级到 cloud ──
    try:
        scores = _rerank_cloud(query, documents)
        _last_backend = "cloud"
        return scores
    except Exception as exc:
        reason = f"cloud 也失败（{exc}），降级到 passthrough"
        logger.warning("重排降级: %s", reason)
        _last_degrade_reason = reason

    # ── 第三级：兜底，不重排 ──
    _last_backend = "passthrough"
    return _rerank_passthrough(documents)


def get_last_rerank_status() -> dict:
    """
    查询最近一次 rerank_documents() 调用的实际后端与降级信息。
    用于调试、日志记录与测试断言。
    :return: {"backend": str, "degrade_reason": str}
    """
    return {
        "backend": _last_backend,
        "degrade_reason": _last_degrade_reason,
    }


def reset_local_reranker() -> None:
    """
    重置本地重排模型单例（主要用于测试场景：模拟模型路径变更 / 依赖缺失）。
    生产环境不应调用此函数。
    """
    global _local_reranker, _local_reranker_load_error
    _local_reranker = None
    _local_reranker_load_error = None
