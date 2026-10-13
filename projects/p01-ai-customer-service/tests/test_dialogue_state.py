# domain/state.py 与 domain/contexts.py 的纯逻辑测试
# 覆盖对话状态机：任务生命周期（开始/中断/恢复/取消）、会话、回合、聚焦对象、槽位。
# 以及 SystemContext 带鉴别器联合类型的反序列化（持久化往返不丢子类字段）。

import pytest

from domain.contexts import (
    CanceledSystemContext,
    CollectedSystemContext,
    InterruptedSystemContext,
    ResumedSystemContext,
    StartedSystemContext,
    TaskContext,
    system_context_adapter,
)
from domain.messages import BotMessage, FocusedObject, MessageType, UserMessage
from domain.state import DialogueState, Session, Turn


def _user_msg(text="你好", mid="m1"):
    return UserMessage(sender_id="user_001", message_id=mid, type=MessageType.TEXT, text=text)


# ---------- 任务生命周期 ----------

def test_start_and_end_active_task():
    st = DialogueState(sender_id="user_001")
    assert st.active_task is None
    task = TaskContext(flow_id="order_query")
    st.start_active_task(task)
    assert st.active_task is task
    st.end_active_task()
    assert st.active_task is None


def test_interrupt_pushes_to_paused_stack():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="refund_request", step_id="collect_reason"))
    st.interrupted_active_task()
    assert st.active_task is None
    assert len(st.paused_tasks) == 1
    assert st.paused_tasks[0].flow_id == "refund_request"
    # 现场（step_id）被保留，可从挂起处续跑
    assert st.paused_tasks[0].step_id == "collect_reason"


def test_resume_latest_paused_lifo():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="A"))
    st.interrupted_active_task()
    st.start_active_task(TaskContext(flow_id="B"))
    st.interrupted_active_task()
    assert [t.flow_id for t in st.paused_tasks] == ["A", "B"]
    # flow_id=None -> 恢复最近挂起的（LIFO）
    assert st.resumed_active_task() is True
    assert st.active_task.flow_id == "B"
    assert [t.flow_id for t in st.paused_tasks] == ["A"]


def test_resume_by_flow_id():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="A"))
    st.interrupted_active_task()
    st.start_active_task(TaskContext(flow_id="B"))
    st.interrupted_active_task()
    # 指定 flow_id 精确恢复 A，并从栈移除
    assert st.resumed_active_task(flow_id="A") is True
    assert st.active_task.flow_id == "A"
    assert [t.flow_id for t in st.paused_tasks] == ["B"]


def test_resume_unknown_flow_id_returns_false():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="A"))
    st.interrupted_active_task()
    assert st.resumed_active_task(flow_id="does_not_exist") is False
    # 失败时不动栈、不激活
    assert st.active_task is None
    assert len(st.paused_tasks) == 1


def test_resume_empty_stack_returns_false():
    st = DialogueState(sender_id="user_001")
    assert st.resumed_active_task() is False


def test_cancel_clears_task_and_system():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="refund_request"))
    st.start_active_system_task(StartedSystemContext(started_flow_id="refund_request"))
    st.cancel_active_task()
    assert st.active_task is None
    assert st.active_system_task is None
    # 取消是作废，不进挂起栈
    assert st.paused_tasks == []


def test_current_active_task_system_priority():
    st = DialogueState(sender_id="user_001")
    biz = TaskContext(flow_id="order_query")
    st.start_active_task(biz)
    # 无系统过场 -> 返回业务任务
    assert st.current_active_task() is biz
    # 有系统过场 -> 系统优先
    sys_ctx = CollectedSystemContext(slot_name="order_id", response={"text": "请提供订单号"})
    st.start_active_system_task(sys_ctx)
    assert st.current_active_task() is sys_ctx
    st.end_active_system_task()
    assert st.current_active_task() is biz


# ---------- 槽位 ----------

def test_set_and_remove_slots():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="refund_request", slots={"order_number": "A001"}))
    st.set_slots({"reason": "尺寸不合"})
    assert st.active_task.slots == {"order_number": "A001", "reason": "尺寸不合"}
    st.remove_slot("reason")
    assert "reason" not in st.active_task.slots


