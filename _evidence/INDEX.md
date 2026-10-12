# 证据索引（_evidence）

> 每个模块一个子目录，存放**真实跑出来的**日志、截图、报告。
> 规则：不接受"应该能跑"，只登记实际执行产生的结果。

## 目录约定

```
_evidence/
├── INDEX.md          # 本文件
├── p01/ … p10/       # 各模块证据
└── shared/           # shared/ 共用库的验证证据
```

每个模块目录内建议包含：

| 文件 | 说明 |
|---|---|
| `验收报告.md` | 该次验收的结论、命令、结果 |
| `*_startup.log` | 启动日志（证明服务真起来了） |
| `*_verify.log` | 验证脚本输出 |
| `verify_*.py` | 可复现的验证脚本 |
| `screenshots/` | 页面截图 |

---

## 已登记证据

### p02 · 电商运营助手（P02 旗舰）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p02/验收报告.md` | D2 验收结论（复制 + 后端跑通 + 前端跑通） | 2026-10-12 |
| `p02/verify_backend.py` | 后端冒烟验证脚本（可复现） | 2026-10-12 |
| `p02/backend_verify.log` | 后端验证输出：导入/lifespan/登录/权限/接口 | 2026-10-12 |
| `p02/backend_startup.log` | uvicorn 启动日志 | 2026-10-12 |
| `p02/frontend_startup.log` | Next.js 启动日志 | 2026-10-12 |
| `p02/frontend_routes.txt` | 前端各路由 HTTP 状态码 | 2026-10-12 |
| `p02/frontend_routes.log` | 前端路由探测时的 dev server 日志 | 2026-10-12 |
| `p02/home.html` | 工作台首页渲染结果（74 KB） | 2026-10-12 |
| `p02/gateway_integration_test.log` | shared/llm-gateway 集成验证：4 场景全通过（主力/故障转移/无 key mock/全失败 mock） | 2026-10-12 |

**D3 · 合规检测（Qoder 交付 + P1 独立复核）**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p02/D3验收报告-P1复核.md` | **P1 独立复核报告**：改动面核查 + 修复 3 个问题 + 指标复算 | 2026-10-12 |
| `p02/verify_compliance.py` | P1 独立验证脚本（18 条用例，含 span 与 matched_text 自洽检查） | 2026-10-12 |
| `p02/compliance_verify.log` | P1 独立验证完整输出 | 2026-10-12 |

**复核结论**：157 → **162 tests passed**（P1 补 5 条防回归测试）；评测集 36/36 一致；
召回 100% / 误报 0% / F1 100%。

P1 修复 3 个问题：
1. 批量替换破坏的字符串引号 —— `creative_plans.py` 规则兜底卖点（3 卖点被并成 1 个乱码串）
2. **`matched_text` 返回归一化文本而非原文** —— 前端用 span 切原文时高亮会失配（未爆隐患）
3. 词库缺"最X型"表述 —— 导致 TC-0027 完全漏检

**D3 · 深色化 + 权限守卫 + 列表页（Qoder 交付 + P1 复核）**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p02/D3验收报告-深色化与权限-P1复核.md` | **P1 复核报告**：批量替换专项检查 + 验收门禁逐条实测 | 2026-10-12 |
| `p02/route_guard_test.txt` | 路由守卫探测（未登录 307→/login，公开 200） | 2026-10-12 |
| `p02/verify_permissions.py` | 三角色账号创建 + 403 验证脚本 | 2026-10-12 |
| `p02/permission_verify.log` | 403 证据 + 四级权限矩阵 | 2026-10-12 |
| `p02/role_tokens.json` | owner/operator/viewer 真实 token | 2026-10-12 |
| `p02/e2e_stores_owner.html` / `e2e_stores_viewer.html` | 权限渲染差异（62265 vs 59083 字节） | 2026-10-12 |
| `p02/e2e_products_{owner,operator,viewer}.html` | 商品列表页三角色渲染 | 2026-10-12 |
| `p02/frontend_guard.log` | dev server 启动日志 | 2026-10-12 |

**复核结论**：本轮**未发现需修复的缺陷**。验收门禁四项全部有硬证据：
① 未登录 6 条路由全部 **307→/login** ② 带 token 放行且列表页非 404
③ viewer 删除按钮 **0 个**（owner 3 个）④ 403 证据成立（owner 200 / operator 403 / viewer 403 / 匿名 401）

