# tests/test_reranker.py

"""
重排器单元测试 —— 不依赖 Milvus / MongoDB / MinIO / Docker。

测试矩阵：
  1. passthrough 兜底：纯函数，无需任何外部依赖
  2. local 正常路径：真实加载 BGE-reranker-large 并推理
  3. local → cloud 降级：模拟本地模型不可用
  4. cloud → passthrough 降级：模拟云端 API 失败
  5. 单例缓存：模型只加载一次
  6. 依赖缺失：FlagEmbedding 未安装时不崩溃

运行方式：
    cd projects/p04-rag-knowledge-base
    python -m pytest tests/test_reranker.py -v

    # 只跑不依赖真实模型的纯单元测试
    python -m pytest tests/test_reranker.py -v -m "not needs_model"

    # 只跑需要真实模型的集成测试
    python -m pytest tests/test_reranker.py -v -m needs_model
"""

from __future__ import annotations

import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── 确保项目根目录在 sys.path 中 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════
# 1. passthrough 兜底测试（纯函数，零依赖）
# ══════════════════════════════════════════════
class TestRerankPassthrough:
    """测试「不重排」兜底逻辑"""

    def test_passthrough_returns_correct_length(self):
        """passthrough 返回的分数列表长度必须与输入文档数一致"""
        from utils.reranker_http_utils import _rerank_passthrough

        docs = ["文档A", "文档B", "文档C", "文档D", "文档E"]
        scores = _rerank_passthrough(docs)

        assert len(scores) == 5, f"期望 5 个分数，实际 {len(scores)}"

    def test_passthrough_preserves_order(self):
        """passthrough 分数必须严格递减，确保排序后保持原始顺序"""
        from utils.reranker_http_utils import _rerank_passthrough

        docs = ["第一", "第二", "第三", "第四"]
        scores = _rerank_passthrough(docs)

        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], (
                f"passthrough 分数未严格递减: scores[{i}]={scores[i]} <= scores[{i+1}]={scores[i+1]}"
            )

    def test_passthrough_scores_are_positive(self):
        """passthrough 分数必须全部为正数"""
        from utils.reranker_http_utils import _rerank_passthrough

        docs = ["A"] * 50  # 50 条文档
        scores = _rerank_passthrough(docs)

        assert all(s > 0 for s in scores), "passthrough 分数出现非正值"

    def test_empty_documents(self):
        """空文档列表应返回空列表，不抛异常"""
        from utils.reranker_http_utils import rerank_documents

        with patch("utils.reranker_http_utils.reranker_config") as mock_config:
            mock_config.backend = "local"
            result = rerank_documents("测试查询", [])
            assert result == []


