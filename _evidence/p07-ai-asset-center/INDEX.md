# P07 AI 素材中心 — 证据索引

## pytest-20261013.log
- **命令**：`uv run python -m pytest tests -v`（PYTHONIOENCODING=utf-8）
- **结果**：18 passed, 1 warning in 0.74s
- **测试隔离**：`conftest.py` 用 monkeypatch 把 `DB_PATH` / `UPLOAD_DIR` 重定向到 tmp_path，
  再 `init_db()` 重建临时库并播种 demo 数据，不污染真实 `data/assets.db`
- **证明的功能（对应验收门禁）**：
  - **上传素材→打标→以文搜图命中**：
    - `test_create_asset_upload_and_delete`：multipart 上传落库、file_size 正确、总数 12→13、删除后 404 且总数回落
    - `test_create_asset_without_file`：无文件上传 file_size=0
    - `test_search_by_text_hits`：查询「防晒 夏天」命中 AST-007，relevance_score 归一化最高为 1.0
    - `test_search_filter_by_type`：按 asset_type 过滤生效
    - `test_search_no_match_returns_empty`：无匹配返回空列表（不编造结果）
  - **素材与投放效果关联报表可查看**：
    - `test_performance_report`：7 条关联记录，含 SQL 计算的 ctr/cvr/roi，按 revenue 降序
    - `test_performance_report_filter_platform`：按平台（douyin）过滤命中 3 条
  - **列表/详情/统计**：分页（5+5+2）、类型过滤、关键词过滤、详情带 performance、404
- **Mock 边界（已在响应体 `mock_note` 字段 + README 双处标注）**：
  - `/api/v1/search`：基于 TF-IDF 文本匹配模拟 CLIP 多模态检索，**非真实向量检索**
  - `/api/v1/generate`：返回预设模板，**非真实 AI 图片/视频/文案生成**
- **修复**：`python-multipart` 是 Form/File 上传端点的真实运行依赖，原先缺失导致 app 无法导入，
  已补入 `pyproject.toml` 主依赖；`[tool.uv] package = false` 解决单文件 app 布局的 setuptools 打包发现失败

## 未测量 / 未覆盖（诚实标注）
- **真实 CLIP 多模态以文搜图召回率/精确率**：当前为 TF-IDF mock，未做真实向量检索评测
- **真实 AI 生成链路质量**：mock 模板，无生成质量评测