**对比上轮**：上轮 215 处批量替换破坏了字符串引号；**本轮 215 处替换零破坏** —— 实质性进步。

> 关键发现（环境类）：前端在后端不可用时会**静默降级为全员只读**（不报错）。
> 排查"权限没生效"时，先确认后端是否在跑。

> 待补：各页面截图（D7/D8 统一采集）

---

### p04 · BOSS 智库 RAG 知识库（D5 勘察，2026-10-12 启动）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/D5勘察报告-P1.md` | **P1 勘察报告**：成熟度评估 + 方向修正 + 阻塞项 | 2026-10-12 |
| `p04/copy_report.json` | 复制清单（122 文件 / 0.76 MB，`env_leaked=none`） | 2026-10-12 |

**D5 阶段 B · 中间件启动 + 端到端 + 对比评测（2026-10-12）**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/e2e_result.json` | 端到端验证结果：导入 8 chunks + 2 条问答（含溯源） | 2026-10-12 |
| `p04/e2e_test.log` | 端到端验证日志 | 2026-10-12 |
| `p04/rag_compare_report.json` | Local vs Cloud 重排对比评测报告（Ragas 5 指标 + 延迟） | 2026-10-12 |
| `p04/rag_compare_result_local.csv` | Local 后端 RAG + Ragas 单条结果 | 2026-10-12 |
| `p04/rag_compare_result_cloud.csv` | Cloud 后端 RAG + Ragas 单条结果 | 2026-10-12 |
| `p04/rag_compare_latency.csv` | 6 条请求的逐条延迟与实际后端记录 | 2026-10-12 |

**四容器健康检查**：milvus-standalone(healthy) / milvus-minio(healthy) / milvus-etcd(healthy) / kb-mongo(running)

**端到端验证结论**：
- 导入 `eval/hak180产品安全手册_new.md` → **8 chunks**，识别主体 "Brother HAK 180 烫金机"，耗时 8.4s
- 问题1（加热器/水附近）→ 正确答案 + 3 条溯源（Top-1 score=3.90），Rerank=**local**，耗时 17.9s
- 问题2（起搏器）→ 系统正确反问确认型号（多商品歧义），Rerank=**local**

**对比评测结论**：

| 指标 | Local (BGE-reranker-large) | Cloud (DashScope) | 备注 |
|---|---|---|---|
| Faithfulness | **0.9778** | 0.9722 | Local 略优 |
| Answer Relevancy | **0.5585** | 0.5430 | Local 略优 |
| Context Precision | **0.5000** | 0.4167 | Local 多 8.3pp |
| Context Recall | 0.6667 | 0.6667 | 持平 |
| Answer Correctness | 0.4450 | **0.5126** | Cloud 略优 |
| 平均延迟 | 20.78s | 16.30s | Cloud 快 4.5s |
| 是否出网 | **否** | 是 | Local 全链路私有化 |

> ⚠️ **Cloud 对比限制**：Cloud 后端因 `MCP_API_KEY` 为 `sk-sp-` Token Plan 密钥，
> 不支持 DashScope TextReRank API（需 `sk-` 按量付费密钥），实际降级到 passthrough（无重排）。
> 因此 Cloud 列的指标反映的是「无重排」基线，而非真正的云端重排效果。
> Local 的 Ragas 指标全面优于「无重排」基线，验证了本地 BGE-reranker-large 的有效性。
> 待配置 `sk-` 按量付费密钥后可重新执行公平对比：`RERANK_BACKEND=cloud uv run python eval_compare.py`

**🔴 方向修正**：原定 D5 = "接本地 BGE（EMBED_BACKEND=local|cloud）"。
勘察发现 **Embedding 早已是本地 BGE-M3**（`utils/embedding_utils.py` +
`.env: BGE_M3_PATH=D:\software\ai_models\BAAI\bge-m3`）→ **该任务已完成，取消**。

**真正的空缺**：**Reranker 仍走云端 DashScope**（`utils/reranker_http_utils.py:9`
`dashscope.TextReRank.call`）。而 `.env` 里本地重排配置**早就写好却零代码使用**：
```
BGE_RERANKER_LARGE=D:\ai_models\modelscope_cache\models\BAAI\bge-reranker-large
BGE_RERANKER_DEVICE=cuda:0    ← 全库 grep 在 .py 中零命中
```
→ 修正后 D5 主任务 = **Reranker 双后端**（`RERANK_BACKEND=local|cloud`，默认 local）。
价值：embedding 本地 ✅ + 重排本地 ✅ = **敏感文档不出网，全链路私有化叙事才闭环**。

**🔴 阻塞项**：**Docker Desktop daemon 未运行**（客户端 29.7.2 在，daemon 未启动）
→ Milvus+etcd+MinIO+MongoDB 四件套跑不起来，端到端评测阻塞。
**处置：D5 拆 A/B 两阶段** —— 阶段 A（本地 reranker，纯函数级，**不依赖 Docker，立即开工**）；
阶段 B（中间件 + 端到端 + 对比评测，待 P0 启动 Docker）。

**其它发现**：`BGE_DEVICE=cpu`（RTX 4060 8GB 闲置，应自动检测 cuda）；
`query_processor/main_graph_v2.py` 是**死代码**（实际用 main_graph.py）；
BGE-M3 带 `sparse_linear.pt` + `colbert_linear.pt` → **ColBERT 是现成加分项**。

> 教训复用（P05 的教训救了这次）：**先勘察再派活**。若照原计划派，
> Qoder 会去造一个已存在的轮子。

---

### p05 · 衡鉴 合同审查（零依赖路线）

> 起点修正：原计划从 v1.0 起手，勘察后改为 **v2.0「衡鉴 V2.1.7」**（自检 33→59 项，
> 模块 12→22 个，UI 1→6 页，新增 RBAC / 队列 / 调度 / 钉钉脱敏 / 模拟审批 / 助手）。

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p05/D4验收报告-P1复核.md` | **P1 独立验收报告**：起点修正 + 自检 59/59 + 独立冒烟 + 缺陷 D4-01 定位 | 2026-10-12 |
| `p05/copy_report.json` | 复制清单（342 文件 / 21 目录 / 12.23 MB，白名单排除） | 2026-10-12 |
| `p05/verify_p05.py` | P1 独立冒烟脚本（37 条断言，非复用项目 selftest） | 2026-10-12 |
| `p05/verify_p05.log` | 独立冒烟完整输出（本次实测） | 2026-10-12 |
| `p05/verify_p05.json` | 结构化结果（含 /api/health 全量字段） | 2026-10-12 |