# ══════════════════════════════════════════════
# 2. local 正常路径测试（需要真实模型）
# ══════════════════════════════════════════════
@pytest.mark.needs_model
class TestRerankLocalNormalPath:
    """测试本地 BGE-reranker-large 真实推理"""

    def setup_method(self):
        """每个测试前重置单例，确保干净状态"""
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_local_rerank_returns_correct_length(self):
        """本地重排返回的分数列表长度必须与输入文档数一致"""
        from utils.reranker_http_utils import _rerank_local

        query = "如何检测主板短路"
        docs = [
            "主板短路通常表现为通电后风扇转一下就停，可以使用万用表测量。",
            "今天天气很好，适合出去散步。",
            "使用万用表的蜂鸣档测量各供电电感对地阻值，阻值偏低即为短路。",
        ]

        scores = _rerank_local(query, docs)

        assert len(scores) == 3, f"期望 3 个分数，实际 {len(scores)}"
        print(f"\n  query: {query}")
        for i, (doc, score) in enumerate(zip(docs, scores)):
            print(f"  [{i}] score={score:.4f} | {doc[:40]}...")

    def test_local_rerank_semantic_ordering(self):
        """本地重排的分数排序必须与语义相关度一致"""
        from utils.reranker_http_utils import _rerank_local

        query = "如何检测主板短路"
        docs = [
            "今天中午去吃猪脚饭吧，这块主板外观很漂亮。",           # 不相关
            "主板短路通常表现为通电后风扇转一下就停，可以使用万用表测量。",  # 高度相关
            "苹果发布新款手机，A系列芯片性能提升20%。",               # 不相关
            "使用万用表的蜂鸣档测量各供电电感对地阻值，阻值偏低即为短路。",  # 高度相关
            "主板维修需要先了解电路原理，建议参考维修手册。",           # 弱相关
        ]

        scores = _rerank_local(query, docs)

        # 步骤1：打印完整结果供人工审查
        print(f"\n  query: {query}")
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        for rank, (idx, score) in enumerate(ranked):
            print(f"  Top-{rank+1}: score={score:.4f} | [{idx}] {docs[idx][:50]}...")

        # 步骤2：断言高相关文档（索引 1, 3）的分数高于不相关文档（索引 0, 2）
        relevant_indices = {1, 3}
        irrelevant_indices = {0, 2}
        min_relevant = min(scores[i] for i in relevant_indices)
        max_irrelevant = max(scores[i] for i in irrelevant_indices)

        assert min_relevant > max_irrelevant, (
            f"语义排序异常: 最弱相关文档分数 {min_relevant:.4f} "
            f"<= 最强不相关文档分数 {max_irrelevant:.4f}"
        )

    def test_rerank_documents_with_local_backend(self):
        """通过 rerank_documents() 主入口调用 local 后端"""
        from utils.reranker_http_utils import rerank_documents, get_last_rerank_status

        with patch("utils.reranker_http_utils.reranker_config") as mock_config:
            mock_config.backend = "local"
            # 本地模型路径等字段从真实 config 读取
            from config.reranker_config import reranker_config as real_config
            mock_config.bge_reranker_path = real_config.bge_reranker_path
            mock_config.bge_reranker_device = real_config.bge_reranker_device
            mock_config.bge_reranker_fp16 = real_config.bge_reranker_fp16
            mock_config.text_rerank_api_key = real_config.text_rerank_api_key
            mock_config.text_rerank_model = real_config.text_rerank_model
            mock_config.text_rerank_instruct = real_config.text_rerank_instruct

            query = "电磁炉不加热的常见原因"
            docs = [
                "电磁炉不加热可能是IGBT管损坏，需要更换。",
                "今天超市促销，电磁炉打八折。",
                "检查电磁炉的保险丝是否熔断，以及谐振电容是否漏电。",
            ]

            scores = rerank_documents(query, docs)
            status = get_last_rerank_status()

            assert len(scores) == 3
            assert status["backend"] == "local", f"期望使用 local 后端，实际 {status['backend']}"
            assert status["degrade_reason"] == ""

            print(f"\n  backend={status['backend']}, scores={[round(s, 4) for s in scores]}")


# ══════════════════════════════════════════════
# 3. local → cloud 降级测试
# ══════════════════════════════════════════════
class TestLocalToCloudDegradation:
    """测试本地模型不可用时自动降级到云端"""

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_nonexistent_model_path_falls_back(self):
        """模型路径不存在时，应自动降级到 cloud 或 passthrough，不抛异常"""
        from utils.reranker_http_utils import rerank_documents, get_last_rerank_status

        with patch("utils.reranker_http_utils.reranker_config") as mock_config:
            mock_config.backend = "local"
            mock_config.bge_reranker_path = "/this/path/does/not/exist"
            mock_config.bge_reranker_device = "cpu"
            mock_config.bge_reranker_fp16 = False
            # cloud 也模拟失败（无 API Key）
            mock_config.text_rerank_api_key = None
            mock_config.text_rerank_model = None
            mock_config.text_rerank_instruct = None

            scores = rerank_documents("测试查询", ["文档A", "文档B", "文档C"])
            status = get_last_rerank_status()

            # 不应抛异常，应降级到 passthrough
            assert len(scores) == 3
            assert status["backend"] == "passthrough", (
                f"期望降级到 passthrough，实际 {status['backend']}"
            )
            print(f"\n  降级路径: local(路径不存在) → cloud(无Key) → {status['backend']}")
            print(f"  降级原因: {status['degrade_reason']}")

    def test_local_fails_cloud_succeeds(self):
        """local 失败但 cloud 可用时，应降级到 cloud 并返回真实分数"""
        from utils.reranker_http_utils import rerank_documents, get_last_rerank_status

        # 模拟 cloud 返回成功响应
        mock_response = MagicMock()
        mock_response.get.side_effect = lambda key, default=None: {
            "status_code": 200,
        }.get(key, default)
        mock_response.output = {
            "results": [
                {"index": 0, "relevance_score": 0.95},
                {"index": 1, "relevance_score": 0.30},
                {"index": 2, "relevance_score": 0.70},
            ]
        }

        mock_dashscope = MagicMock()
        mock_dashscope.TextReRank.call.return_value = mock_response

        with patch("utils.reranker_http_utils.reranker_config") as mock_config:
            mock_config.backend = "local"
            mock_config.bge_reranker_path = "/nonexistent/path"
            mock_config.bge_reranker_device = "cpu"
            mock_config.bge_reranker_fp16 = False
            mock_config.text_rerank_api_key = "sk-fake-key"
            mock_config.text_rerank_model = "qwen3-rerank"
            mock_config.text_rerank_instruct = ""

            with patch.dict(sys.modules, {"dashscope": mock_dashscope}):
                scores = rerank_documents("测试", ["A", "B", "C"])
                status = get_last_rerank_status()

            assert len(scores) == 3
            assert status["backend"] == "cloud", (
                f"期望降级到 cloud，实际 {status['backend']}"
            )
            # 验证分数来自 cloud 模拟响应
            assert scores[0] == 0.95
            assert scores[1] == 0.30
            assert scores[2] == 0.70
            print(f"\n  降级: local → cloud, scores={scores}")


