# clarify/responder.py 的规则话术测试（build_clarify_message 是纯规则，不调用 LLM）
# 注意：导入 clarify.responder 会触发 infrastructure.llm 在 import 时构造 LLM 客户端
# （依赖 .env 完整）。若环境缺配置导致导入失败，则跳过本文件而非判失败。

import pytest

try:
    from clarify.responder import ClarifyResponder
    from plan.models import ClarifyReason
    from domain.messages import FocusedObject
    from domain.state import DialogueState
except Exception as exc:  # .env 缺项 / langchain 构造失败
    pytest.skip(f"clarify.responder 导入失败（依赖 .env / LLM 客户端）: {exc}", allow_module_level=True)


@pytest.fixture
def responder():
    return ClarifyResponder()


@pytest.fixture
def empty_state():
    return DialogueState(sender_id="user_001")


@pytest.fixture
def order_state():
    return DialogueState(
        sender_id="user_001",
        focused_object=FocusedObject(id="ORDER_1", type="order", title="订单1"),
    )


@pytest.fixture
def product_state():
    return DialogueState(
        sender_id="user_001",
        focused_object=FocusedObject(id="SKU_1", type="product", title="纯棉T恤"),
    )


def test_multiple_tracks(responder, empty_state):
    msg = responder.build_clarify_message(ClarifyReason.MULTIPLE_TRACKS, empty_state)
    assert "先办业务还是先咨询" in msg


def test_missing_focused_object(responder, empty_state):
    msg = responder.build_clarify_message(ClarifyReason.MISSING_FOCUSED_OBJECT, empty_state)
    assert "发送你想咨询的对象" in msg


def test_missing_knowledge_intent(responder, empty_state):
    msg = responder.build_clarify_message(ClarifyReason.MISSING_KNOWLEDGE_INTENT, empty_state)
    assert "商品信息" in msg and "订单信息" in msg


def test_missing_track(responder, empty_state):
    msg = responder.build_clarify_message(ClarifyReason.MISSING_TRACK, empty_state)
    assert "业务" in msg and "咨询" in msg


def test_missing_task_commands(responder, empty_state):
    msg = responder.build_clarify_message(ClarifyReason.MISSING_TASK_COMMANDS, empty_state)
    assert "查订单" in msg or "退款" in msg


def test_object_requires_intent_order(responder, order_state):
    msg = responder.build_clarify_message(ClarifyReason.OBJECT_REQUIRES_INTENT, order_state)
    assert "订单" in msg


def test_object_requires_intent_product(responder, product_state):
    msg = responder.build_clarify_message(ClarifyReason.OBJECT_REQUIRES_INTENT, product_state)
    assert "商品" in msg


def test_object_requires_intent_no_object_fallback(responder, empty_state):
    # 有 OBJECT_REQUIRES_INTENT 原因但无聚焦对象 -> 落到兜底话术
    msg = responder.build_clarify_message(ClarifyReason.OBJECT_REQUIRES_INTENT, empty_state)
    assert "再确认一下" in msg


def test_unknown_reason_fallback(responder, empty_state):
    msg = responder.build_clarify_message(ClarifyReason.UNKNOWN_TASK_FLOW, empty_state)
    assert "再确认一下" in msg


def test_all_reasons_produce_nonempty_text(responder, empty_state):
    # 任何原因码都必须给出一句非空兜底话术（永远有话可说）
    for reason in ClarifyReason:
        msg = responder.build_clarify_message(reason, empty_state)
        assert isinstance(msg, str) and msg.strip()
