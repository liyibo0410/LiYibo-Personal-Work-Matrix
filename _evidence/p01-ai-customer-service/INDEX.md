# P01 AI 电商客服 — 证据索引

## pytest-20261013.log
- **命令**：`uv run python -m pytest tests -v`（PYTHONIOENCODING=utf-8）
- **结果**：62 passed in 1.43s
- **测试范围**：聚焦「不依赖 LLM 网络调用」的确定性核心逻辑（规划/校验/状态机/规则话术）
- **证明的功能（对应验收门禁）**：
  - **意图识别 → 防幻觉校验链**（`test_turn_validator.py`，18 例）：
    - 三轨道判定：无轨道→MISSING_TRACK；多轨道→MULTIPLE_TRACKS；仅闲聊→放行
    - task 轨五重校验：空命令→MISSING_TASK_COMMANDS；未知命令类型→INVALID_TASK_COMMANDS；
      多流程→MULTIPLE_TASK_FLOWS；**幻觉流程名→UNKNOWN_TASK_FLOW**；system_ 内部流程禁开；
      合法 start_flow / set_slots 放行
    - knowledge 轨校验：空意图/幻觉意图→MISSING_KNOWLEDGE_INTENT；
      order_info 无聚焦对象→MISSING_FOCUSED_OBJECT；聚焦类型不匹配（order vs product_info）→拒绝；
      政策类意图（requires_object=None）免对象放行
  - **LLM 结构化指令反序列化**（`test_command_and_plan.py`）：Command.from_dict 判别式分发四子类、
    未知命令 KeyError、缺字段 ValidationError；TurnPlan.from_dict 三轨道还原（单轨/多轨/全 null）
  - **对话状态机**（`test_dialogue_state.py`）：任务生命周期（开始/结束/中断压栈/LIFO 恢复/按 flow_id 恢复/
    取消作废）、系统过场优先级、槽位增删、会话开启幂等/关闭/重置保留历史、回合 begin/commit、
    SystemContext 带鉴别器联合类型反序列化 + 持久化往返不丢子类字段
  - **负面情绪/澄清话术**（`test_clarify_responder.py`，10 例）：build_clarify_message 按 9 类原因码
    给出对应追问话术，任何原因码都产出非空兜底句
- **整理**：`test/sqlalchemy/test_sync_usage.py`（SQLAlchemy 学习样例，非真实测试，`main()` 入口 +
  import 不存在的 `models.Base/User`）已重命名为 `sqlalchemy_sync_usage_demo.py`，去掉 `test_` 前缀避免被误收集；
  清理了残留的 pytest `.pyc`。真实 pytest 套件统一放在 `tests/`（testpaths=["tests"]）

## 未测量 / 未覆盖（诚实标注）
- **端到端「提问→意图识别→知识检索→生成回复→负面情绪建单转人工」**：依赖真实 LLM 端点 + MySQL + 商城 API，
  属人工演示项；当前 pytest 只覆盖确定性规划/校验/状态机逻辑，**未对 LLM 生成质量做自动化评测**
- **50 并发压测 P95 / 错误率**：未在本轮执行，需真实服务起来后用压测工具单独跑
- **RAG/FAQ 检索召回质量**：knowledge/providers 走外部知识库，未做检索评测