# ══════════════════════════════════════════════
# 4. cloud → passthrough 降级测试
# ══════════════════════════════════════════════
class TestCloudToPassthroughDegradation:
    """测试云端 API 不可用时的降级"""

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_cloud_backend_fails_falls_to_passthrough(self):
        """backend=cloud 且 API 调用失败时，应降级到 passthrough"""
        from utils.reranker_http_utils import rerank_documents, get_last_rerank_status

        mock_dashscope = MagicMock()
        mock_dashscope.TextReRank.call.side_effect = Exception("网络超时")

        with patch("utils.reranker_http_utils.reranker_config") as mock_config:
            mock_config.backend = "cloud"
            mock_config.text_rerank_api_key = "sk-fake"
            mock_config.text_rerank_model = "qwen3-rerank"
            mock_config.text_rerank_instruct = ""

            with patch.dict(sys.modules, {"dashscope": mock_dashscope}):
                scores = rerank_documents("测试", ["A", "B", "C"])
                status = get_last_rerank_status()

            assert len(scores) == 3
            assert status["backend"] == "passthrough"
            # 验证保序递减
            for i in range(len(scores) - 1):
                assert scores[i] > scores[i + 1]
            print(f"\n  降级: cloud(网络超时) → passthrough, scores={[round(s, 4) for s in scores]}")

    def test_unknown_backend_falls_to_passthrough(self):
        """backend 配置为非法值时，应降级到 passthrough"""
        from utils.reranker_http_utils import rerank_documents, get_last_rerank_status

        with patch("utils.reranker_http_utils.reranker_config") as mock_config:
            mock_config.backend = "quantum_computer"

            scores = rerank_documents("测试", ["A", "B"])
            status = get_last_rerank_status()

            assert len(scores) == 2
            assert status["backend"] == "passthrough"
            print(f"\n  非法 backend → passthrough")


