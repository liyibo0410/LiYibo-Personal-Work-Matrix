# P07 AI 素材中心 — 证据索引

> 验收门禁（`.qoder/rules/04-验收门禁.md`）：**上传素材→打标→以文搜图命中**；**生成链路可跑（真实或 mock 均可但必须标注）**；
> **素材与投放效果关联报表可查看**。以下每条证据都对应一次真实执行。

## 2026-10-14 返工：从「只有后端能跑」到「全链路可演示」

返工前的缺陷（本轮实测确认，非推测）：前端零上传入口（`type="file"` 出现 0 次）、上传文件无预览路由（全 404）、
「智能打标」端点根本不存在、`generate` 是写死模板且引用 `via.placeholder.com` 外链、检索用 `split()+子串包含`
（6/8 条自然语言中文查询 0 命中）、`created_at` 写死 `2026-10-12T10:00:00`、上传不读宽高、
`tags` 以原始字符串入库导致前端 `JSON.parse` 抛错、README 三个指标（<100ms / 1000+ / >80%）无测量依据。

## 证据清单

| 文件 | 证据证明的功能 | 怎么复现 |
|---|---|---|
| `p07-01-dashboard.png` | 概览页 4 指标卡 + 6 张 ECharts 图全部由接口真实字段聚合（素材 14 / 已关联 8 / 花费 ¥45,200 / ROI 10.25x） | `python _tools\shot.py "http://127.0.0.1:8070/#dashboard" p07-01.png --module p07-ai-asset-center --wait 6` |
| `p07-02-library-upload-and-thumbs.png` | **上传素材**：上传面板 + 拖拽区 + 自动打标勾选；12 条素材缩略图来自 `GET /api/v1/assets/{id}/file` 真实文件；卡片显示真实尺寸（640×480 为上传测试图实测）、来源徽章（本地上传 / AI程序生成 / 演示数据）、真实时间戳 | 同上，`#library` |
| `p07-03-asset-detail-llm-tags.png` | **打标**：详情页标签由 LLM 真实产出（`tag_source=llm`），可「重新打标（覆盖）」与「追加」；投放数据录入表单就地提交 | 同上，`#asset/AST-B1AB14` |
| `p07-04-search-hit-explainable.png` | **以文搜图命中**：查询「夏天清爽的防晒霜」→ 命中 AST-007 相关度 43%，并回显命中词与字段（`防晒/防晒霜→tags,name,description`）；同义组归一让「防晒霜」命中只打了「防晒」标的素材 | 同上，`#search/<查询词>` |
| `p07-05-search-refused.png` | **拒答而非硬凑**：查询「库里没有的无人机航拍素材」→ 最高相关度低于阈值 0.18，返回 `refused=true` + 原因，列表为空 | 同上 |
| `p07-06-generate-card-saved.png` | **生成链路可跑 + 边界标注**：图片类型产出真实 PNG 文件（800×800，落 `data/uploads/`）、可直接预览、一键入库；页面与接口响应双处标注「程序化占位图，非 AI 出图」 | 同上，`#generate/<提示词>\|image` |
| `p07-07-report-with-p06-metrics.png` | **素材与投放效果关联报表** + **真实跨模块取数**：大盘对照区显示 P07 经 SERVICE_REGISTRY 解析端口后真实调用 `http://127.0.0.1:8060/api/v1/metrics/summary` 的结果（GMV 35958.37 / 转化率 0.0044% / 客单价 270.36 / UV 30410），并标注取数时间 | 同上，`#report` |
| `pytest-20261014.log` | 68 passed（改造前 18 passed）。覆盖：上传真实宽高与时间戳、MIME 文件头嗅探拒伪造、预览路由、删除连带文件、标签数组化、5 条中文自然语言查询命中、拒答、命中理由回显原词、打标 LLM/规则双分支与脏输出过滤、生成落库、投放漏斗校验（点击>曝光 → 422）、P06 可用性透传、ingest 白名单与令牌 | `cd projects/p07-ai-asset-center && .venv\Scripts\python.exe -m pytest tests -v` |
| `eval-search-20261013.json` / `.md` | 检索策略对比（26 条人工标注查询，12 条语料）：**新策略 Recall@5 1.0 / Precision@1 1.0 / MRR 1.0 / 拒答准确率 1.0**，平均 0.78ms、P95 0.87ms；**改造前 split+子串：Recall@5 0.05（19/20 条未命中）** | `.venv\Scripts\python.exe -u eval/search_eval.py` |
| `eval-tagging-20261013.json` / `.md` | 打标质量（12 条素材 × 人工标注概念）：**LLM 概念覆盖率 0.97 vs 词表规则 0.879**；真实 12 次网关调用、7963 tokens、0 次 mock、平均 7.4s/次（qwen3.8-flash）；另统计「字面无依据标签」16 个并说明处置方式 | `.venv\Scripts\python.exe -u eval/tagging_eval.py`（**会发出真实模型调用**） |

## 真实调用凭据与降级路径

- 模型：`shared/llm-gateway` → `token-plan.cn-beijing.maas.aliyuncs.com`，主用 `LLM_API_KEY` 在根 `.env` 中为空，
  解析器自动落到备用端点（`app/config.py::Settings.llm_endpoint`）。实测打标/文案均为真实返回（`source=llm`，非 mock）。
- 降级：凭证不齐或模型全部端点失败 → 打标退回词表规则并返回 `tag_source=rule` + `degraded_reason`；
  文案/脚本退回规则模板并返回 `source=rule` + `note`；P06 不可达 → 报表显示原因而不是编造大盘数字。
  降级分支由 `pytest` 打桩覆盖（测试进程不发真实请求）。

## Mock / 未做 / 未测量（诚实边界）

- **图片「AI 出图」未实现**：`generate` 的 image 分支是 Pillow 按投放规格绘制的占位卡片，接口 `note`、页面横幅、README 三处标注。
  端点 `/models` 里确有 `wan2.7-image`、`wan3.0-video`，但其调用接口形状（DashScope 异步任务 vs OpenAI 兼容）在本环境未验证 —— 未验证不宣称已跑通。
- **以文搜图仍是文本检索**，不是 CLIP 多模态向量检索；响应体 `engine` 字段与页面横幅都写明。
  真实向量方案未做评测：`EMBEDDING_MODEL` 在 token-plan 端点实测 404。
- **12 条 demo 素材的图是程序化演示图**（`source=demo`），不是真实商品图；演示数据边界在概览页脚注与 README 都写明。
- **P02 → P07 的推送尚未在 P02 侧接线**：P07 已提供 `POST /api/v1/ingest`（来源白名单 + 可选令牌），
  并有 `test_ingest_*` 与截图外的接口证据；P02 侧的「一键推送」仍是 P02 `AGENTS.md` 里未勾选的待办，本轮未改 P02。
- **P07 API 未接入统一鉴权**（读接口匿名可访问，写接口仅 ingest 有令牌），与 P06/P08/P09/P10 一致，属平台级待办，不是 P07 单独的坑。
- **未测量**：并发/压测（无 50 并发数据）、真实生产素材量级下的检索延迟（当前 0.78ms 是 12 条语料、本机进程内数字，不外推）、
  生成文案的投放效果增益（没有真实投放回流）。

## 历史

- `pytest-20261013.log`：改造前 18 passed（仅后端接口，前端无上传入口、无预览、无打标端点时的状态）。