def test_remove_missing_slot_raises():
    st = DialogueState(sender_id="user_001")
    st.start_active_task(TaskContext(flow_id="x"))
    with pytest.raises(KeyError):
        st.remove_slot("not_there")


# ---------- 会话 ----------

def test_start_session_idempotent():
    st = DialogueState(sender_id="user_001")
    assert st.current_session() is None
    st.start_session()
    first_id = st.current_session_id
    assert st.current_session() is not None
    # 已有当前会话再调用不重复创建
    st.start_session()
    assert st.current_session_id == first_id
    assert len(st.sessions) == 1


def test_close_current_session():
    st = DialogueState(sender_id="user_001")
    st.start_session()
    sess = st.current_session()
    st.close_current_session()
    assert st.current_session_id is None
    assert sess.closed_at is not None
    # 历史会话保留
    assert len(st.sessions) == 1


def test_reset_runtime_keeps_history():
    st = DialogueState(sender_id="user_001")
    st.start_session()
    st.start_active_task(TaskContext(flow_id="A"))
    st.set_focused_object(FocusedObject(id="ORDER_1", type="order"))
    st.reset_runtime_state_for_new_session()
    # 运行时字段清空
    assert st.active_task is None
    assert st.focused_object is None
    assert st.current_session_id is None
    assert st.paused_tasks == []
    # 历史 sessions 保留
    assert len(st.sessions) == 1


# ---------- 回合 ----------

def test_begin_and_commit_turn():
    st = DialogueState(sender_id="user_001")
    st.start_session()
    st.begin_turn(_user_msg("我想退款"))
    assert st.pending_turn is not None
    assert st.pending_turn.user_message.text == "我想退款"
    # 补机器人回复后提交
    st.pending_turn.bot_messages.append(BotMessage(text="好的，请提供订单号"))
    st.commit_turn()
    assert st.pending_turn is None
    sess = st.current_session()
    assert len(sess.turns) == 1
    assert sess.turns[0].bot_messages[0].text == "好的，请提供订单号"


def test_begin_turn_without_session_is_noop():
    st = DialogueState(sender_id="user_001")
    # 无当前会话时不产生游离 pending_turn
    st.begin_turn(_user_msg("hi"))
    assert st.pending_turn is None


# ---------- SystemContext 鉴别器联合类型 ----------

def test_system_context_adapter_dispatches_subclass():
    data = {
        "flow_id": "system_task_started",
        "step_id": "start",
        "started_flow_id": "order_status_query",
        "started_flow_name": "订单状态查询",
    }
    obj = system_context_adapter.validate_python(data)
    assert isinstance(obj, StartedSystemContext)
    # 子类独有字段完整保留（父类 model_validate 会丢弃）
    assert obj.started_flow_id == "order_status_query"
    assert obj.started_flow_name == "订单状态查询"


@pytest.mark.parametrize("flow_id,cls", [
    ("system_task_started", StartedSystemContext),
    ("system_task_interrupted", InterruptedSystemContext),
    ("system_task_canceled", CanceledSystemContext),
    ("system_task_resumed", ResumedSystemContext),
    ("system_collect_information", CollectedSystemContext),
])
def test_system_context_all_subclasses_roundtrip(flow_id, cls):
    obj = system_context_adapter.validate_python({"flow_id": flow_id})
    assert isinstance(obj, cls)
    assert obj.flow_id == flow_id


def test_system_context_persistence_roundtrip_keeps_subclass_fields():
    # 模拟持久化往返：子类 -> dict -> 联合类型还原，字段不丢
    original = InterruptedSystemContext(
        interrupted_flow_id="refund_request",
        interrupted_flow_name="退款申请",
        started_flow_id="order_query",
        started_flow_name="订单查询",
    )
    dumped = original.model_dump(mode="json")
    restored = system_context_adapter.validate_python(dumped)
    assert isinstance(restored, InterruptedSystemContext)
    assert restored.interrupted_flow_id == "refund_request"
    assert restored.started_flow_name == "订单查询"
