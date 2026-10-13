# task/command/models.py 与 plan/models.py 的纯逻辑测试
# 覆盖「LLM 结构化指令反序列化」与「三轨道计划还原」——防幻觉链路的第一环。

import pytest
from pydantic import ValidationError

from task.command.models import (
    CancelFlowCommand,
    Command,
    ResumeFlowCommand,
    SetSlotsCommand,
    StartFlowCommand,
)
from plan.models import (
    ChitchatTurnPlan,
    ClarifyReason,
    KnowledgeTurnPlan,
    TaskTurnPlan,
    TurnPlan,
)


# ---------- Command.from_dict 判别式反序列化 ----------

def test_command_from_dict_start_flow():
    cmd = Command.from_dict({"command": "start_flow", "flow": "refund_request"})
    assert isinstance(cmd, StartFlowCommand)
    assert cmd.flow == "refund_request"


def test_command_from_dict_set_slots():
    cmd = Command.from_dict({"command": "set_slots", "slots": {"order_number": "A001"}})
    assert isinstance(cmd, SetSlotsCommand)
    assert cmd.slots == {"order_number": "A001"}


def test_command_from_dict_cancel_flow():
    cmd = Command.from_dict({"command": "cancel_flow"})
    assert isinstance(cmd, CancelFlowCommand)


def test_command_from_dict_resume_flow_default_none():
    cmd = Command.from_dict({"command": "resume_flow"})
    assert isinstance(cmd, ResumeFlowCommand)
    assert cmd.flow is None


def test_command_from_dict_resume_flow_with_id():
    cmd = Command.from_dict({"command": "resume_flow", "flow": "refund_request"})
    assert isinstance(cmd, ResumeFlowCommand)
    assert cmd.flow == "refund_request"


def test_command_from_dict_unknown_raises():
    # 注册表外的指令名 -> KeyError（设计如此：LLM 编造命令应暴露）
    with pytest.raises(KeyError):
        Command.from_dict({"command": "self_destruct"})


def test_start_flow_command_requires_flow():
    # 缺 flow 字段 -> pydantic 校验错误
    with pytest.raises(ValidationError):
        StartFlowCommand(command="start_flow")


# ---------- TurnPlan.from_dict 三轨道还原 ----------

def test_turnplan_task_only():
    plan = TurnPlan.from_dict({
        "task": {"commands": [{"command": "start_flow", "flow": "refund_request"}]},
        "knowledge": None,
        "chitchat": None,
    })
    assert plan.task is not None
    assert plan.knowledge is None
    assert plan.chitchat is None
    assert isinstance(plan.task.commands[0], StartFlowCommand)


def test_turnplan_knowledge_only():
    plan = TurnPlan.from_dict({
        "task": None,
        "knowledge": {"intents": ["refund_policy", "shipping_policy"]},
        "chitchat": None,
    })
    assert plan.knowledge is not None
    assert plan.knowledge.intents == ["refund_policy", "shipping_policy"]
    assert plan.task is None


def test_turnplan_chitchat_only():
    plan = TurnPlan.from_dict({"task": None, "knowledge": None, "chitchat": {}})
    assert isinstance(plan.chitchat, ChitchatTurnPlan)
    assert plan.task is None and plan.knowledge is None


def test_turnplan_all_null():
    # 三轨全 null -> 三个字段都是 None（白纸计划，validator 会拒）
    plan = TurnPlan.from_dict({"task": None, "knowledge": None, "chitchat": None})
    assert plan.task is None
    assert plan.knowledge is None
    assert plan.chitchat is None


def test_turnplan_multi_track():
    # 多轨道并存也能还原（互斥判定交给 validator）
    plan = TurnPlan.from_dict({
        "task": {"commands": [{"command": "cancel_flow"}]},
        "knowledge": {"intents": ["order_info"]},
        "chitchat": None,
    })
    assert plan.task is not None and plan.knowledge is not None


def test_clarify_reason_is_str_enum():
    # ClarifyReason 继承 str，可直接当字符串比较/序列化
    assert ClarifyReason.MISSING_TRACK == "missing_track"
    assert isinstance(ClarifyReason.UNKNOWN_TASK_FLOW, str)


def test_subplan_from_dict_direct():
    assert TaskTurnPlan.from_dict({"commands": [{"command": "cancel_flow"}]}).commands
    assert KnowledgeTurnPlan.from_dict({"intents": ["platform_rule"]}).intents == ["platform_rule"]
