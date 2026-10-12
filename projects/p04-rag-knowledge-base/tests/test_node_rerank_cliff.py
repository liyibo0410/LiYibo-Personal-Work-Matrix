# tests/test_node_rerank_cliff.py

"""
断崖截断集成测试 —— 用真实 BGE-reranker-large 分数验证 _step_3_cliff_cutoff。

缺陷类型学（D5-01 修复前的问题）：
  ① 只测降级路径（passthrough），不测真实模型路径
  ② sigmoid 归一化缺失导致断崖阈值（0.5 / 0.25）在 logits 空间失效
  ③ score_span 无 epsilon 保护，等分场景除零产生 NaN
  ④ 全相关文档被误砍到 RERANK_MIN_TOPK 下限

运行方式：
    cd projects/p04-rag-knowledge-base
    python -m pytest tests/test_node_rerank_cliff.py -v -s
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _build_ranked_docs(docs: list[str], scores: list[float]) -> list[dict]:
    """将文档和分数组装成降序排列的 ranked_docs（模拟 _step_2 输出）。"""
    scored = [
        {"content": doc, "score": score, "source": "local"}
        for doc, score in zip(docs, scores)
    ]
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def _print_score_profile(ranked_docs: list[dict]) -> None:
    """打印分数分布摘要，便于诊断。"""
    scores = [d["score"] for d in ranked_docs]
    print(f"\n  分数（降序）: {[f'{s:.4f}' for s in scores]}")
    print(f"  span = {max(scores) - min(scores):.4f}")
    for i in range(len(scores) - 1):
        gap = scores[i] - scores[i + 1]
        span = max(scores) - min(scores) + 1e-6
        print(
            f"  gap[{i}→{i+1}] abs={gap:.4f}  rel={gap / span:.4f}"
            f"  {'← TRIGGER' if gap >= 0.5 or gap / span >= 0.25 else ''}"
        )


# ══════════════════════════════════════════════════════════
# a) 全相关文档不应被过度截断
# ══════════════════════════════════════════════════════════
@pytest.mark.needs_model
class TestCliffAllRelated:
    """
    回归基线：6 条全部语义相关的文档，断崖检测后不应被砍到 RERANK_MIN_TOPK=3。

    旧实现缺陷：BGE logits 未经 sigmoid（如 -1.2 ~ +3.5），score_span 在 logits
    空间计算，rel_gap 分母过大导致所有相对差距都低于 0.25 阈值；同时绝对差距
    在 logits 空间也不到 0.5。结果：要么完全不砍（保留全部），要么因阈值错位
    在随机位置截断。实测「6 条全相关 → 只剩 3 条」即为旧实现的典型症状。

    新实现：sigmoid 将 logits 压缩到 [0,1]，score_span + 1e-6 保护等分边界，
    全相关文档间 gap 极小，不会触发任何阈值 → 保留全部 6 条。
    """

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_all_related_not_over_truncated(self):
        from utils.reranker_http_utils import _rerank_local
        from processor.query_processor.nodes.node_rerank import NodeRerank

        query = "hak 180 烫金机安全操作规范"
        docs = [
            "烫金机操作前必须检查设备接地是否可靠，防止漏电事故。",
            "使用烫金机时应佩戴防护手套，避免高温烫伤。",
            "烫金机工作时严禁将手伸入加热区域，防止严重烫伤。",
            "设备维护前必须断开电源，等待加热元件完全冷却后再操作。",
            "烫金机应放置在通风干燥的环境中，远离易燃易爆物品。",
            "操作烫金机前需阅读产品安全手册，了解应急处置方法。",
        ]

        # ── 真实 BGE 打分（内部已做 sigmoid 归一到 [0,1]） ──
        scores = _rerank_local(query, docs)
        ranked_docs = _build_ranked_docs(docs, scores)

        _print_score_profile(ranked_docs)

        # 前置校验：sigmoid 确实在 [0,1] 内（若此处失败说明 sigmoid 缺失）
        assert all(0.0 <= s <= 1.0 for s in scores), (
            f"sigmoid 归一后分数超出 [0,1]: {scores}。"
            f"原因：_rerank_local 缺少 sigmoid 步骤，断崖阈值在 logits 空间失效"
        )

        # ── 调用真实 _step_3_cliff_cutoff ──
        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        print(f"  断崖后保留: {len(result)} / {len(ranked_docs)} 条")

        # 核心断言：6 条全相关 → 至少保留 5 条（允许砍 1 条，但绝不能砍到下限 3）
        assert len(result) >= 5, (
            f"6 条全部语义相关，断崖后仅保留 {len(result)} 条。"
            f"旧实现缺陷：sigmoid 缺失导致阈值在 logits 空间错位，"
            f"全相关文档被误砍到 RERANK_MIN_TOPK=3 下限。"
            f"分数={scores}"
        )


# ══════════════════════════════════════════════════════════
# b) 原始 logits 经 sigmoid 后落在 [0, 1]
# ══════════════════════════════════════════════════════════
@pytest.mark.needs_model
class TestSigmoidNormalization:
    """
    验证 BGE reranker 的原始 logits 量纲（可达 -10 ~ +10）经 sigmoid 后映射到 [0,1]。

    旧实现缺陷：_rerank_local 直接返回 raw logits（如 -9.48 ~ +5.05），
    断崖阈值 RERANK_GAP_ABS=0.5 和 RERANK_GAP_RATIO=0.25 是为 [0,1] 设计的，
    在 logits 空间完全失效 —— abs_gap 动辄个位数，rel_gap 分母（score_span）
    被极端 logit 拉大到十几，正常差距都被稀释到阈值以下。

    新实现：_rerank_local 末尾执行 sigmoid = 1/(1+exp(-x))，
    将任意量纲的 logits 压缩到 (0,1)，使断崖阈值在统一尺度上生效。
    """

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_raw_logits_and_sigmoid_range(self):
        from utils.reranker_http_utils import _get_local_reranker, _rerank_local

        query = "电磁炉不加热故障排查步骤"
        docs = [
            "电磁炉不加热可能是 IGBT 管损坏，需要检查并更换。",
            "今天天气很好，适合出去散步放松心情。",
            "检查电磁炉保险丝是否熔断，谐振电容是否漏电。",
            "苹果发布新款手机，A 系列芯片性能提升 20%。",
            "电磁炉加热 intermittently 可能是温度传感器接触不良。",
        ]

        # ── 直接调用模型获取原始 logits（不经过 sigmoid） ──
        reranker = _get_local_reranker()
        assert reranker is not None, "BGE reranker 加载失败，无法获取原始 logits"

        pairs = [[query, doc] for doc in docs]
        raw_logits = reranker.compute_score(pairs)
        if isinstance(raw_logits, (int, float)):
            raw_logits = [float(raw_logits)]
        else:
            raw_logits = [float(s) for s in raw_logits]

        print(f"\n  原始 logits: {[f'{s:.4f}' for s in raw_logits]}")
        print(f"  logits 范围: [{min(raw_logits):.2f}, {max(raw_logits):.2f}]")

        # 验证原始 logits 确实超出 [0,1]（证明 sigmoid 是必要的）
        assert min(raw_logits) < 0 or max(raw_logits) > 1, (
            f"原始 logits 已在 [0,1] 内: {raw_logits}，"
            f"无法验证 sigmoid 的必要性（BGE 通常输出 -10~+10 的 logits）"
        )

        # ── 手动 sigmoid 并验证范围 ──
        sigmoid_scores = [1.0 / (1.0 + math.exp(-s)) for s in raw_logits]
        print(f"  sigmoid 后:  {[f'{s:.4f}' for s in sigmoid_scores]}")

        assert all(0.0 < s < 1.0 for s in sigmoid_scores), (
            f"sigmoid 后分数超出 (0,1): {sigmoid_scores}。"
            f"旧实现直接使用 raw logits，断崖阈值在错误量纲上生效"
        )

        # ── 验证 _rerank_local 的返回值与手动 sigmoid 一致 ──
        normalized = _rerank_local(query, docs)
        for i, (expected, actual) in enumerate(zip(sigmoid_scores, normalized)):
            assert abs(expected - actual) < 1e-6, (
                f"doc[{i}] sigmoid 不一致: 手动={expected:.6f}, "
                f"_rerank_local={actual:.6f}。"
                f"原因：_rerank_local 可能未执行 sigmoid 归一化"
            )

        print("  [OK] _rerank_local 返回的分数与手动 sigmoid 一致，归一化生效")


# ══════════════════════════════════════════════════════════
# c) 真断崖存在时确实触发截断
# ══════════════════════════════════════════════════════════
@pytest.mark.needs_model
class TestCliffTriggersTruncation:
    """
    存在明显语义断层时，断崖检测必须截断（不能完全不砍）。

    旧实现缺陷：有两个相反的问题 ——
    (1) 无 sigmoid 时，logits 空间 abs_gap 动辄 >0.5，几乎所有位置都触发，
        导致在 lower_bound 位置就截断（等效于砍到 MIN_TOPK）；
    (2) 有 sigmoid 但阈值设计不当时，可能全不触发，保留全部 10 条。

    新实现：sigmoid 归一 + score_span 相对化，使阈值在统一尺度上生效，
    真断崖位置（相关→不相关边界）精确触发，保留相关部分、砍掉不相关部分。
    """

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_real_cliff_triggers_truncation(self):
        from utils.reranker_http_utils import _rerank_local
        from processor.query_processor.nodes.node_rerank import NodeRerank

        query = "笔记本电脑电池耗电过快怎么办"
        docs = [
            # 高度相关（3 条）
            "笔记本电池耗电快可能是电池老化，建议检查电池健康度和循环次数。",
            "关闭后台不必要的应用程序可以降低电池消耗，延长续航时间。",
            "在电源管理中降低屏幕亮度、关闭蓝牙 WiFi 可显著减少耗电。",
            # 完全不相关（7 条）
            "红烧肉的做法：五花肉切块焯水，冰糖炒色后加酱油慢炖两小时。",
            "今天北京天气晴朗，最高气温 28 度，适合户外活动。",
            "唐朝第二位皇帝李世民发动玄武门之变，夺取了皇位。",
            "篮球比赛每队上场五名球员，分为控球后卫、得分后卫等位置。",
            "学习吉他需要坚持练习，初学者建议每天至少练半小时。",
            "海南三亚是热门旅游目的地，亚龙湾和天涯海角是必去景点。",
            "新款运动鞋采用轻量化设计，适合长跑和日常穿搭。",
        ]

        # ── 真实 BGE 打分 ──
        scores = _rerank_local(query, docs)
        ranked_docs = _build_ranked_docs(docs, scores)

        _print_score_profile(ranked_docs)

        # 前置校验：确认真实分数存在明显断层
        sorted_scores = [d["score"] for d in ranked_docs]
        max_gap = 0.0
        max_gap_pos = -1
        for i in range(len(sorted_scores) - 1):
            gap = sorted_scores[i] - sorted_scores[i + 1]
            if gap > max_gap:
                max_gap = gap
                max_gap_pos = i
        span = max(sorted_scores) - min(sorted_scores) + 1e-6
        max_rel_gap = max_gap / span

        print(f"  最大 gap: 位置 {max_gap_pos}→{max_gap_pos+1}, "
              f"abs={max_gap:.4f}, rel={max_rel_gap:.4f}")

        # 前置断言：BGE 确实产生了可检测的断层
        # （如果此断言失败，说明 BGE 对所有文档打分过于接近，需更换测试文档）
        cliff_detected_by_threshold = max_gap >= 0.5 or max_rel_gap >= 0.25
        assert cliff_detected_by_threshold, (
            f"BGE 未产生可检测的语义断层: max_abs_gap={max_gap:.4f} (<0.5), "
            f"max_rel_gap={max_rel_gap:.4f} (<0.25)。"
            f"请更换语义差异更大的测试文档。"
        )

        # ── 调用断崖检测 ──
        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        print(f"  断崖后保留: {len(result)} / {len(ranked_docs)} 条")

        # 核心断言：确实触发了截断，没有保留全部
        assert len(result) < len(ranked_docs), (
            f"存在明显语义断层（max_abs_gap={max_gap:.4f}, "
            f"max_rel_gap={max_rel_gap:.4f}），但断崖检测未截断，"
            f"保留了全部 {len(ranked_docs)} 条。"
            f"原因：断崖检测逻辑可能未正确实现阈值比较"
        )

        # 附加断言：截断位置应在相关文档范围内（3 条左右，允许 ±1）
        assert len(result) <= 5, (
            f"截断保留了 {len(result)} 条，远超相关文档数（3 条）。"
            f"断崖检测可能在错误位置截断"
        )
        assert len(result) >= 2, (
            f"截断仅保留 {len(result)} 条，少于相关文档数（3 条）。"
            f"断崖检测可能砍掉了相关文档"
        )


# ══════════════════════════════════════════════════════════
# d) 等分边界：score_span → 1e-6，不产生除零 / NaN
# ══════════════════════════════════════════════════════════
@pytest.mark.needs_model
class TestCliffEqualScoresBoundary:
    """
    所有分数相等时 score_span = max - min + 1e-6 = 1e-6，
    验证 rel_gap = abs_gap / 1e-6 不产生 Inf / NaN，不抛异常。

    旧实现缺陷：score_span = max - min（无 epsilon），等分时 = 0，
    rel_gap = 0 / 0 → NaN，NaN >= 0.25 为 False → 不截断（碰巧正确），
    但 NaN 传播到日志和下游，污染调试信息。某些 Python/NumPy 版本下
    0/0 可能直接抛 ZeroDivisionError 或 RuntimeWarning。

    新实现：score_span = max - min + 1e-6，等分时 span = 1e-6，
    rel_gap = 0 / 1e-6 = 0.0，干净无 NaN。
    """

    def setup_method(self):
        from utils.reranker_http_utils import reset_local_reranker
        reset_local_reranker()

    def test_equal_scores_no_nan_no_crash(self):
        from processor.query_processor.nodes.node_rerank import (
            NodeRerank,
            RERANK_MAX_TOPK,
        )

        # ── 构造等分 ranked_docs（直接构造，因 BGE 不可能产出完全相等的分数） ──
        n = 8
        equal_score = 0.7333
        ranked_docs = [
            {"content": f"文档 {i}", "score": equal_score, "source": "local"}
            for i in range(n)
        ]

        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        # 不抛异常即通过第一关
        assert result is not None, "_step_3_cliff_cutoff 返回 None"
        assert len(result) > 0, "等分场景返回空列表"

        # 所有分数相等 → 无任何 gap → 不应触发截断 → 保留全部
        assert len(result) == min(n, RERANK_MAX_TOPK), (
            f"等分场景应保留全部 {min(n, RERANK_MAX_TOPK)} 条，"
            f"实际保留 {len(result)} 条。"
            f"原因：score_span epsilon 保护可能缺失，0/0 产生 NaN 导致异常截断"
        )

        # 验证结果中无 NaN / Inf
        for i, doc in enumerate(result):
            score = doc["score"]
            assert not math.isnan(score), (
                f"结果 [{i}] score=NaN。原因：score_span=0 导致除零，"
                f"NaN 传播到输出。新实现通过 +1e-6 避免分母为零"
            )
            assert not math.isinf(score), (
                f"结果 [{i}] score=Inf。原因同上"
            )

        print(f"\n  等分场景（score={equal_score}×{n}）: "
              f"保留 {len(result)} 条，无 NaN/Inf [OK]")

    def test_near_equal_scores_small_span(self):
        """
        近似等分（span ≈ 0.001）：验证极小但非零的 span 不导致 rel_gap 爆炸。

        旧实现：span=0.001 时，abs_gap=0.001 → rel_gap=0.001/0.001=1.0 ≥ 0.25，
        每个位置都触发截断 → 砍到 MIN_TOPK=3。

        新实现：同样的数学结果（rel_gap 确实 ≥ 0.25），但此时 abs_gap 极小（0.001），
        远低于 RERANK_GAP_ABS=0.5，只有 rel_gap 触发。
        这是正确行为 —— 分数差异极小时在 MIN_TOPK 处截断是合理的。
        """
        from processor.query_processor.nodes.node_rerank import (
            NodeRerank,
            RERANK_MIN_TOPK,
        )

        n = 8
        ranked_docs = [
            {"content": f"文档 {i}", "score": 0.8 - 0.001 * i, "source": "local"}
            for i in range(n)
        ]

        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        assert result is not None
        for doc in result:
            assert not math.isnan(doc["score"])
            assert not math.isinf(doc["score"])

        # 近似等分 → rel_gap ≈ 1.0 → 在 lower_bound 处截断 → 保留 MIN_TOPK 条
        assert len(result) >= RERANK_MIN_TOPK, (
            f"近似等分场景保留 {len(result)} 条，低于 MIN_TOPK={RERANK_MIN_TOPK}"
        )

        print(f"\n  近似等分场景（span=0.007）: 保留 {len(result)} 条，无 NaN/Inf [OK]")

    def test_two_docs_equal_scores(self):
        """
        仅 2 条文档且分数相等：upper_bound=2, lower_bound=min(3,2)=2，
        遍历范围 range(1, 1) 为空 → 不检测 → 保留全部 2 条。
        """
        from processor.query_processor.nodes.node_rerank import NodeRerank

        ranked_docs = [
            {"content": "A", "score": 0.5, "source": "local"},
            {"content": "B", "score": 0.5, "source": "local"},
        ]

        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        assert len(result) == 2, (
            f"2 条等分文档应保留 2 条，实际 {len(result)} 条"
        )
        for doc in result:
            assert not math.isnan(doc["score"])

    def test_all_none_scores(self):
        """所有 score=None（rerank 失败的兜底场景）：不应崩溃。"""
        from processor.query_processor.nodes.node_rerank import NodeRerank

        ranked_docs = [
            {"content": f"文档 {i}", "score": None, "source": "local"}
            for i in range(5)
        ]

        node = NodeRerank()
        result = node._step_3_cliff_cutoff(ranked_docs)

        assert len(result) == 5, (
            f"全 None 分数应保留全部 5 条（无 gap 可检测），实际 {len(result)} 条"
        )