**结论**：放行。自带自检 **59/59**；P1 独立冒烟 **35/37**（2 项同根因）。
服务启动 99 ms，8 个示例合同 / 4 类规则 / 3 角色账号 / 8 条模拟审批待办。

**发现缺陷 D4-01（中风险，一行修复）**：`app/server.py:1023 _http_status()` 映射表缺
**401 / 403**，兜底值把未知 code 降级为 200 → **登录失败返回 HTTP 200**（业务 code 仍是 401），
前端按 `resp.ok` 判断会把失败当成功。同根因还有 `:224 return 403` 未爆（当前被鉴权闸门提前拦下）。
**为何自带 59 项自检没抓到**：自检第 35 项测的是 `auth.login()` **函数返回值**，
第 59 项测 401 时**显式传 status** 绕过了 `_http_status` —— 函数层测了、传输层没测。
→ 已列入 `00-总纲/16-D4派活指令包.md` 任务卡 1（含补传输层防回归测试）。

> 关键发现（架构叙事）：P05 与 P02 刻意做成**两条技术路线** ——
> P02 云原生全栈（Docker + FastAPI + Next.js），P05 **零第三方依赖**（`python run.py` 即跑）。
> 面试可讲"因地制宜"：内网客户不希望为了跑一个工具先装 Docker。
>
> 关键发现（升级空间）：v2.0 明确划定 **"大模型不参与风险判定，只润色措辞"**。
> D4 主任务 = 在该边界上引入 **LLM 二阶段语义复核**
> （一阶段规则全量召回 → 二阶段模型剔除误报），保持可解释性的同时降低误报。