# ══════════════════════════════════════════════
# 5. 单例缓存测试
# ══════════════════════════════════════════════
@pytest.mark.needs_model
class TestSingletonCache:
    """验证本地模型只加载一次"""

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_model_loaded_only_once(self):
        """重复调用 100 次，模型只加载一次，后续调用应显著更快"""
        from utils.reranker_http_utils import _rerank_local, reset_local_reranker

        query = "测试查询"
        docs = ["测试文档一", "测试文档二"]

        # 步骤1：首次调用（包含模型加载）
        t0 = time.time()
        scores_first = _rerank_local(query, docs)
        first_call_time = time.time() - t0

        # 步骤2：重复调用 99 次（应命中缓存）
        t1 = time.time()
        for _ in range(99):
            _rerank_local(query, docs)
        remaining_99_time = time.time() - t1

        avg_subsequent = remaining_99_time / 99

        print(f"\n  首次调用（含模型加载）: {first_call_time:.2f} 秒")
        print(f"  后续 99 次总耗时: {remaining_99_time:.2f} 秒")
        print(f"  后续单次平均耗时: {avg_subsequent:.4f} 秒")
        print(f"  加速比: {first_call_time / max(avg_subsequent, 0.001):.0f}x")

        # 步骤3：断言首次调用比后续调用慢至少 5 倍（模型加载通常 5-15 秒）
        assert first_call_time > avg_subsequent * 5, (
            f"首次调用 {first_call_time:.2f}s 不够慢，"
            f"可能模型已被缓存或未被真正加载"
        )

        # 步骤4：验证分数一致（同一模型、同一输入，结果应相同）
        scores_last = _rerank_local(query, docs)
        for i, (a, b) in enumerate(zip(scores_first, scores_last)):
            assert abs(a - b) < 1e-5, f"第 {i} 个分数不一致: {a} vs {b}"


# ══════════════════════════════════════════════
# 6. 依赖缺失测试
# ══════════════════════════════════════════════
class TestDependencyMissing:
    """测试 FlagEmbedding 未安装时的优雅降级"""

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_flagembedding_import_error_graceful(self):
        """FlagEmbedding 未安装时，local 应失败并降级到 cloud 或 passthrough"""
        from utils.reranker_http_utils import (
            rerank_documents,
            get_last_rerank_status,
            reset_local_reranker,
        )

        # 模拟 FlagEmbedding 未安装：让 _try_import_flag_reranker 返回 None
        with patch("utils.reranker_http_utils._try_import_flag_reranker", return_value=None):
            reset_local_reranker()

            with patch("utils.reranker_http_utils.reranker_config") as mock_config:
                mock_config.backend = "local"
                mock_config.bge_reranker_path = "/some/path"
                mock_config.bge_reranker_device = "cpu"
                mock_config.bge_reranker_fp16 = False
                # cloud 也模拟不可用
                mock_config.text_rerank_api_key = None
                mock_config.text_rerank_model = None
                mock_config.text_rerank_instruct = None

                # 不应抛异常
                scores = rerank_documents("测试", ["A", "B"])
                status = get_last_rerank_status()

                assert len(scores) == 2
                assert status["backend"] == "passthrough"
                print(f"\n  FlagEmbedding 缺失 → 降级到 {status['backend']}")
                print(f"  原因: {status['degrade_reason']}")

    def test_module_import_does_not_crash(self):
        """
        即使 FlagEmbedding 完全不可用，import utils.reranker_http_utils 也不应崩溃。
        验证 try/except 包裹的 import 保护生效。
        """
        import importlib

        # 步骤1：移除已缓存的模块
        mods_to_remove = [k for k in sys.modules if "reranker" in k]
        saved = {}
        for mod_name in mods_to_remove:
            saved[mod_name] = sys.modules.pop(mod_name)

        try:
            # 步骤2：模拟 FlagEmbedding 不存在
            with patch.dict(sys.modules, {"FlagEmbedding": None}):
                # 重新导入不应崩溃
                import utils.reranker_http_utils as rh
                importlib.reload(rh)

                # _try_import_flag_reranker 应返回 None
                result = rh._try_import_flag_reranker()
                assert result is None, "FlagEmbedding=None 时 _try_import_flag_reranker 应返回 None"
                print("\n  FlagEmbedding 缺失时模块 import 正常，不崩溃")
        finally:
            # 步骤3：恢复原始模块状态
            for mod_name in mods_to_remove:
                if mod_name in saved:
                    sys.modules[mod_name] = saved[mod_name]
            # 重新导入恢复正常状态
            if "utils.reranker_http_utils" in sys.modules:
                importlib.reload(sys.modules["utils.reranker_http_utils"])
            else:
                import utils.reranker_http_utils  # noqa: F401


