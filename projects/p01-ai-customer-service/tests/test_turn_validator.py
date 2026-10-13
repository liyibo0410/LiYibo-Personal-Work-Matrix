# plan/turn_validator.py 的测试：防幻觉安检门（验收门禁「幻觉/越界被拦截」的核心证据）
# 纯逻辑，不调用 LLM。把原 __main__ 的 13 个自测用例转成可回归的 pytest。

import pytest

from domain.messages import FocusedObject
from domain.state import DialogueState
from knowledge.intents import KNOWLEDGE_INTENTS
from plan.models import ClarifyReason, TaskTurnPlan, TurnPlan
from plan.turn_validator import TurnPlanValidator
from task.command.models import Command, StartFlowCommand
from task.flow.flows import Flow, FlowsList


@pytest.fixture
def validator():
    return TurnPlanValidator()


@pytest.fixture
def flow_list():
    # 必须含 refund_request，否则合法 start_flow 会被误判 UNKNOWN_TASK_FLOW
    return FlowsList(flows=[
        Flow(id="refund_request", name="退款申请", description="处理用户退款申请"),
        Flow(id="onboarding", name="欢迎引导", description="开场欢迎"),
        Flow(id="system_task_started", name="系统过场", description="内部流程"),
    ])


@pytest.fixture
def empty_state():
    return DialogueState(sender_id="user_001")


@pytest.fixture
def order_state():
    return DialogueState(
        sender_id="user_001",
        focused_object=FocusedObject(id="ORDER_10001", type="order", title="订单10001"),
    )


def _validate(validator, state, plan, flow_list):
    return validator.validate(state, plan, flow_list, KNOWLEDGE_INTENTS)


# ---------- 轨道数量判定 ----------

def test_no_track_rejected(validator, empty_state, flow_list):
    r = _validate(validator, empty_state, TurnPlan.from_dict({}), flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MISSING_TRACK


def test_multiple_tracks_rejected(validator, empty_state, flow_list):
    plan = TurnPlan.from_dict({
        "task": {"commands": [{"command": "start_flow", "flow": "refund_request"}]},
        "knowledge": {"intents": ["refund_policy"]},
    })
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MULTIPLE_TRACKS


def test_chitchat_only_passes(validator, empty_state, flow_list):
    r = _validate(validator, empty_state, TurnPlan.from_dict({"chitchat": {}}), flow_list)
    assert r.valid is True


# ---------- task 轨五重校验 ----------

def test_empty_commands_rejected(validator, empty_state, flow_list):
    r = _validate(validator, empty_state, TurnPlan.from_dict({"task": {"commands": []}}), flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MISSING_TASK_COMMANDS


def test_unknown_command_type_rejected(validator, empty_state, flow_list):
    # 绕过注册表直接造基类命令 -> 白名单外类型
    plan = TurnPlan(task=TaskTurnPlan(commands=[Command(command="weird_cmd")]))
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.INVALID_TASK_COMMANDS


def test_multiple_start_flows_rejected(validator, empty_state, flow_list):
    plan = TurnPlan(task=TaskTurnPlan(commands=[
        StartFlowCommand(command="start_flow", flow="refund_request"),
        StartFlowCommand(command="start_flow", flow="onboarding"),
    ]))
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MULTIPLE_TASK_FLOWS


def test_nonexistent_flow_rejected(validator, empty_state, flow_list):
    # 幻觉流程名 -> 防幻觉核心拦截
    plan = TurnPlan.from_dict({"task": {"commands": [{"command": "start_flow", "flow": "not_exist_flow"}]}})
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.UNKNOWN_TASK_FLOW


def test_system_flow_cannot_be_started(validator, empty_state, flow_list):
    # system_ 前缀即便真实存在也禁止 LLM 直接开
    plan = TurnPlan.from_dict({"task": {"commands": [{"command": "start_flow", "flow": "system_task_started"}]}})
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.UNKNOWN_TASK_FLOW


def test_valid_start_flow_passes(validator, empty_state, flow_list):
    plan = TurnPlan.from_dict({"task": {"commands": [{"command": "start_flow", "flow": "refund_request"}]}})
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is True


def test_set_slots_only_passes(validator, empty_state, flow_list):
    plan = TurnPlan.from_dict({"task": {"commands": [{"command": "set_slots", "slots": {"order_number": "ORDER_10001"}}]}})
    r = _validate(validator, empty_state, plan, flow_list)
    assert r.valid is True


# ---------- knowledge 轨校验 ----------

def test_empty_intents_rejected(validator, empty_state, flow_list):
    r = _validate(validator, empty_state, TurnPlan.from_dict({"knowledge": {"intents": []}}), flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MISSING_KNOWLEDGE_INTENT


def test_hallucinated_intent_rejected(validator, empty_state, flow_list):
    # 注册表里没有的意图 id -> 幻觉意图
    r = _validate(validator, empty_state, TurnPlan.from_dict({"knowledge": {"intents": ["made_up_intent"]}}), flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MISSING_KNOWLEDGE_INTENT


def test_order_info_without_focus_rejected(validator, empty_state, flow_list):
    # order_info 要求聚焦 order 对象，但 state 无聚焦对象
    r = _validate(validator, empty_state, TurnPlan.from_dict({"knowledge": {"intents": ["order_info"]}}), flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MISSING_FOCUSED_OBJECT


def test_order_info_with_focus_passes(validator, order_state, flow_list):
    r = _validate(validator, order_state, TurnPlan.from_dict({"knowledge": {"intents": ["order_info"]}}), flow_list)
    assert r.valid is True


def test_product_info_wrong_object_type_rejected(validator, order_state, flow_list):
    # 聚焦的是 order，但 product_info 要求 product -> 类型不匹配
    r = _validate(validator, order_state, TurnPlan.from_dict({"knowledge": {"intents": ["product_info"]}}), flow_list)
    assert r.valid is False
    assert r.reason == ClarifyReason.MISSING_FOCUSED_OBJECT


def test_refund_policy_needs_no_object(validator, empty_state, flow_list):
    # 政策类意图 requires_object=None，无聚焦对象也放行
    r = _validate(validator, empty_state, TurnPlan.from_dict({"knowledge": {"intents": ["refund_policy"]}}), flow_list)
    assert r.valid is True