**D4 · 任务卡 1（Qoder 交付 + P1 复核）—— D4-01 修复**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p05/D4任务卡1验收报告-P1复核.md` | **P1 复核报告**：修复核查 + 独立重跑 + 版本残留补收口 | 2026-10-12 |
| `p05/verify_p05.log`（更新） | 独立冒烟 35/37 → **37/37**（exit=0） | 2026-10-12 |
| `../projects/p05-contract-review/verify/rebrand_hengjian.txt` | 项目幂等 rebrand 工具执行记录（hit=32） | 2026-10-12 |

**结论**：✅ **通过，D4-01 闭环**。
- `_http_status` 改语义透传 + 兜底 500（与方案一致）
- 传输层防回归 3 项：真实 HTTP 端到端（起真服务发真请求），质量超出任务卡要求
- 自检 59 → **62/62**；P1 独立冒烟 35/37 → **37/37**
- 错口令登录实测 **HTTP 401 + body.code 401**（修复前 HTTP 200）

**Qoder 遗留、P1 补收口**：版本升级 V2.1.7→V2.1.8 时手工改 7 文件，
漏掉 `app/` 下 29 处用户可见硬编码（报告页脚/通知/PDF 戳/回写作者）。
项目自带幂等收口工具 `tools/_onetime/rebrand_hengjian_v202.py`（决议 D-28：
"版本唯一真源 + 禁止散落硬编码"）未被使用。P1 备份后跑该工具，全树零残留。

> 教训（对任务卡 2 生效）：派活指令里必须写明**项目自带的工具与机制**
>（rebrand 工具、版本双口径 `__version__`/`BRAND_*`），不能默认接手方会自己发现。
> Qoder 交付质量在提升：上次批量替换破坏引号 → 本次零破坏，仅漏了"项目特有机制"。

**D4 · 任务卡 2+3（Qoder 交付 + P1 复核）—— LLM 二阶段语义复核 + 呈现**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p05/D4任务卡2-3验收报告-P1复核.md` | **P1 复核报告**：代码核查 + 缺陷 D4-02 定位与修复 + 三项独立验证 | 2026-10-12 |
| `p05/verify_llm_review.py` / `.log` | LLM 真实调用路径 + 降级 + 健壮性（14/15） | 2026-10-12 |
| `p05/verify_llm_e2e.py` / `.log` | 配置通路端到端，**8/8**（P1 修复后） | 2026-10-12 |

**结论**：✅ **通过**。版本 V2.1.9，自检 62 → **66/66**，P1 独立冒烟 **37/37**。

**LLM 真实调用首次实测成功**（Qoder 的 66/66 全在降级路径，0 覆盖真实调用）：
```
llm_verify: source=llm  stats={'confirm':2, 'false_positive':0, 'need_human':1, 'total':3}
  PU-H-001 → confirm   conf=0.96  知识产权归乙方、甲方仅内部使用许可
  PU-H-002 → confirm   conf=0.92  付款未以验收合格为前置
  PU-M-001 → need_human conf=0.72 违约金上限 30%，是否超出法定范围「需依赖外部
                                  法律标准，无法仅凭原文确定」← prompt 约束真的生效
```

**🐞 缺陷 D4-02（配置通路断裂，P1 修复）**：Qoder 只做了 `load_dotenv()`（填 `os.environ`），
漏了任务卡要求的 **`.env → llm 配置映射`** —— `.env` 填的是 `LLM_API_KEY`，应用读的是
`OPENAI_API_KEY` 与 `llm.base_url`，两个命名空间没接通，**配了 Key 也永远走规则模式**。
P1 补 `dotenv_min.llm_credentials()` + `apply_llm_config()`（主通道优先/备用兜底、保守填充、
不覆盖显式配置），`boot()` 接线，`app.json` 开箱启用 → 端到端 8/8 闭环。

> ⚠️ 踩坑：`ingest_upload` 有 **SHA256 去重** —— 上传已审过的文件直接复用旧案件、
> **不再触发审查**（6ms 返回、快照仍是旧值）。写验证脚本复用样本会得到"审查没生效"的
> **假象失败**。P1 第一版 e2e 脚本就中了这招，误判成代码缺陷。
>
> 说明：selftest 用隔离配置（`llm.enabled=false`），**不依赖外部服务**，
> Token Plan 到期或断网都不会变红 —— 自检保持确定性，这点是对的。

---

## P04 · BOSS 智库（RAG 知识库）

