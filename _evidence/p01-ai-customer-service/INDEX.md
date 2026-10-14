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

## P01-mysql-restored.png · 客服页「加载历史消息失败 / 加载订单列表失败」根因与修复（2026-10-14 上午）

- **现象**：外壳挂载 P01 后，中间历史消息区与右侧「业务对象 → 订单」两处同时报错。
- **根因**：P01 后端(18082) 与商城中台(18081) 都连 MySQL 容器 `customer-service-mysql`
  （`external/docker/docker-compose.yml` 发布 `127.0.0.1:3307:3306`）。而桌面「一键启动」/ `start-all.bat`
  只管 SERVICE_REGISTRY 里那 15 个业务进程，**不管 Docker** —— 本轮 Docker Desktop 引擎没运行，
  3307 无人监听，两个接口全部 500。日志 `_runtime/logs/p01-api.log` 与 `p01-commerce.log`：
  `sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on '127.0.0.1'")`。
  与 `_evidence/shell/INDEX.md:90` 那条历史记录同源但反过来：那次是 18081 没被启动而 MySQL 在听，这次是 18081 在听而 MySQL 没起。
- **处置**：拉起 Docker Desktop（引擎 15.9s 就绪）→ 容器因 `restart: unless-stopped` 自动回到 3307；
  并把这一步并进启动器（`_tools/launcher.py::ensure_mysql`，宿主端口从 compose 解析、不抄常量），见 `_evidence/INDEX.md` D21。
- **复验走的是浏览器同一条 vite 代理路径**（不是直连后端）：
  - `GET http://127.0.0.1:5173/api/chat/history?sender_id=u1001` → **200，106 条**真实历史消息
  - `GET http://127.0.0.1:5173/commerce/users/u1001/orders` → **200**，iPhone 15 Pro ¥8999（待发货）、
    小米恒温电热水壶 ¥149（运输中）、Apple Watch Series 9 ¥2999、美的空气炸锅 ¥399 等
  - 页面 DOM 断言：`err_history=false, err_orders=false, has_iPhone=true` → 截图 `P01-mysql-restored.png`
  - 对照：`/commerce/users/1/orders` 返回 404「用户 1 不存在。」—— 那是中台自己的业务响应（真实 user_id 是 u1001/u1002/u1003），不是故障
- **仍未闭环（与本轮无关，不变）**：50 并发压测 P95 / 错误率、LLM 生成质量自动评测。
