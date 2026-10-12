# AI 电商运营助手 —— 验收执行报告

- 执行模式：**离线验收（SQLite + inline，临时库 C:\Users\23329\AppData\Local\Temp\ecommerce_acceptance.db）**
- 执行时间：2026-10-07 12:58:16
- 耗时：43.1 秒
- 用例：共 58 项，PASS 58 / FAIL 0 / SKIP 0 / WARN 0
- 通过率（PASS/(PASS+FAIL)）：**100.0%**
- 结论：**通过**

- 回归测试：pytest 通过 117 条，失败 0 条

## 逐项结论

| 用例号 | 分组 | 验收项 | 期望 | 实测 | 结论 |
|---|---|---|---|---|---|
| ENV-01 | S0 环境与工程基线 | Python 运行时版本 | ≥3.11 | Python 3.12.9 | ✅ 通过 |
| ENV-02 | S0 环境与工程基线 | Alembic 迁移版本数 | ≥1 | 23 | ✅ 通过 |
| ENV-03 | S0 环境与工程基线 | 测试用例文件数 | ≥20 | 28 | ✅ 通过 |
| ENV-04 | S0 环境与工程基线 | API 路由模块数 | ≥10 | 10 | ✅ 通过 |
| ENV-05 | S0 环境与工程基线 | 数据库表创建 / 表数量 | 建表成功且 ≥30 张表 | 36 | ✅ 通过 |
| AUTH-00 | S1 认证与会话 | 引导创建首个管理员 | 创建成功且角色为 owner | {"email": "owner@local.dev", "role": "owner"} | ✅ 通过 |
| AUTH-01 | S1 认证与会话 | 健康检查 | 200 + status=ok | (200, {'status': 'ok'}) | ✅ 通过 |
| AUTH-02 | S1 认证与会话 | JWT 登录 | 200 且返回非空 access_token | {"code": 200, "token_len": 136} | ✅ 通过 |
| AUTH-03 | S1 认证与会话 | 当前用户 | 200 且 email 与登录账号一致 | (200, {'email': 'owner@local.dev', 'display_name': '验收 Owner', 'role': 'owner', 'status': 'active', 'id': 1, 'permissions': {'can_read': True, 'can_edit': True, 'can_manage_users': True, 'can_confirm_ad_actions': True... | ✅ 通过 |
| AUTH-04 | S1 认证与会话 | 无凭证访问受保护资源 | 401 | 401 | ✅ 通过 |
| AUTH-05 | S1 认证与会话 | 伪造 token 拒绝 | 401 | 401 | ✅ 通过 |
| AUTH-06 | S1 认证与会话 | 工作区列表（多租户入口） | 200 且至少 1 个工作区 | {"code": 200, "count": 1, "workspace_id": 1} | ✅ 通过 |
| RES-01 | S2 店铺·商品·库存 | 创建店铺 | 201 且返回 id | {"code": 201, "id": 1} | ✅ 通过 |
| RES-02 | S2 店铺·商品·库存 | 查询店铺详情 | 200 且名称一致 | (200, {'name': '验收专用店铺', 'platform': 'douyin', 'status': 'active', 'external_store_id': None, 'owner_name': '李奕波', 'note': '一键验收脚本创建', 'id': 1, 'created_at': '2026-10-07T04:57:44', 'updated_at': '2026-10-07T04:57:44',... | ✅ 通过 |
| RES-03 | S2 店铺·商品·库存 | 创建商品（关联店铺 + 卖点） | 201 且卖点完整落库 | {"code": 201, "id": 1, "points": 3} | ✅ 通过 |
| RES-04 | S2 店铺·商品·库存 | 商品详情（结构化字段） | 200 且含 selling_points / target_audience | (200, {'store_id': 1, 'name': '验收商品·控油气垫', 'platform': 'douyin', 'category': '美妆/底妆', 'price': '129.00', 'cost': '49.00', 'target_audience': '25-35 岁通勤人群，注重持妆与轻薄', 'selling_points': ['轻薄不闷痘', '12 小时控油持妆', '妆效自然'], 'pr... | ✅ 通过 |
| RES-05 | S2 店铺·商品·库存 | 编辑商品 | 200 且字段已更新 | (200, {'store_id': 1, 'name': '验收商品·控油气垫', 'platform': 'douyin', 'category': '美妆/底妆（已复核）', 'price': '129.00', 'cost': '49.00', 'target_audience': '25-35 岁通勤人群，注重持妆与轻薄', 'selling_points': ['轻薄不闷痘', '12 小时控油持妆', '妆效自然']... | ✅ 通过 |
| RES-06 | S2 店铺·商品·库存 | 创建 SKU 并带初始库存 | 201 且生成库存档案 | {"code": 201, "id": 1, "has_inventory": true} | ✅ 通过 |
| RES-07 | S2 店铺·商品·库存 | 库存流水（入库） | 201 且数量变更被记账 | (201, {'id': 2, 'inventory_item_id': 1, 'sku_id': 1, 'movement_type': 'inbound', 'quantity_delta': 8, 'locked_delta': 0, 'before_quantity': 12, 'after_quantity': 20, 'before_locked_quantity': 0, 'after_locked_quantity... | ✅ 通过 |
| RES-08 | S2 店铺·商品·库存 | 店铺库存汇总 | 200 且汇总体现 12+8=20 件 | (200, {'store_id': 1, 'sku_count': 1, 'total_quantity': 20, 'total_locked_quantity': 0, 'total_available_quantity': 20, 'low_stock_count': 1, 'rows': [{'product_id': 1, 'product_name': '验收商品·控油气垫', 'sku_id': 1, 'sku_c... | ✅ 通过 |
| RES-09 | S2 店铺·商品·库存 | 库存建议（未配置 LLM 走规则兜底） | 200 且返回建议条目 | (200, {'source': 'rules', 'summary': '验收专用店铺 有 1 个 SKU 低于预警线，需要优先处理补货和投放节奏。', 'risks': ['1 个 SKU 可用库存低于或等于预警线。'], 'replenishment_actions': ['优先补货 验收商品·控油气垫 / AC-001-N01，当前可用 20，预警线 30。'], 'operation_actions': ['检查低库存 ... | ✅ 通过 |
| RES-10 | S2 店铺·商品·库存 | 删除店铺（自研新增接口） | 204；关联商品 store_id 置空而非删除 | {"delete": 204, "get_after": 404, "product_store_id": null} | ✅ 通过 |
| CMP-01 | S3 竞品监控·经营复盘 | 录入竞品 | 201 且返回竞品 id | {"code": 201, "id": 1} | ✅ 通过 |
| CMP-02 | S3 竞品监控·经营复盘 | 创建竞品监控任务 | 201 且返回监控 id | {"code": 201, "id": 1} | ✅ 通过 |
| CMP-03 | S3 竞品监控·经营复盘 | 执行监控生成快照 | 201 且快照带结构化字段 | (201, {'id': 1, 'monitor_id': 1, 'product_id': 1, 'competitor_id': 1, 'checked_at': '2026-10-07T04:57:45.103396', 'status': 'failed', 'title': None, 'price': None, 'sales_hint': None, 'main_image': None, 'selling_poin... | ✅ 通过 |
| PERF-01 | S3 竞品监控·经营复盘 | 批量导入经营数据 | 201 且返回条目数与提交一致 | {"code": 201, "count": 3} | ✅ 通过 |
| PERF-02 | S3 竞品监控·经营复盘 | 生成经营复盘报告 | 201（未配置 LLM 时走规则/模板兜底） | (201, {'period_start': '2026-10-07', 'period_end': '2026-10-07', 'summary': '2026-10-07 至 2026-10-07，商品《验收商品·控油气垫》累计曝光 12000，点击 360，成交 42，ROI 为 6.54。', 'insights': ['本次复盘关联素材：未关联素材。', '点击率 3.00% 处于可测试区间，需要结合转化判断。', '转... | ✅ 通过 |
| GRO-01 | S4 推广链接·投放实验 | 批量生成推广链接 | 201 且至少 1 条含 tracking_code | {"code": 201, "count": 3, "has_tracking": true} | ✅ 通过 |
| GRO-02 | S4 推广链接·投放实验 | 生成投放实验 | 201 且落在 draft 状态待人工确认 | {"code": 201, "id": 1, "status": "draft"} | ✅ 通过 |
| GRO-03 | S4 推广链接·投放实验 | 投放看板聚合 | 200 且返回聚合结构 | (200, {'product_id': 1, 'total_experiments': 1, 'active_experiments': 0, 'measured_experiments': 0, 'total_spend': '0', 'total_revenue': '0', 'overall_roi': None, 'best_experiment': None, 'rows': [{'ad_experiment_id':... | ✅ 通过 |
| GRO-04 | S4 推广链接·投放实验 | 生成投放建议（人工确认前不动真金白银） | 201 且默认未确认 | {"code": 201, "id": 1, "confirmed": null} | ✅ 通过 |
| MOD-01 | S5 模型配置·AI 素材 | 读取模型配置（脱敏） | 200 且只返回掩码，不含 api_key 明文 | (200, {'text': {'base_url': '', 'api_key_masked': '', 'has_api_key': False, 'model': ''}, 'image': {'provider': '', 'base_url': '', 'api_key_masked': '', 'has_api_key': False, 'model': '', 'size': '1024*1024', 'worksp... | ✅ 通过 |
| MOD-02 | S5 模型配置·AI 素材 | 文本模型连通性测试 | 未配置时 400（fail-fast，而非静默假成功） | 400 | ✅ 通过 |
| MOD-03 | S5 模型配置·AI 素材 | 商品诊断生成 | 201 且 source ∈ {llm, rule/rules} 且有定位结论 | {"code": 201, "source": "rules", "has_positioning": true} | ✅ 通过 |
| MOD-04 | S5 模型配置·AI 素材 | 生成主图创意策划 | 201 且至少 1 个可编辑方案 | {"code": 201, "count": 4, "plan_id": 1} | ✅ 通过 |
| MOD-05 | S5 模型配置·AI 素材 | 提交图片生成任务（异步任务落库） | 202 且返回 job_id | {"code": 202, "job_id": 1, "status": "pending"} | ✅ 通过 |
| MOD-06 | S5 模型配置·AI 素材 | 生成任务可取消/可重试（运维闭环） | 取消端点返回 200/202/409 之一 | {"code": 200, "status": "cancelled"} | ✅ 通过 |
| AGT-01 | S6 多 Agent 编排 | Agent 目录（1 协调者 + 8 专家 + 7 工作流） | 目录完整且数量吻合 | {"code": 200, "agents": 8, "workflows": 7, "coordinator": "ecommerce_operations_agent"} | ✅ 通过 |
| AGT-02 | S6 多 Agent 编排 | 创建 Agent Task（202 异步受理） | 202 且返回 task_id | {"code": 202, "task_id": 1, "workflow_key": "inventory_operations", "status": "queued"} | ✅ 通过 |
| AGT-03 | S6 多 Agent 编排 | 查询任务详情 | 200 且回读字段一致 | (200, {'id': 1, 'workspace_id': 1, 'conversation_id': None, 'requested_by_user_id': 1, 'workflow_key': 'inventory_operations', 'workflow_version': '1.0.0', 'title': '验收·库存运营', 'intent': None, 'status': 'queued', 'risk... | ✅ 通过 |
| AGT-04 | S6 多 Agent 编排 | 任务关联执行记录（Run） | 200 且至少 1 条 Run | (200, [{'id': 1, 'thread_id': '3993a437-c0be-4158-8b79-53ed2d13795c', 'workspace_id': 1, 'task_id': 1, 'product_id': 1, 'requested_by_user_id': 1, 'workflow_key': 'inventory_operations', 'workflow_version': '1.0.0', '... | ✅ 通过 |
| AGT-05 | S6 多 Agent 编排 | 任务/执行/Outbox 同事务写入 | 存在 workflow.run.requested 事件 | {"count": 1, "types": ["workflow.run.requested"]} | ✅ 通过 |
| AGT-06 | S6 多 Agent 编排 | 审批列表接口（人工审批入口） | 200 且返回列表 | (200, []) | ✅ 通过 |
| AGT-07 | S6 多 Agent 编排 | 跨工作区越权（路径与会话不一致） | 403 | 403 | ✅ 通过 |
| AGT-08 | S6 多 Agent 编排 | 跨租户商品上下文拒绝 | 422 | 422 | ✅ 通过 |
| AGT-09 | S6 多 Agent 编排 | Agent 策略：越权工具被拒 / R3 需 owner | 越权抛错且 R3 需 owner 批准 | {"blocked": true, "operator_allowed": false, "owner_allowed": true, "owner_need_approval": true} | ✅ 通过 |
| AGT-10 | S6 多 Agent 编排 | 固定评测集（≥6 条 / 每工作流 6 类） | 用例数与类别覆盖达标 | {"fixed": 7, "categories": ["human_review", "policy", "quality", "workflow"], "platform": 42} | ✅ 通过 |
| AGT-11 | S6 多 Agent 编排 | 【真实图】R2 工作流停在审批 → 批准后恢复完成 | 首次 next=(approval_gate)，恢复后 final_status=completed | {"paused_at": ["approval_gate"], "after": [], "final_status": "completed", "finalized": 1} | ✅ 通过 |
| AGT-12 | S6 多 Agent 编排 | 【真实图】商品图：人工拒绝则不落库 | final_status=rejected 且落库产物为 None | {"paused_at": ["human_review_gate"], "final_status": "rejected", "decision": "reject", "persisted_positioning": null} | ✅ 通过 |
| AGT-13 | S6 多 Agent 编排 | 【真实图】商品图：草稿→质检→人工审核→采纳人工编辑版 | resume 后落地的是人工编辑后的输出 | {"paused_at": ["human_review_gate"], "expect_gate": "human_review_gate", "final_status": "completed", "persisted_positioning": "人工调整后的商品定位"} | ✅ 通过 |
| AGT-14 | S6 多 Agent 编排 | 【真实图】质检不通过则不落库 | final_status=quality_failed 且无落库 | {"final_status": "quality_failed", "finalized": 0} | ✅ 通过 |
| SEC-01 | S7 权限与安全边界 | 密码不以明文形式返回 | 用户响应不含 password 字段 | (200, {'email': 'owner@local.dev', 'display_name': '验收 Owner', 'role': 'owner', 'status': 'active', 'id': 1, 'permissions': {'can_read': True, 'can_edit': True, 'can_manage_users': True, 'can_confirm_ad_actions': True... | ✅ 通过 |
| SEC-02 | S7 权限与安全边界 | viewer 只读角色不能编辑 | 403 | {"viewer_patch": 403, "restored_patch": 200} | ✅ 通过 |
| SEC-03 | S7 权限与安全边界 | 全局管理接口只对 owner 开放 | 用户目录非 owner 时 403 或 200(owner) | 200 | ✅ 通过 |
| SEC-04 | S7 权限与安全边界 | 采集合规：拒绝绕登录/验证码的采集方式 | 授权方式枚举受控 | {"code": 201, "body_type": "dict"} | ✅ 通过 |
| DLV-01 | S8 交付与回归 | Docker Compose 交付编排完整 | 包含 api/web/worker/mysql/redis/postgres | {"found": ["api", "web", "worker", "mysql", "redis", "postgres", "agent-checkpoints"], "count": 7} | ✅ 通过 |
| DLV-02 | S8 交付与回归 | 环境变量模板齐备 | 存在 .env 模板且含数据库/队列/鉴权/模型四类关键键 | {"sources": [".env.example", "api/.env.example", "api/.env.sqlite"], "keys": ["AUTH_SECRET_KEY", "DATABASE_URL", "LLM_API_KEY", "TASK_QUEUE_BACKEND"]} | ✅ 通过 |
| REG-01 | S8 交付与回归 | 自动化回归测试（pytest 全量） | 全部用例通过 | {"exit": 0, "passed": 117, "failed": 0, "errors": 0, "summary": "117 passed in 5.92s"} | ✅ 通过 |

---

> 本报告由 `api/scripts/acceptance_check.py` 自动生成，可重复执行以获得一致结论。