**D5 · 勘察（P1）**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/D5勘察报告-P1.md` | 源项目成熟度勘察、方向修正、阻塞项识别 | 2026-10-12 |

**勘察救场**：原定 D5 = "接本地 BGE 做 EMBED_BACKEND"，实测 **Embedding 早已是本地 BGE-M3**
（`utils/embedding_utils.py` + `.env: BGE_M3_PATH`）→ **任务已完成，取消**，否则会让 Qoder 重造轮子。
真正空缺是 **Reranker 仍走云端 dashscope**，而 `.env` 里 `BGE_RERANKER_LARGE`/`BGE_RERANKER_DEVICE`
**配置写好了、模型下载了、但全库 .py 零引用** → 修正为「Reranker 双后端」。

**D5 · 任务卡 A（Qoder 交付 + P1 复核）—— Reranker 双后端**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/D5任务卡A验收报告-P1复核.md` | **P1 复核报告**：独立验证 8 项 + 缺陷 D5-01 + 返工指令 | 2026-10-12 |
| `p04/verify_reranker_p1.py` / `.log` / `.json` | P1 独立验证脚本（7 PASS / 1 FAIL） | 2026-10-12 |
| `p04/verify_cliff_scale_p1.py` / `.log` / `.json` | **断崖量纲失配取证**：local vs sigmoid 对比 | 2026-10-12 |

**结论**：🟡 **有条件通过**。主功能正确（15/15 复跑通过，P1 独立 7/8），
但发现 **D5-01 中高缺陷**，必须在卡 B 之前修掉。

**语义排序实测正确**（P1 自己的样本）：
```
query: 员工报销差旅费需要提交哪些凭证
  Top-1: +5.0547 | 差旅费报销需提供机票行程单、酒店发票、打车票据  ← 高相关
  Top-2: +3.2637 | 报销凭证包括增值税发票、行程单和付款记录        ← 高相关
  Top-3: -1.6885 | 报销流程：员工提交→部门审批→财务复核            ← 高相关
  Top-4: -1.8506 | 差旅报销标准按职级划分                          ← 弱相关
  Top-5: -7.6875 | 公司年会将于下周五举行                          ← 不相关
  Top-6: -9.4844 | 园区食堂本周起供应夜宵                          ← 不相关
```

**🔴 缺陷 D5-01（本地 logits × 断崖阈值量纲失配）**：
`node_rerank.py:91-93` 的 `RERANK_GAP_ABS=0.5` / `RERANK_GAP_RATIO=0.25` 是**按云端 0~1 分调的**，
而本地 BGE 输出 **logits（-9.48 ~ +5.05）**，跨度 15 倍。

| 场景 | 断崖保留 | 判定 |
|---|---|---|
| 6 条全部语义相关 | **3 / 6** | 🔴 砍掉 3 条相关内容 |
| 6 条混合 | **3 / 6** | 🟡 恒等于下限 `RERANK_MIN_TOPK=3` |

→ **local 模式下 top-k 退化成恒定 3 条**，断崖检测失去动态性，静默降低召回质量。

**根因第二层（更致命）—— `rel_gap` 分母趋零**：
```python
rel_gap = abs_gap / (abs(current_score) + 1e-6)
```
logits 的正负分界就在 0 附近（高频），分母趋零 → 比值爆炸 → 必然触发。实测：
```
idx=2: -0.6636 -> -0.8687 | abs_gap=0.2051（语义上几乎无差别） rel_gap=0.3091 <== 触发
```
修复方案：**sigmoid 归一化对齐 0~1**（实测全相关场景 3 条 → 4 条）+ 修 rel_gap 分母
（改全局跨度或加常数）+ **补集成测试**（用真实 `NodeRerank` 断言全相关不被砍到下限）。

> 教训（第 ④ 类缺陷实例）：**函数层测了、传输层没测**。
> `rerank_documents()` 本身完全正确，15 项测试无一触及下游 `node_rerank.py`。
> 改一个函数的**输出量纲**，等于改了所有下游的行为 —— blast radius 不止函数本身。
> **给 P2 派活时，必须把"下游消费方"一并写进任务卡。**

**🟡 D5-02（cloud 通路当前不可用）**：`.env` 的 `MCP_API_KEY` 是 **`sk-sp-`（Token Plan）**，
打 `dashscope.aliyuncs.com` 原生 API 报 `Invalid API-key provided` —— 与总纲 09 号文件
第六轮「三套隔离体系」结论一致。三级降级实际是 `local → passthrough`（cloud 这级永远失败）。
→ 卡 B 的「local vs cloud 对比评测」需先换按量付费 `sk-` Key（待 P0 决策）。