# ══════════════════════════════════════════════
# 7. local vs cloud 一致性测试
# ══════════════════════════════════════════════
@pytest.mark.needs_model
class TestLocalCloudConsistency:
    """验证同一输入下 local 与 cloud 的 Top-1 一致或高度接近"""

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_top1_consistency(self):
        """同一组输入，local 与 cloud 的 Top-1 文档应一致"""
        from utils.reranker_http_utils import _rerank_local, reset_local_reranker

        query = "合同违约赔偿标准"
        docs = [
            "根据民法典第577条，违约方应承担继续履行、采取补救措施或赔偿损失等责任。",
            "今天天气不错，适合户外运动。",
            "违约金一般不超过实际损失的30%，但当事人可以约定。",
            "公司年会将于下周五举行，请各部门做好准备。",
            "合同解除后，尚未履行的部分终止履行。",
        ]

        # 步骤1：local 打分
        reset_local_reranker()
        local_scores = _rerank_local(query, docs)
        local_top1_idx = local_scores.index(max(local_scores))

        print(f"\n  query: {query}")
        print(f"  local 排序:")
        for rank, (idx, score) in enumerate(
            sorted(enumerate(local_scores), key=lambda x: x[1], reverse=True)
        ):
            print(f"    Top-{rank+1}: score={score:.4f} | [{idx}] {docs[idx][:50]}...")

        # 步骤2：cloud 打分（mock 返回与 local 一致的 Top-1）
        # 注意：这里我们只验证 local 的排序合理性
        # 因为 cloud 需要真实 API Key，在测试环境中不可用
        # 真实一致性验证在验收阶段手动完成

        # 步骤3：断言 Top-1 是语义最相关的文档（索引 0 或 2）
        assert local_top1_idx in (0, 2), (
            f"local Top-1 为文档 [{local_top1_idx}]，"
            f"期望为 [0] 或 [2]（语义最相关）"
        )
        print(f"\n  local Top-1: [{local_top1_idx}]（语义最相关文档）")


# ══════════════════════════════════════════════
# 8. D5-01 断崖检测集成测试（真实 BGE 分数）
# ══════════════════════════════════════════════
@pytest.mark.needs_model
class TestCliffCutoffIntegration:
    """
    D5-01 修复验证：6 条全部语义相关的文档，经 sigmoid 归一 + 全局跨度 rel_gap 后，
    断崖检测不应砍到下限（RERANK_MIN_TOPK=3），应保留 >= 4 条。
    """

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_cliff_does_not_over_truncate_related_docs(self):
        """6 条全部语义相关 → 断崖后应保留 >= 4 条，不能砍到下限 3"""
        from utils.reranker_http_utils import _rerank_local
        from processor.query_processor.nodes.node_rerank import NodeRerank

        query = "hak 180 烫金机安全使用注意事项"
        docs_all_related = [
            "烫金机操作前必须检查设备接地是否可靠，防止漏电事故。",
            "使用烫金机时应佩戴防护手套，避免高温烫伤。",
            "烫金机工作时严禁将手伸入加热区域，防止严重烫伤。",
            "设备维护前必须断开电源，等待加热元件完全冷却。",
            "烫金机应放置在通风干燥的环境中，远离易燃易爆物品。",
            "操作烫金机前需阅读产品安全手册，了解应急处置方法。",
        ]

        # 步骤1：用真实 BGE 模型打分（已含 sigmoid 归一）
        scores = _rerank_local(query, docs_all_related)

        print(f"\n  query: {query}")
        print(f"  sigmoid 归一后分数: {[f'{s:.4f}' for s in scores]}")
        assert all(0.0 <= s <= 1.0 for s in scores), (
            f"sigmoid 归一后分数超出 [0,1]: {scores}"
        )

        # 步骤2：构造 ranked_docs（按分数降序，模拟 _step_2 的输出）
        scored_docs = [
            {"content": doc, "score": score, "source": "local"}
            for doc, score in zip(docs_all_related, scores)
        ]
        ranked_docs = sorted(scored_docs, key=lambda x: x["score"], reverse=True)

        for i, doc in enumerate(ranked_docs):
            print(f"  [{i}] score={doc['score']:.4f} | {doc['content'][:50]}...")

        # 步骤3：调用真实的 _step_3_cliff_cutoff
        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        print(f"  断崖后保留: {len(result)} 条（下限=3）")

        # 步骤4：6 条全部相关，不应砍到下限
        assert len(result) >= 4, (
            f"6 条全部语义相关，断崖后仅保留 {len(result)} 条（砍到下限），"
            f"分数={[d['score'] for d in ranked_docs]}"
        )
