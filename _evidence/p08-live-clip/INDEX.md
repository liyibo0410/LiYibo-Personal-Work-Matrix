# P08 直播切片 — 证据索引

## pytest-20261013.log
- **命令**：`uv run python -m pytest tests -v`（PYTHONIOENCODING=utf-8）
- **结果**：30 passed, 1 warning in 0.11s
- **测试隔离**：`conftest.py` autouse fixture 记录 `_all_tasks` 原有 key，测试后删除新增任务，
  避免 `/process` 写入污染其他用例；streams/clips/asr 在 import 时只读生成，无需快照
- **证明的功能（对应验收门禁）**：
  - **打点结果可解释（每段给出得分构成）**：
    - `test_list_clips_and_score_breakdown_explainable`：每个切片含 keyword_density/energy_level/
      speech_rate/interaction 四维得分（0–95）+ keyword_hits + explanation 文本理由
    - `test_score_clip_keyword_hits_match_theme`：命中关键词属于对应主题词表且写入 explanation
    - `test_score_clip_interaction_and_promo_boost_isolated`：保持 text[:30] 不变（hash 种子相同）
      隔离验证互动词/促销词加成，证明评分逻辑可解释、非随机
    - `test_score_clip_deterministic_within_process`：同进程同输入 → 同分数
  - **批量任务队列可用，进度可见**：
    - `test_process_creates_completed_task`：单场任务 status=completed / progress=100 /
      clips_generated 等于该场切片数
    - `test_process_multi_stream`：三场批量任务 clips_generated == 全部切片数
    - `test_process_invalid_stream_400`：不存在的 stream_id → 400
    - `test_tasks_list_includes_seed_and_new`：任务列表含 seed 任务 + 新建任务
  - **样例端到端**：3 场直播（美妆/美食/时尚）→ ASR 分段 → 切片生成 → 列表/详情/统计
    - `test_gen_asr_segments_respects_duration`：ASR 分段遵守时长上限
    - `test_gen_asr_segments_unknown_theme_falls_back_to_beauty`：未知主题回退 beauty 脚本
    - 列表过滤（stream_id/min_score）、排序（score desc）、分页、404、stats 一致性
- **Mock 边界（已在 /health `mock_boundaries` + README 双处标注）**：
  - ASR：模拟语音转文字，**非真实语音识别**
  - 评分：基于规则的模拟算法，**非真实 ML 模型**
  - 视频处理：**无实际 ffmpeg 操作**（不产出真实视频文件）
- **说明**：`_score_clip` 用 `hash(text[:30])` 作种子，Python 字符串 hash 每进程随机化，
  故跨进程分值不固定；测试只断言同进程确定性与结构/相对关系，不硬编码分值（诚实标注）

## 未测量 / 未覆盖（诚实标注）
- **真实视频出片 + 前后对比截图**：无 ffmpeg 实际裁剪，属人工演示项，非 pytest 覆盖
- **真实 ASR 准确率 / 打点质量评测**：mock 算法，无真实模型评测