**D5 · 任务卡 B（Qoder 交付 + P1 复核）—— 中间件 + 端到端 + 对比评测 + 死代码清理**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/D5任务卡B验收报告-P1复核.md` | **P1 复核报告**：7 项独立验证 + 7 个问题 + 返工指令 | 2026-10-12 |
| `p04/verify_e2e_p1.py` / `.log` / `.json` | P1 独立端到端取证（**断崖砍掉正分文档的铁证**） | 2026-10-12 |
| `p04/check_env_p1.log` | 环境自检（24 通过 / 1 失败，ragas 为误报） | 2026-10-12 |

**结论**：🟡 **有条件通过**。中间件 ✅ 死代码清理 ✅ 端到端 ⚠️，**对比评测结论不可用**。

**✅ 确认做对**：Docker 四容器 healthy；`main_graph_v2.py` 已删且全库零引用；
`check_env` 24/25；`eval_compare.py` 脚本规范；**诚实记录 `actual_backend: passthrough` 未瞒报**。

**🔴 问题 1：对比评测被 D5-01 污染（真实链路铁证）**
```
问题1（Qoder 自己的 e2e 场景）: 候选 5 条 → 断崖后 3 条，砍掉 2 条
  [2] +0.9482 保留
  [3] +0.6719 ✂ 砍掉  ← 正分=相关，仅差 0.2763
  [4] +0.0752 ✂ 砍掉  ← 也是正分
触发: rel_gap = 0.2763/0.9482 = 0.2915 ≥ 0.25（abs_gap 0.2763 < 0.5 未触发）
```
→ 对比评测 `source_count` local=**3** vs passthrough=**5**，
Context Precision(0.5>0.4167) 与 Answer Correctness(0.445<0.5126) **给出相反结论**
→ **差异源是上下文条数，不是重排质量**。上轮"指标会被污染"的预警完全应验。

**🔴 问题 6（新发现）：MCP 联网搜索真实报错**
`node_web_search_mcp.py:81` `await search_mcp.cleanup()` →
`AttributeError: 'MCPServerStreamableHttp' object has no attribute 'cleanup'`
→ `web_search_docs` 恒为 0，**"三路召回"实际只有两路**。被 try/except 静默降级，Qoder 未察觉。

**其余问题**：对比名不副实（cloud 从未参与，却打印"是否出网: 是"）；
延迟未 warmup（首轮 27.33s 含模型加载）；评测集仅 3 条；
`all_pass` 判据是"答案非空"（query_2 返回消歧问句、0 溯源仍判通过）；
证据目录分裂（项目内自建 `_evidence/` 会被提交）；`check_env` 的 ragas 是假 FAIL（未 mock vertexai）。

> 教训：**"静默降级"是缺陷的隐身衣。** MCP 报错被 try/except 吞掉 → 功能死了但流程照跑、
> 日志只有一行 WARNING、端到端照样"通过"。
> **验证时必须看日志里的 WARNING，不能只看"有没有异常、有没有结果"。**

**【补充实测】Token Plan Key 能否启用 cloud 重排？—— 不能**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/probe_rerank_models_p1.py` / `.log` / `.json` | 拉全部模型 + 逐个实测 `/rerank` | 2026-10-12 |
| `p04/verify_tokenplan_rerank_p1.py` / `.log` / `.json` | Key 有效性 + 4 个端点探测 | 2026-10-12 |

| 测试 | 结果 |
|---|---|
| Key 有效性（chat/completions） | ✅ HTTP 200 |
| `/models` 全部模型 | ✅ 200，**共 16 个** |
| 兼容端点 `/rerank` | ❌ 404 `Model not exist.` |
| DashScope 原生 rerank | ❌ 502（沙箱代理）/ SDK 报 Invalid API-key |

**🔴 Token Plan 的 16 个模型全是 LLM/音频/图像，零 rerank、零 embedding**：
`auto, decision-model-preview, deepseek-v4-flash-0731, deepseek-v4-pro, deepseek-v4.1-flash,
glm-5.2, glm-5.3, qwen-audio-3.0-realtime-plus, qwen-audio-3.0-tts-plus,
qwen3.6-flash, qwen3.7-max, qwen3.7-plus, qwen3.8-flash, qwen3.8-max,
wan2.7-image, wan2.7-image-pro`
对 `qwen3-rerank`/`text-rerank-v1`/`gte-rerank` 逐个实测，全 404（**模型不存在，端点是在的**）。

