"""Unit tests for the P09 rule-based scoring engine.

The engine is the deterministic "mock LLM" scorer. These tests pin its
explainability contract: every dimension carries deduction_reasons/highlights,
forbidden words are recorded as violations, the overall score is the weighted
sum of dimensions, and scores stay clamped to [0, 100].
"""

from __future__ import annotations

from app.main import (
    Conversation,
    Message,
    _rule_based_score,
)

WEIGHTS = {
    "服务态度": 0.25,
    "专业度": 0.25,
    "需求挖掘": 0.15,
    "促成转化": 0.20,
    "合规性": 0.15,
}

# 违规词与话术关键词均为中文（质检规则的可判定特征），测试与 app.main 的词表保持一致。
FORBIDDEN_RUDE = "笨蛋"
FORBIDDEN_PUSH_OFF = "不关我的事"
FORBIDDEN_FALSE_PROMISE = "向您承诺"
FORBIDDEN_COMPETITOR = "别家更好"


def _conv(messages: list[tuple[str, str]], duration: int = 120) -> Conversation:
    msgs = [
        Message(role=role, content=content, timestamp=f"2025-03-15T10:{i:02d}:00")
        for i, (role, content) in enumerate(messages)
    ]
    return Conversation(
        id="t-1",
        agent_id="agent-001",
        agent_name="测试坐席",
        store="旗舰店 A",
        customer_name="赵女士",
        topic="测试会话",
        messages=msgs,
        duration_seconds=duration,
    )


def _dims(score):
    return {d.dimension: d for d in score.dimensions}


# ── Structure & explainability ───────────────────────────────────

def test_score_has_all_five_dimensions():
    score = _rule_based_score(_conv([("agent", "您好，请问有什么可以帮您的吗？"), ("customer", "你好")]))
    names = {d.dimension for d in score.dimensions}
    assert names == set(WEIGHTS.keys())


def test_overall_is_weighted_sum_of_dimensions():
    score = _rule_based_score(_conv([("agent", "您好！很高兴帮您处理。"), ("customer", "谢谢")]))
    expected = sum(d.score * WEIGHTS[d.dimension] for d in score.dimensions)
    assert score.overall == round(expected, 1)


def test_every_dimension_score_clamped():
    score = _rule_based_score(_conv([("agent", "随便，白痴。"), ("customer", "？！")]))
    for d in score.dimensions:
        assert 0 <= d.score <= 100
    assert 0 <= score.overall <= 100


def test_low_scoring_dimensions_produce_suggestions():
    score = _rule_based_score(_conv([("agent", "不关我的事，您自己处理。"), ("customer", "很生气")]))
    assert score.suggestions  # non-empty
    assert any("需重点改进" in s or "仍有提升空间" in s for s in score.suggestions)


# ── Forbidden words → violations + attitude drop ─────────────────

def test_forbidden_words_recorded_as_violations():
    score = _rule_based_score(
        _conv([("agent", f"你就是{FORBIDDEN_RUDE}，这事{FORBIDDEN_PUSH_OFF}。"), ("customer", "太意外了")])
    )
    violated_words = {v["word"] for v in score.rule_violations}
    assert FORBIDDEN_RUDE in violated_words
    assert FORBIDDEN_PUSH_OFF in violated_words
    attitude = _dims(score)["服务态度"]
    assert attitude.score < 80  # base attitude is 80 before penalties
    assert any("违规用语" in r for r in attitude.deduction_reasons)


def test_false_promise_drops_compliance():
    score = _rule_based_score(
        _conv([("agent", f"我{FORBIDDEN_FALSE_PROMISE}，物流一定能准时到。"), ("customer", "好的")])
    )
    compliance = _dims(score)["合规性"]
    assert compliance.score < 90  # base compliance is 90
    assert any("不实承诺" in r for r in compliance.deduction_reasons)


def test_competitor_mention_drops_compliance():
    score = _rule_based_score(
        _conv([("agent", f"说实话，这类商品{FORBIDDEN_COMPETITOR}。"), ("customer", "这样啊")])
    )
    compliance = _dims(score)["合规性"]
    assert compliance.score < 90
    assert any("竞品" in r for r in compliance.deduction_reasons)


# ── Positive signals → boosts + highlights ───────────────────────

def test_greeting_empathy_closing_boost_attitude():
    good = _rule_based_score(
        _conv([
            ("agent", "您好，欢迎进店！我很理解您的顾虑，很高兴帮您处理这个问题。"),
            ("customer", "谢谢"),
            ("agent", "感谢您的支持，祝您生活愉快！"),
        ])
    )
    attitude = _dims(good)["服务态度"]
    assert attitude.score >= 85
    assert attitude.highlights  # explainable positives
    assert not attitude.deduction_reasons


def test_upsell_attempt_boosts_conversion():
    with_upsell = _rule_based_score(
        _conv([("agent", "顺便说一下，我们刚上了新品，还有一套和您这次选购很搭配的组合装，您或许会感兴趣。")])
    )
    without_upsell = _rule_based_score(_conv([("agent", "以上就是您咨询的答案。")]))
    assert _dims(with_upsell)["促成转化"].score > _dims(without_upsell)["促成转化"].score


def test_multi_turn_engagement_boosts_demand_mining():
    multi = _rule_based_score(
        _conv([
            ("agent", "您好，请问有什么可以帮您？还有其他想了解的更多需求吗？"),
            ("customer", "问题一"),
            ("customer", "问题二"),
            ("customer", "问题三"),
        ])
    )
    single = _rule_based_score(_conv([("agent", "您好，还有其他问题吗？"), ("customer", "问题一")]))
    assert _dims(multi)["需求挖掘"].score > _dims(single)["需求挖掘"].score


def test_detailed_long_response_boosts_expertise():
    detail = "这款产品的成分、功效和使用顺序我都为您逐项说明，您可以放心选购。"
    detailed = _rule_based_score(
        _conv([("agent", "我这边先帮您核实一下订单详情。 " + detail * 4)], duration=120)
    )
    brief = _rule_based_score(_conv([("agent", "好的，已处理。")], duration=120))
    assert _dims(detailed)["专业度"].score > _dims(brief)["专业度"].score
