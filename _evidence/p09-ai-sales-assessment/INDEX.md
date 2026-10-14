# `_evidence/p09-ai-sales-assessment/` 证据登记（P09 AI 销售考核）

> 本目录此前没有 `INDEX.md`，2026-10-14 补上。

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `pytest-20261013.log` | 早期套件记录（**30 passed**，与 `_evidence/INDEX.md` 声称的 34 不符，以本日志为准） | 2026-10-13 |
| `pytest-20261014.log` | **删除假人工分 + 新增真人评分台后全量测试：41 passed / 0 failed / 0.35s** | 2026-10-14 00:4x |
| `cross-module-p01-20261013.md` | P09→P01 真实 HTTP 取会话（65.5 / 70.5 两条）+ 降级路径不伪造会话 | 2026-10-13 |
| `2026-10-14_人工评分台_盲评.png` | 评分台真实渲染（22 条待评、五维权重口径说明、署名位、无 AI 分） | 2026-10-14 |

**测试命令**（在 `projects/p09-ai-sales-assessment/` 内；`PYTHONIOENCODING=utf-8` 必带，否则中文路径乱码使证据失效）：

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests -v
```

**环境**：`platform win32 -- Python 3.13.14, pytest-9.1.1`，`collected 41 items`。
测试**不会污染真实标注**：`tests/conftest.py` 的 `_isolate_human_labels` 把 `LABELS_PATH` 重定向到 `tmp_path`，
并在用例后恢复 `HUMAN_LABELS` 与每条会话的 `human_score`。

## 本次改的是什么（红线 2/3）

门禁要求「与人工评分一致性报告可出具」，而原实现是：

```python
noise = random.uniform(-12, 12)
conv.human_score = max(0, min(100, conv.score.overall + noise))   # 已删除
```

**用「AI 分 + 随机噪声」当人工分算 Cohen's Kappa，等于让 AI 和自己比**，Kappa 必然虚高，
且 README 还写着「预期 Moderate-Substantial」这种先给结论的表述。

改造后：

| 行为 | 现在 |
|---|---|
| 预置人工分 | 一律 `None`（实测 `GET /api/v1/conversations` 返回的 5 条 `human_score` 全为 `null`） |
| 人工分来源 | 只能由真人从 `/label.html`（`POST /api/v1/labeling/{id}`）写入，落盘 `data/human_labels.json` |
| 是否盲评 | 是 —— 队列与单条视图**在接口层就不返回 AI 分**，提交后才揭示（防锚定） |
| 口径一致 | 人工分沿用与 `_rule_based_score()` 完全相同的五维权重（25/25/15/20/15） |
| 样本不足 | `GET /api/v1/agreement` 返回 `kappa: null` + 原因 + 怎么评，**不出数** |
| 报告自证 | 响应带 `provenance`（评分者、时间范围、被评会话是 P01 真实导入还是演示预置、是否盲评、权重）与 `limitations` |

## 门禁对应情况（`.qoder/rules/04-验收门禁.md` P09 行）

| 门禁项 | 状态 | 证据 |
|---|---|---|
| 导入会话→自动评分→排行榜与个人报告 | ✅ 真实通过 | `pytest-20261014.log`（排行榜/报告/明细用例）+ `cross-module-p01-20261013.md` |
| 规则命中与 LLM 评分可解释可追溯 | ⚠️ 部分：评分是**规则引擎**，非真实 LLM（README 已标注） | `test_scoring.py` 12 条用例 |
| **与人工评分一致性报告可出具** | 🟡 **工具与口径已就位，报告尚未出具** —— 需真人评满 ≥5 条（当前 `labeled_count=0`） | 本目录 + `/label.html` |

## 未测量 / 边界

- 评分引擎为规则匹配，不具备语义理解；无并发压测、无 P95、无覆盖率数字。
- 会话与坐席是演示预置数据；真实会话需先 `POST /api/v1/import/from-p01`（导入的会话在内存里，
  **P09 重启即消失**，而人工标注按 id 落盘 —— 重启后若要继续评同一批真实会话，需重新导入）。
- 单人评分，无第二位评分者做 inter-rater 校验；四档切分阈值（85/70/55）本身会影响 Kappa。
  以上两条已写进接口 `limitations`，不靠 README 口头声明。