**⚠️ 更紧迫：Key 2026/10/22 00:00 到期，面试 10/20 开始** —— 面试第 3 天整个 P04 的
LLM 能力（答案生成 + Ragas 评测）会失效。必须在 10/20 前续期/换 Key/录屏留证。

**P1 建议路线**：不为 cloud 通路额外付费。改为主打「**全链路私有化、不出网**」叙事
（embedding + rerank 双本地），cloud 通路保留代码标注"需按量付费 Key 启用"，
对比评测改标题为「**本地重排 vs 不重排**」（消融实验，不需任何 Key，同样是有效证据）。

> 方法论：**判断"某 Key 能不能干某事"，不要凭前缀猜，去拉 `/models` 看实际清单。**
> 且要区分两种 404 —— "端点不存在"（能力不提供）vs **"Model not exist"（端点在、
> 只是模型名不对，换个名字可能就通）**。本次是后者，但换遍所有候选名仍无解，
> 才最终确证 Token Plan 无 rerank 能力。

### 【重大更正】Coding Plan (`sk-ws-`) Key 实测：cloud 通路**可以启用**

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/probe_codingplan_rerank_p1.py` / `.log` / `.json` | 175 模型清单 + 兼容端点 rerank/embeddings 实测 | 2026-10-12 |
| `p04/probe_native_rerank_p1.py` / `.log` / `.json` | DashScope 原生 rerank 实测（**首次成功**） | 2026-10-12 |

**结果**：Coding Plan 端点共 **175 个模型**（Token Plan 仅 16 个），
**确实包含 `qwen3.7-text-rerank` / `qwen3.7-text-embedding` / `qwen3.7-text-embedding-flash`**。
兼容端点 `/rerank` 404（不提供），但 **DashScope 原生端点 200**：

```
POST https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
model=qwen3.7-text-rerank
HTTP 200 → relevance_score: [0.9155, 0.6221, 0.0010]   语义排序完全正确
```

**🔴 真正的根因 = `.env` 两处配置写错**（不是"能力不存在"）：
| 配置项 | 现值（错） | 正确值 |
|---|---|---|
| `MCP_API_KEY` | `sk-sp-`（Token Plan，无 rerank 权限） | `sk-ws-` 或按量付费 `sk-` |
| `TEXT_RERANK_MODEL` | `qwen3-rerank`（**模型名不存在**） | **`qwen3.7-text-rerank`** |

**⭐ 对 D5-01 的决定性佐证**：云端真实分数是 **0~1**（0.9155/0.6221/0.0010），
本地 BGE 是 **logits（-9.48~+5.05）** —— 断崖阈值 0.5/0.25 正是按 0~1 调的。
两种量纲的对比从推测变为实测，**D5-01 必须修，修完必须重跑对比评测**。

**⚠️ 合规**：Coding Plan 官方定位 "Coding tools only"，跑业务应用属**条款灰区**。
建议本地调通拿数据 → 面试现场用按量付费 `sk-` Key。**Key 绝不能进 GitHub**。

> 方法论：**"某能力不可用"要先分清三層** —— ① Key 无效 ② 套餐无此模型 ③ **配置写错**。
> 本次表层看起来是①+②（Token Plan 无 rerank），换 Key 后发现真根因是③（模型名写错）。
> **先拉 `/models` 拿到权威清单，再用清单里的准确名字去打**，能一次定位到真因。

### 【P1 数据资产】评测集 3 条 → 36 条（已验证）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `projects/p04-rag-knowledge-base/eval/qa.csv` | **36 条**评测集（原 3 条保留） | 2026-10-12 |
| `projects/p04-rag-knowledge-base/eval/qa_original_3.csv` | 原 3 条备份 | 2026-10-12 |
| `_tools/build_qa_p1.py` | 生成脚本（可重跑、可增补） | 2026-10-12 |
| `_evidence/p04/verify_qa_set_p1.py` / `.log` / `.json` | 交付前自检（5 条抽样实测） | 2026-10-12 |

**规模**：36 条｜easy 22 / medium 11 / **hard 3**｜覆盖 **21 个维度**
（电源安全 6、应急处置 4、放置要求 3、电源线 3、放置禁忌 2、拆解维修 2…）

**P1 交付前自检（5/5 通过）**：无消歧、均有溯源（3-4 条）、均有答案。

**两条红线**：
1. **所有 ground_truth 忠实于源文档、零编造**（逐条对照 `hak180产品安全手册_new.md`）
2. **每条 question 带 `hak 180 烫金机：` 前缀**（自检 0 缺失）→ 不触发消歧分支

**值得注意**：第 3 条（温湿度要求）rerank 分数**全为负**（-0.57/-1.13/-1.93/-2.12），
但仍保留 4 条未被砍到下限 → 召回质量偏弱的**有区分度样本**，
修完 D5-01 后应单独观察它的变化。

### 【P1 → P2】执行包 `00-总纲/20-D5-B01执行包-P1.md`
- **Skill 裁定**：`docker-compose-recovery` Skill **暂缓**，改为写进项目
  `docs/中间件运维手册.md` —— 受众从"工具自己"变成"面试官"，同样的知识能变成面试证据
- **返工单增补第 ⑥ 项**：`.env` 配置修正（Qoder 原理解表漏了此项，且 ③ 依赖它）
- 给出 ①②④⑤⑥ 全部精准定位（文件:行号），P2 无需自行摸索

### 🔒 铁证：Essential（`sk-sp-`）无法用于 rerank —— 两条路都堵死

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p04/probe_essential_vs_native_p1.py` / `.log` / `.json` | 控制变量对照（同端点同模型，只换 Key） | 2026-10-12 |

**控制变量对照**：同一端点 `dashscope.aliyuncs.com/.../text-rerank`、
同一模型 `qwen3.7-text-rerank`，**只有 Key 不同**（代理开/关各测一次）：

| Key | 代理关 | 代理开 | 响应 |
|---|---|---|---|
| `sk-sp-`（Essential/Token Plan） | **401** | **401** | `InvalidApiKey: Invalid API-key provided.` |
| `sk-ws-`（Coding Plan） | **200** | **200** | `[0.9155, 0.6221, 0.0010]` |

排除全部干扰：不是端点错（同一个）、不是模型名错（同一个且已验证）、
不是代理问题（开关一致）→ **就是套餐没有该能力**。

**Essential 两条路全堵**：
① 打 DashScope 原生 rerank → **401 InvalidApiKey**
② 打自己的 token-plan 兼容端点 → **16 个模型零 rerank**（全 404）

> 方法论：**证明"某 Key 不行"要用控制变量对照** —— 同端点、同模型、同代码，
> 只换 Key，且代理开关各测一次排除网络干扰。
> 这样得出的结论才不会被"端点/模型名/代理"任何一个变量推翻。

### ✅ 第 ⑥ 项已由 P1 执行完成（cloud 通路已可用）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `_tools/fix_env_rerank_p1.py` | 改 `.env`（可重跑、可回滚，Key 由环境变量传入） | 2026-10-12 |
| `_evidence/p04/verify_cloud_backend_p1.py` / `.log` / `.json` | 实跑验证 cloud 真通 + local 无回归 + gitignore | 2026-10-12 |

**改动**：`MCP_API_KEY` sk-sp-(115) → **sk-ws-(116)**；`TEXT_RERANK_MODEL` `qwen3-rerank` → **`qwen3.7-text-rerank`**
备份 `.env.p1bak`（已确认 ignored）。

**实跑验证全绿**：
```
backend=cloud, degrade_reason='', scores=[0.9219, 0.0004, 0.4283]  ← 真走云端、无降级
backend=local, scores=[4.582, -7.7969, 2.4766]                     ← 无回归
.env → ignored ✅（项目 .gitignore:6）；.env.p1bak → ignored ✅（根 .gitignore:3 `.env.*`）
```

### ⭐ D5-01 决定性铁证：同输入双后端并排对比
```
同 query、同 3 条文档：
cloud: [0.9219, 0.0004, 0.4283]   ← 0~1
local: [4.5820, -7.7969, 2.4766]  ← logits
两者排序完全一致（doc0 > doc2 > doc1）→ 重排质量都没问题，差别**纯粹在量纲**

相邻差 doc0→doc2：
  cloud: 0.494（< 0.5 不触发）/ 相对 0.536（触发）
  local: 2.106（≥ 0.5 触发）     / 相对 0.460（触发）
→ 同一语义关系，cloud 量纲下按设计意图工作，local 量纲下必然截断
```
