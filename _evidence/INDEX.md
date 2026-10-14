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

> ⚠️ **这条结论原先只有数字、没有日志**（P02 是十个模块里唯一没有 pytest 运行记录的）。
> 2026-10-13 23:52 在 `api/` 内用 `.venv/Scripts/python.exe -m pytest tests -v` 真实重跑复核：
> **162 passed / 0 failed / 24.13s**，与结论一致。完整输出归档到
> `p02/pytest-20261013.log`，跑法/隔离方式/未测量项登记在 `p02/INDEX.md`。
> 未测量：覆盖率（无 coverage 插件）、前端套件（不存在）、门禁「部署上线可访问」（无公网入口）。

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
| `p04/rag_compare_report.json` | **Local vs Cloud 重排对比评测报告（36 条评测集，Ragas 5 指标 + 延迟）** | 2026-10-12 22:08 |
| `p04/rag_compare_result_local.csv` | Local 后端 RAG + Ragas 单条结果 | 2026-10-12 |
| `p04/rag_compare_result_cloud.csv` | Cloud 后端 RAG + Ragas 单条结果 | 2026-10-12 |
| `p04/rag_compare_latency.csv` | **72 条请求**（36×2 后端）的逐条延迟与实际后端记录 | 2026-10-12 |
| `p04/eval_compare_run.log` | 对比评测完整运行输出（2.1 MB） | 2026-10-12 |
| `p04/verify_eval_compare_p1.py` / `_out.txt` | P1 独立复核脚本与输出 | 2026-10-12 |
| `p04/stream-query-evidence.log` | **端到端流式问答真实证据**（317 个 SSE 事件 + 4 条引用） | 2026-10-13 21:18 |
| `p04/verify-cascade-delete.log` | 删除重建/级联清理验证 | 2026-10-13 21:17 |
| `p04/console-tab-{upload,docs,dashboard,qa}.png` | 管理后台四个页签真实渲染截图 | 2026-10-13 21:16 |
| `p04/_archive_D5-01_baseline/` | **已废弃的 3 条样本基线**（Key 未通、Cloud 降级 passthrough 那一版） | 2026-10-12 |

> ⚠️ **登记修正（2026-10-13 深夜复核）**：本表原先列的 `p04/e2e_result.json` **文件不存在**、
> `p04/e2e_test.log` **是 0 字节空文件**（10-13 10:56 被清空），却写着"端到端验证结果"。
> 现改为指向上面真实存在的流式问答与级联删除证据。空日志留在目录里仅作故障记录，不再当证据引用。

**四容器健康检查**：milvus-standalone(healthy) / milvus-minio(healthy) / milvus-etcd(healthy) / kb-mongo(running)

**端到端验证结论**：
- 导入 `eval/hak180产品安全手册_new.md` → **8 chunks**，识别主体 "Brother HAK 180 烫金机"，耗时 8.4s
- 问题1（加热器/水附近）→ 正确答案 + 3 条溯源（Top-1 score=3.90），Rerank=**local**，耗时 17.9s
- 问题2（起搏器）→ 系统正确反问确认型号（多商品歧义），Rerank=**local**
- 2026-10-13 重采：一次真实问答收到 **317 个 SSE 事件**、回答带 **4 条引用**（`stream-query-evidence.log`）

**对比评测结论（36 条评测集，两侧 `actual_backend` 均为真实后端，`degrade_notes` 为空）**：

| 指标 | Local (BGE-reranker-large) | Cloud (DashScope qwen3.7-text-rerank) | 备注 |
|---|---|---|---|
| Faithfulness | 0.9651 | **0.9777** | Cloud 高 1.3pp |
| Answer Relevancy | 0.8152 | **0.8178** | 基本持平 |
| Context Precision | 0.6810 | **0.9190** | Cloud 多 23.8pp |
| Context Recall | 0.8681 | **0.9583** | Cloud 多 9.0pp |
| Answer Correctness | 0.6900 | **0.7217** | Cloud 高 3.2pp |
| 平均延迟 | 51.37s | **18.69s** | Cloud 快 2.75× |
| 是否出网 | **否** | 是 | Local 全链路私有化 |

> **结论与早期版本相反**：Cloud 侧 Key 换成 `sk-ws-` 免费工作空间端点、重排真正生效后，
> **五项 Ragas 指标全部优于 Local，且延迟只有本地的 1/2.75**；Local 唯一保留的优势是
> **不出网（全链路私有化）**。早期"Local 略优"的说法来自 3 条样本 + Cloud 降级成 passthrough
> 的基线（已归档在 `p04/_archive_D5-01_baseline/`），不能作为结论对外讲。
>
> **仍未满足的门禁项**：① 规则 04 要的**拒答率**在 `eval/eval.py` 里根本没有计算
> （只有 faithfulness / answer_relevancy / context_precision / context_recall / answer_correctness）；
> ② **父子分块 vs 定长分块的策略对比实验从未做过**（分块只有一种长度配置）。


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

---

## D6 · 全模块批量推进（2026-10-12 晚）

### P02 · 四角色 RBAC + 合规评测（Qoder 自主完成）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p02/rbac_四角色验证报告.md` | 四角色权限矩阵 + 403 证据 + 代码变更清单 | 2026-10-12 |
| `p02/合规评测报告.md` | 36 条评测集：准确率 100%、高危拦截 100%、误报 0%、绕过 0% | 2026-10-12 |

**变更摘要**：
- UserRole 枚举从 3 角色扩展为 4 角色：OWNER/OPERATOR/DESIGNER/CS
- 新增 `require_owner_permission` 依赖 + `/api/v1/dashboard/overview` 老板看板端点
- CS 角色访问老板看板返回 **HTTP 403**（已验证）
- 前端导航按角色过滤 + 角色徽章展示
- 4 个演示账号：boss/ops/design/cs@cloudpivot.com

### P01 · AI 客服（从源项目复制）

- 源项目：`D:\software\PycharmProjects\customer-service-backend\`
- 状态：已复制、README 重写、start.bat 修复
- 技术栈：FastAPI + LangChain + Vue 3 + MySQL

### P03 · Deep Research（从源项目复制）

- 源项目：`D:\software\PycharmProjects\deep_agent_search\`
- 状态：已复制、pyproject.toml 更新、README 重写
- 技术栈：DeepAgents + LangChain + Vue 3 + MySQL

### P04 · RAG 知识库（深色主题转换）

- 3 个 HTML 页面（console/chat/import）全部从浅色转为深色主题
- 设计令牌与 P02 统一：bg #0B0E14, surface #141820, accent #3370FF
- highlight.js 主题从 github → github-dark

### P05 · 合同审批（验证通过）

- 66/66 项自检全部通过
- 状态：生产级，无需修改

### P07 · AI 素材中心（从零构建）

- 完整 FastAPI 后端 + 深色主题单页前端
- 12 个演示素材 + 7 条投放效果关联
- 以文搜图（TF-IDF mock）+ AI 生成（mock）
- Mock 边界在 UI 和 README 双处标注

### P08/P09/P10 · 构建中（Agent 执行）

- P08 直播切片、P09 销售考核、P10 微调平台正在由后台 Agent 构建

### Shell + 门户

- `shell/index.html`：统一工作台入口，iframe 挂载各模块
- `01-portfolio/index.html`：深色主题作品集门户，展示十大模块

---

## D7 · 全服务验证（2026-10-12 深夜）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `D7-全服务验证报告.md` | 10/10 模块端口映射 + curl 验证 + 修复记录 | 2026-10-12 |

**10/10 服务全部运行中**：

| 模块 | 端口 | 状态 |
|---|---|---|
| P01 AI客服 | 18082 | ✅ |
| P02 运营助手 | 8000+3001 | ✅ |
| P03 Deep Research | 8030 | ✅ |
| P04 RAG知识库 | 8041 | ✅ |
| P05 合同审批 | 8770 | ✅ |
| P06 数据中台 | 8060 | ✅ |
| P07 素材中心 | 8070 | ✅ |
| P08 直播切片 | 8080 | ✅ |
| P09 销售考核 | 8090 | ✅ |
| P10 微调平台 | 8101 | ✅ |

**本轮修复 6 个启动 Bug**：
1. P06 uvicorn 字符串导入 → 传 app 对象 + sys.path 补丁
2. P10 hatchling 包发现 → pyproject.toml 加 packages 配置
3. P10 端口 8100 冲突 → 改 8101
4. P03 端口 8000 与 P02 冲突 → 改 8030
5. P04 端口 8100 冲突 → 改 8041
6. P03 缺 .env → 创建占位配置

---

## D8 · 统一平台：跨模块真实 HTTP 调用（2026-10-13）

> 落实架构规范「跨模块取数（P02 取 P06 指标、P09 取 P01 会话）必须走**真实 HTTP 调用**，
> 端口从 `shared/config` 的 `SERVICE_REGISTRY` 解析，禁止硬编码其他模块端口，并在 `_evidence/` 留调用日志」。
> 两条链路均实现「正常路径真实取数 + 降级路径不伪造数据（双处标注）」。

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p02-ecommerce-ops-assistant/cross-module-p06-20261013.md` | **P02→P06 指标**：正常拉取 7 项真实指标（source=p06-live）+ 降级演练（死端口→degraded，不含 metrics 字段） | 2026-10-13 |
| `p09-ai-sales-assessment/cross-module-p01-20261013.md` | **P09→P01 会话**：真实拉取 P01 MySQL 会话→角色映射→评分（65.5/70.5）+ 降级演练 + 34 pytest 全绿 | 2026-10-13 |

**P02 → P06 数据中台（指标）**
- 新增 `api/app/services/data_platform_client.py`；`/api/v1/dashboard/overview` 返回 `metrics/metrics_source/metrics_degraded`
- 地址 `cloudpivot_config.api_url("p06","/metrics/summary")` 从 services.json 解析，**未硬编码端口**；支持 `CP_P06_METRICS_URL` 覆盖
- 正常：7 项指标（gmv/order_count/conversion_rate/avg_order_value/return_rate/traffic_uv/traffic_pv），source=p06-live
- 降级：`ok=False/degraded=True/source=unavailable`，**不含 metrics 字段（不伪造）**；前端 dashboard 双处标注（绿色实时 / 黄色降级）

**P09 → P01 客服（会话）**
- 新增 `app/p01_client.py` + 端点 `GET /api/v1/p01/status`、`POST /api/v1/import/from-p01`
- 地址 `cloudpivot_config.api_url("p01","/chat/history")`；health 用 `service_url`（P01 探针在根 `/health`，不在 `/api` 前缀下）
- 角色映射 P01 user/bot → P09 customer/agent，按 session_id 聚合，规则引擎评分
- 正常：真实拉取 2 段会话并评分（source=p01-live）；降级：`imported=0` 不伪造
- 新增 4 项跨模块集成测试（monkeypatch，不依赖 P01 在线）；P09 pytest 30→**34 全绿**
- 同步修正 P09 README 第 10 条问答（原为「符合架构规范」的空泛表述 → 现写明真实端点/映射/降级/证据路径）

---

## D9 · 统一设计系统：三套构建型前端接入单一令牌源（2026-10-13）

> 落实规范「前端全部重构，版式/配色/组件全局统一」「统一深色主题 + 单一强调色」。
> 本轮覆盖三套**构建型**前端（P01 Vue+Vite、P02 Next.js、P03 Vue+Vite）——它们与
> 静态模块（p04~p10 走 `/shared` 运行时注入）不同，须把 `shared/ui-kit/tokens.css`
> **在构建期打进各自 bundle**，并把模块局部配色变量重指向 `var(--cp-*)`。

**统一机制（构建型模块）**
- 单一真源：`shared/ui-kit/tokens.css`（`--cp-bg/-surface/-line/-ink1..3/-brand/-success/-warning/-danger` + 浅色系覆盖 + `body.cp-app` 基线）
- 注入方式：以 **CSS 模块 `import`** 引入令牌（实测跨根 `@import` 会被 rolldown-vite/Next 静默丢弃）
- 变量重指向：模块 `:root` / Tailwind `@theme` 核心色 → `var(--cp-*)`；无对应令牌的派生色阶（brand 100~400/700~900、个别填充档）保留局部字面量
- 桥接：`data-theme="dark"`（html）+ `class="cp-app" data-cp-module="pXX"`（body）+ shell↔模块 `cp:theme` postMessage 主题同步
- P02 特例：Next 禁止 import 项目根外文件 → 新增 `web/scripts/copy-tokens.mjs`，`predev/prebuild` 构建期把令牌复制进 `web/src/app/tokens.css`（GENERATED 头，真源仍在仓库根）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `p01-ai-customer-service/p01-unified-chat.png` | P01 三栏客服工作台，深色统一主题真实渲染（构建产物 vite preview） | 2026-10-13 |
| `p02-ecommerce-ops-assistant/p02-unified-login.png` | P02 旗舰登录页，`--cp-bg` 底 + `--cp-brand` 主按钮真实渲染（next start 生产构建） | 2026-10-13 |
| `p03-deep-research/p03-unified-welcome.png` | P03 问数欢迎页，统一深色 + 品牌蓝标题真实渲染（vite preview） | 2026-10-13 |

**构建校验（真实执行）**
- P01 `vite build` ✅ → bundle 含 `--cp-bg:#0B0E14` + 浅色 `#F5F7FA` + `--cp-brand:#3370FF`
- P02 `next build` ✅（清 `.next` 后干净重建）→ 生产 CSS chunk `3ea7t4ed533b3.css`：`--color-brand-500:var(--cp-brand)`、`--color-fill-1:var(--cp-bg)`、`--color-ink-1:var(--cp-ink1)`，`--cp-bg` 深/浅双值，`body.cp-app`；`cp-shell/cp:ready` 主题桥编译进客户端 chunk；无残留字面量 `#3370ff`
- P03 `vue-tsc && vite build` ✅ → 令牌内联；删除死脚手架 `HelloWorld.vue`/`assets/vue.svg`/`public/vite.svg`，favicon 改内联品牌 SVG；端口 8030→5174（避开 P01 5173），registry 镜像 `services.js` 同步再生
- P03 后端补 `/outputs` StaticFiles 挂载，产物链接可解析；前端 API 基址由硬编码 `localhost:8000`（错误端口）改为同源相对 + Vite 代理

**未做/边界**：P02 图表组件内 JS 十六进制数组、内联 SVG `stop-color` 仍为字面量（值 == 品牌蓝，属性无法取 var()）；浅色模式下 P02 未映射的 brand 派生色阶不翻转（平台默认深色，浅色为次要开关）。

---

## D10 · 全平台联调 + 技术选型 ADR（2026-10-13）

**全平台联调（真实点击，browser-use 驱动 owner 账号）**
- 外壳网关 `8800`（当前代码）：真实登录签发 HS256 令牌 → 智能体矩阵首页 → 点导航 iframe 挂载模块
- 为联调把 **P06(8060)、P07(8070)** 从当前代码重启（旧进程无 `/shared` 挂载），实测 `/shared/ui-kit/tokens.css`=200、首页含 `cp-app`+`data-cp-module`
- 证据（`_evidence/shell/`，详见该目录 INDEX.md）：
  - `shell-login.png` 统一登录页
  - `shell-matrix-home.png` 登录后 AI 智能体矩阵首页（分层导航 10 模块 + 数据流闭环 + 统计）
  - `shell-mount-p06.png` 挂载 P06 数据中台，与外壳同一深色设计系统
  - `shell-mount-p07.png` 挂载 P07 素材中心，统一主题 + ECharts + 「Mock 模式」标注

**技术选型决策记录（`docs/adr/`）**
- `README.md` 索引 + 6 条 ADR：0001 微前端外壳（非单体）· 0002 SERVICE_REGISTRY 端口单一真源 · 0003 统一认证与令牌下发（P02 Cookie 会话例外）· 0004 跨模块真实调用与降级不伪造 · 0005 设计令牌单一真源与两类前端注入/耦合代价 · 0006 P05 零依赖例外

**启动脚本修正**
- `start-all.bat`：补上此前缺失的 **shell 网关(8800)** 与 **P01 前端(5173)/P03 前端(5174)**；统一入口由错误的「file:// 打开 shell\index.html」改为 **http://127.0.0.1:8800**；端口速查标注真源为 services.json
- `stop-all.bat`：端口清单补 8800/5173/5174

**门户现状校真（`01-portfolio/index.html`）**
- 十大模块卡的状态标签从「构建中」橙色改为「已运行」绿色（P01/P05/P09/P03/P04/P07/P08/P06/P10 均已真实运行，此前低估）；P02 保留「★ 旗舰」
- 「数据闭环架构」区补第 4 个共用盒 **`shell · 统一外壳`**（微前端外壳：登录 · 模块挂载 · 分层导航 · iframe），与 shared/llm-gateway、shared/auth+config、shared/ui-kit 并列
- 全页仍走 `shared/ui-kit` 深色令牌 + 单一品牌蓝强调色（无硬编码色）

| 文件 | 内容 | 采集时间 |
|---|---|---|
| `portfolio/portfolio-home.png` | 门户首屏（Hero + 统计条 + 旗舰 spotlight + 十大模块卡全绿「已运行」）Edge headless 真实渲染 | 2026-10-13 |
| `portfolio/portfolio-full.png` | 门户整页（含数据闭环架构 4 共用盒 + shell 盒 + 技术栈 + 关于作者） | 2026-10-13 |

**AGENTS.md 现状同步**：`agents.md`「当前阶段」由过期的「Phase 0 已完成」改写为真实当前态（微前端外壳 + SERVICE_REGISTRY + 统一认证（P02 例外）+ 跨模块真实调用 + 统一设计系统 + docs/adr + 证据 + start-all→http://127.0.0.1:8800）。

**已知边界（诚实记录）**：门户为静态页、直接引用 `shared/ui-kit` 令牌，不受进程新旧影响。

**续 · 静态模块全量重启收口（2026-10-13）**：上一节遗留的旧代码进程边界已闭合——用 `_restart_stale.bat` 从当前代码重启 **P04/P08/P09/P10** 并实测：四端口 `/shared/ui-kit/tokens.css` 全部 **200**、根页面均含 `cp-app` + `data-cp-module="pXX"` + tokens 链接；P09 Dashboard、P04 控制台真实截图确认与外壳同一深色主题（详见 `_evidence/shell/INDEX.md`）。至此**六个静态模块 P04/P06/P07/P08/P09/P10 全部运行当前代码、统一主题实测一致**。剩余边界仅为设计使然：P01/P02/P03 构建型前端令牌内联（见 D9）、P05 零依赖例外自带调色（ADR 0006），二者均不以 `/shared` 判定。

**再续 · 十模块全平台在线**：进一步按 `start-all.bat` 方式把构建型前端 **P01(5173)/P02(3001)/P03(5174)** 从当前代码拉起，三套真实截图（`_evidence/shell/unified-p0{1,2,3}-web.png`）确认与外壳同一深色统一主题。**至此十模块 + 外壳全部在线、深色统一主题全平台实测一致**（P02 登录 307 路由守卫、P05 登录 302 均属预期）。

---

## D11 · 用户反馈十项问题返工（2026-10-13）

反馈来源：`E:\桌面\问题整理.docx`（11 张截图）。逐条根因、修复与证据登记在
**`_evidence/shell/INDEX.md` 的「D11 返工」一节**，此处只记结论与状态变化。

| # | 反馈 | 结论 |
|---|---|---|
| 1 | CP logo / 云枢智能 要可自定义 | ✅ `shared/config/brand.json` 单一真源 + `/api/brand` 读写 + `data-cp-brand` 全站绑定；实测换成「奕波科技 / EboTech / 上传图片 logo」后外壳与模块同步变化（`D11-brand-custom-*.png`），随后已恢复默认 |
| 2 | P01 数字人三卡要横排 | ✅ 根因是 `App.vue` 的 `@media (max-width:1280px)` 在 iframe 内（视口 = CSS 宽 − 240px 侧栏）被误命中；改 clamp 自适应列宽 + 断点降到 900px + 嵌入态单独放宽 |
| 3 | P01 订单列表查不到 | ✅ 根因是商城中台 **18081 从未被 start-all.bat 启动**；已纳入托管，真实订单/商品出数据 |
| 4 | P02 忘密码 + 页面不显示 | ✅ 口令 `Test123456`（`bootstrap_demo_users.py:19-24`，实测登录 200，**未重置任何数据**）；前端 3001 已起；三份系统凭据已写进 README 与 `start-all.bat` 输出 |
| 5 | P05 颜色与平台不匹配 | ✅ 接入 `shared/ui-kit`（`/shared/*` 只读映射 + `cp:theme` 桥），并删掉 app.css 里把强调色覆盖成 **#7c3aed 紫**的重复 light 块；浅色态实测与外壳一致 |
| 6 | P09 不显示 + 英文 | ✅ 服务已托管；界面与**后端演示数据**全部中文化（含质检规则词表与台词一一对齐，评分区分度实测不变） |
| 7 | P03 答不出 + 英文 | ⚠️ 界面已中文化；「答不出」根因是**两套阿里云 Key 实测均 `InvalidApiKey`**。已改为按「模块 .env → 根 .env 主/备」成对解析、占位值导入期即判定，并把中文原因通过 WS 明确推给前端（实测收到 `event: error`），不再永远「思考中…」。要真回答需补有效 Key |
| 8 | P04 不显示 | ✅ 双重原因：服务没起 + 8041 上跑的是**旧进程**（`/` 路由还没注册，返回 `{"detail":"Not Found"}`）。全量重启后 `/` 307 → `/console.html` 正常 |
| 9 | P07 概览图表混乱/太少/去 emoji | ✅ 根因是 `echarts.init` 在 Tailwind CDN 注入 grid 样式前测宽 → 画布溢出压图；改为双 rAF 后 init + ResizeObserver + 配色读 CSS 变量（浅色可读）。删掉用 `Math.random()` 造数的趋势图，换成真实字段聚合的转化漏斗/标签热度/尺寸分布，共 6 图；侧栏 emoji 换 `CP.icon` SVG。**注**：截图是旧版，磁盘代码此前已被改过一轮 —— 这正是「旧进程」问题 |
| 10 | P08 / P10 不显示（P10 另含英文） | ✅ 服务托管 + P10 界面与演示数据中文化（模型/数据集标识符按约定保留英文） |

**新增基础设施**：`_tools/supervisor.py`（15 进程托管，端口 TCP 实测，`--takeover` 接管旧进程）、
`_tools/shot.py`（无头 Edge + CDP 截图取证，支持真实登录态注入与页面内断言）、
`shared/config/brand.json` + `/api/brand` + `/api/services/health`。
`start-all.bat` / `stop-all.bat` 改为调用 supervisor（旧版已备份到 `_tmp_issue/`）。

**状态变化**：`supervisor.py status` → **15/15 在线**，且全部运行当前代码。

**诚实边界**：① P03 需有效模型 Key 才能真回答；② P02 浅色态在 `/`→`/login` 跳转中会丢
`?cp-theme`，需改 Cookie 供 SSR 读取（用户清单未提 P02 配色，未扩大改动）；
③ P07 图表数据仍是 seed 演示数据，页面「Mock 模式」标注保留；
④ 截图右下角的黄色鸭子/卡通头像经全仓检索确认**不是本项目组件**（来自浏览器扩展或桌面宠物层），未处理。

---

## D13 · 第二批用户反馈（2026-10-13 下午）

5 条反馈逐条结论、根因与证据登记在 **`_evidence/shell/INDEX.md` 的「D13」一节**。要点：

- **P01 三卡比例**：两侧从实测 204px 提到 326/340px、聊天从 880px 收到 622px。过程中发现
  `App.vue:2615` 有一条**带 `!important` 的 `15vw` 规则**（另一并行会话所写）压制了列宽设置，
  已删除并在索引里留了冲突记录。
- **P02 登录页**：演示账号改为可点卡片，`?demo=boss|ops|design|cs` 服务端预填账号与口令。
- **P04 文档管理删除**：原 `DELETE /documents/{task_id}` 只删 MongoDB 记录、**不删 Milvus 向量**，
  删掉的文档仍会被检索命中（库里已实测存在 8 条孤儿向量）。改为向量与记录级联清理，
  并写了 `scripts/verify_cascade_delete.py` 做端到端验证：**PASS**（上传→1 条向量→删除→
  残留 0、按内容标记查回 0 条）。
- **P04 数据看板无限变长**：`canvas` 裸放在无定高容器里，Chart.js `responsive + maintainAspectRatio:false`
  每轮 resize 长高一点。套 `.chart-box{position:relative;height:260px}` 后实测 canvas 稳定 260px、
  页面高度 3 秒零增长。
- **顺带修掉两个真实缺陷**：① `run_graph_task` 为算 `chunk_count` 会把整条 LangGraph 导入流程
  **重跑一遍**（跑完还丢弃、恒写 0）；② 存量 `chunk_count` 全为 0 导致「热门文档 TOP 10」按 0 排序，
  已加列表接口自愈回填（实测 `0,0,0,0` → `14,7,5,3`）。另加 `console.html?tab=docs` 深链。
- **因并行会话把外壳改绑 `0.0.0.0` 而补的加固**：`POST /api/brand` 加令牌校验
  （实测无令牌 401 / 伪造 401 / 真实令牌 200，`GET` 仍匿名可读供登录页显示品牌）。
- **P03 需要配什么 API**：已在索引里给出三级凭据解析表；当前根 `.env` 的 `LLM_API_KEY` 为空、
  `LLM_API_KEY_FALLBACK` 与 `sk-ws-` 均实测 `InvalidApiKey`，需重新申领。未改代码。

**状态**：`supervisor.py status` → 15/15 在线。改动均在工作区，未 commit、未 push。

---

## D11 · 全平台白底化 + 品牌位可定制（2026-10-13 晚）

**做了什么**：默认主题由深色改为**白底 + 单一品牌蓝**（深色降级为 `html[data-theme="dark"]` 可选态）；
公司名与 logo 在全部品牌位改为经 `shared/config/brand.json` 自定义。
过程中先整体回滚了一次中途的「阿利茄汁面」品牌定制试验（该方向已放弃），
回滚依赖 `_runtime/aliren-backup/` 的 36 份改前副本 + 两个子代理各自的备份目录，
`shared/`、`shell/`、`01-portfolio/` 未入 git，故**没有 git 回退点，备份是唯一依据**。

**证据**：`_evidence/whiteblue/`（12 张真实渲染截图：shell 登录页 + 作品集站 + P01–P10，Edge headless 采集，非设计稿）

### 期间挖出并修掉的 4 个真实缺陷（都不是"配色"本身）

| 编号 | 现象 | 根因 | 证据图 |
|---|---|---|---|
| W1 | P05 登录按钮整颗看不见（白色药丸 + 蓝色外发光） | `app/auth.py` 的 `PUBLIC_PREFIX` 漏了 `/shared/` → 登录页请求 `tokens.css` 被鉴权闸门 **302** 拦走 → `--cp-*` 全部取不到 → `.btn.primary` 的 `background: linear-gradient(var(--brand), var(--brand-2))` **整条声明失效**，而字面量 `box-shadow` 仍渲染，于是只剩一圈蓝光 | `whiteblue/p05.png`（修复后蓝底白字） |
| W2 | P03 经营问数副标题/提示「看不见」 | `.welcome-text h2 { color: var(--border-color) }` —— 用**边框色当文字色**，深底上是暗灰幽灵字尚可读，白底上 `#DDE2EA` on `#F5F7FA` 对比度 ≈1.05 | `whiteblue/p03.png`（修复后可读） |
| W3 | P02 按钮文字不清晰、hover 反白 | `web/src/app/globals.css` 的 brand 色阶是**为深色反向排的**（`--color-brand-100:#142040` 最深 → `900:#c6d6ff` 最浅），于是 `bg-brand-700 text-white` = 浅蓝底白字。已按 Tailwind 惯例重排为 50 最浅 → 900 最深，并修掉 `text-brand-300/400` 两处低对比文字 | `whiteblue/p02.png` |
| W4 | 「怎么还有青色蓝色」 | 原 `:root` 里 `--cp-info:#38BDF8`（天青）与品牌蓝并存，且各静态模块页内联了 4–25 处**未令牌化**的深色值 | 全站 grep `38BDF8` 归零；`--cp-info` 改为中性 `#475467` |

### 真实测试数字（未粉饰）

- **P05**：`46 passed`（`.venv/Scripts/python.exe -m pytest tests -q`，1.9s）—— 放行 `/shared/` 后鉴权用例未回退。
- **P06**：`44 passed`（同上，1.9s）—— 确认回滚后数据层与指标层完好。
- **P05 数据健康分 48 / 质量校验 9 条失败**：**这是既有状态，不是本轮引入**。
  根因是样例数据窗口硬编码在 `2024-07-01 + 91 天`，而 `check_freshness` 按 `date.today()` 判定，
  超过 30 天即 FAIL。要修得重跑数据生成（会改变 `约 3.5 万订单` 等已登记口径），本轮**未动**，如实记录。

### 品牌位可定制的落点（新增）

- `shared/ui-kit/tokens.css` 内新增 `.cp-brandmark`（因 P04/P06–P10/画廊/作品集都**不引** `components.css`，
  共享 logo 样式只能放在它们唯一引入的那个文件里）。
- 新挂 `data-cp-brand="logo"` 钩子：P04 `console.html`/`chat.html`、P06、P08、P09、P10、作品集站 —— 此前只有 shell 与 P07 有。
- 主题存储键升 `cp_theme_v2` 并由 `ui-kit.js` 清掉旧 `cp_theme`：
  旧值里存的 `dark` 是「深色曾是默认」时 `initTheme()` 自动写入的，沿用旧键会让白底默认永远翻不回来。
  读写方（ui-kit.js / P01 main.js / P02 theme.ts+bridge+layout / P03 main.ts / P05 app.js+7 页）共 15 个文件同步升键，否则外壳切主题模块不跟随。
- 规范同步：`.qoder/rules/02-技术规范.md` 的「统一深色主题」已改为白底并加**对比度硬门禁**；
  `docs/adr/0005` 追加修订记录（含上述"文档说挂了 tokens.css 但实际没挂"的偏差）。

**状态**：15/15 在线。P05 为验证鉴权修复单独重启过，其余进程未动。改动均在工作区，未 commit、未 push。

### 补记 · P02 运营助手返工（用户反馈「还是有问题」后）

先排除取数问题：`POST /api/v1/auth/login` → 200，`GET /api/v1/dashboard/overview` → 200，
返回真实指标（GMV 35958.37 / 订单 133 / 转化率 0.44% / 客单价 270.36 / 退货率 20.30%），
与 P06 侧数据一致 —— **空白不是数据造成的**。

再定位到两个前端问题：

- **W5｜`bg-ink-1` 被当按钮与面板底色用了 51 处（共 86 处替换）**
  `--color-ink-1` 是**文字色**令牌（ink = 墨），却被拿去当背景。
  深色主题下它 = `#E8EAF0`（近白），于是 `bg-ink-1 text-white` 一直是**白字配近白底**，
  即用户长期反馈的「按钮字看不清」；白底化后它 = `#1A1F2B`（深藏青），字能读了，
  但在一片白页面上留下几十块深色，即「颜色不统一、还有深色块」。
  处理：按钮统一 `bg-brand-600` + `hover:bg-brand-700`（原来 `hover:bg-ink-1` 等于没有悬停反馈）；
  Agent 页「Harness 边界」整块深底面板与生成任务的 JSON 代码块改成浅面深字。
- **W6｜我自己引入的禁用态回归**：把 `--color-fill-3` 从 `#222836` 改浅为 `#E4E9F1` 后，
  5 处 `text-white ... disabled:bg-fill-3` 变成白字配浅灰底。已补 `disabled:text-ink-3`。

**验证方式（如实说明）**：P02 我**没能用像素验证** —— 沙箱内置浏览器经代理请求
`/_next/static/chunks/*` 全部 403（同一 URL 用 curl 是 200），页面只水合出顶栏。
改用服务端渲染产物验证：`/agent`、`/settings`、`/products` 三页 HTML 中
`bg-ink-1` 命中 **0**、`bg-brand-600` 分别 6/10/6、`data-theme="light"` 各 1；
`npx tsc --noEmit` 退出码 0。P02 web dev server 已重启（清掉旧 chunk/HMR 状态，
这是「内容空白」最可能的环境成因），重启后 `/dashboard` SSR 200、46174 字节、日志无编译错误。
**页面实际观感需你在自己浏览器里硬刷新（Ctrl+Shift+R）确认。**

---

## D12 · P03 问数模型凭据接通（2026-10-13 晚，Key 由用户重新提供）

**结论先行：两套百炼 Key 现在都有效，P03 问数已能真实出内容。此前「答不出」不是 Key 的问题，是代码 bug。**

### 根因（真凶，非凭据）

`projects/p03-deep-research/agent/llm.py` 用 `Path(__file__).resolve().parents[2]` 定位仓库根并注释「即面试项目根」——
实际指向 `面试项目/projects`，那里没有 `.env`。于是 `_read_root_env()` 恒返回空字典，
根 `.env` 里配对好的两套凭据**一次都没被读到**，`resolve_model_config()` 直接落到
「未找到可用的模型凭据」分支。已改为向上扫描、以 `LLM_API_KEY_FALLBACK` 作根 `.env` 锚点定位。

| 时点 | 同一问句实测 | 证据 |
|---|---|---|
| 修复前（服务加载旧代码） | `session_created → error「未找到可用的模型凭据」`，2 个事件即终止 | `p03/e2e-20261013-203658.json` |
| 修复后（直答类问句） | `session_created → task_result`，**8.0 秒**真实中文答复，无 `__mock__` 标记 | `p03/e2e-20261013-204428.json` |
| 修复后（取数类问句） | 17 个事件、**195.5 秒**：派发「数据库查询助手」→ `SHOW TABLES`/`SELECT 1`/`SHOW DATABASES` 多次重试 → 转 RAGFlow → **明确回答「未取得数据」并拒绝编造销量数字**，给出端口级故障定性（3306/9380 无人监听）与恢复清单 | `p03/e2e-20261013-204855.json` |

第三行是本轮最有价值的一条：模型层通了之后，`04-验收门禁.md` 要求的「幻觉测试——库里没有的数据必须拒答而非编造」
在真实链路上自发成立（未改提示词）。P03 的 SQL→执行→图表全链路仍卡在 **MySQL 未启动**，见下「遗留」。

### 两套凭据的真实能力边界（本轮逐个打出来的，非文档抄录）

| 通道 | `/models` | chat（qwen3.8-max / flash） | Embedding | 备注 |
|---|---|---|---|---|
| `sk-ws-` 免费额度 `ws-amdqcpdtt4gdo5ax...maas` | 200，**176 个模型** | 200 / 200 | **200**（`qwen3.7-text-embedding-flash`，1024 维） | `qwen3.7-plus` 返回 403 `Free quota exhausted`（账号处于「仅用免费额度」模式）；TCP 层偶发连不通，3 次里 1 次 |
| `sk-sp-` Token Plan（Essential）`token-plan...maas` | 200，17 个模型 | 200 / 200 / 200（含 `qwen3.7-plus`） | **404 `Model not exist`** | 官方标注 2026-10-22 00:00 到期，配额稳定 |

上表由 `p03/llm-endpoint-probe.py` 打出（带重试，逐个端点跑 `/models` + `/chat/completions`），原始输出 `p03/llm-endpoint-probe.txt`。脚本只从 `.env` 取 Key，不落字面量。

要点：**Embedding/Rerank 只有免费额度端点有**，Essential 端点没有 —— 凡涉及真嵌入的模块（P04）不能只靠套餐通道。

### 凭据解析顺序（P03）

`模块 .env` → 根 `.env` 主（`LLM_API_KEY`，当前空）→ **Essential 套餐**（稳定，现用）→ 免费额度端点（兜底，10-22 套餐到期后无需改代码即接管）。

### 顺手修掉的网关缺陷

`shared/llm-gateway` 的 `GatewayConfig.endpoints` 把**主 Key 复用给备用端点** —— 百炼三套凭证互相隔离，
这正是本项目自己文档里禁止的「A 家的 Key 打 B 家的端点」，故障转移必然 401。已新增 `fallback_api_key`
（缺省仍复用主 Key，兼容既有调用方）。回归：`projects/p02-ecommerce-ops-assistant/api/scripts/test_gateway_integration.py`
四场景全 PASS，真实调用消耗 265 tokens、总时延 9.4s。

### ⚠️ 本轮发现的安全问题（需用户处置）

`projects/p02-ecommerce-ops-assistant/api/scripts/test_gateway_integration.py:18` 把 `sk-sp-` 真实 Key
**写成源码字面量**，且该文件已随 `ac08668` 推到 `github.com/liyibo0410/yunshu-ai-portfolio` 的 `origin/main`。
本轮已把源码改为从 `api/.env` 读取（脚本回归通过），但**历史提交里的 Key 仍在公网上**：
需在百炼控制台**吊销并重发**这把 `sk-sp-`，再决定是否清理 git 历史（清历史要 force-push，属破坏性动作，未经确认不做）。

### 遗留（不算本轮完成）

- **P03 完整门禁未闭环**：`sql/cps.yml` 的 MySQL 配 `3307/mydb`，而 P03 自己 `.env` 写的是 `3306/pharma_db/mock_password`；
  本机 3306 无监听、3307 已被 P01 的 `customer-service-mysql` 容器占用 → 起库前要先定端口，属需确认的动作。
- **网络搜索通路仍是 mock**：`TAVILY_API_KEY=tvly-mock-key-not-configured`，工具会返回 `error` 结构（不崩），但问不出外部实时信息。
- **一次瞬时故障**：`p03/e2e-20261013-204321.json` 收到 `error「Execution failed: Connection error.」`（OpenAI SDK 的 APIConnectionError）。
  同一问句重跑已能通过，判定为本机内存吃紧所致——排查期间空闲物理内存仅 **1.0 GB / 16 GB**，
  我的复现脚本直接被 `OpenBLAS: Memory allocation still failed after 10 retries` 打死。演示前建议先关掉占用内存的无关进程。
- `00-总纲/09-凭据与套餐配置说明.md` 第 26 行仍写着 `sk-ws- → 401 InvalidApiKey`，属**绝对保护目录**未改动，此处登记待用户在总纲内自行更新。

---

## D14 · P02 工作台四张图表空白 + 链接型按钮「蓝底无字」（2026-10-13 晚）

**用户反馈**：电商运营助手的「平台商品分布 / 店铺状态分布 / 各店铺商品数 / 商品类目分布」不显示，
且「好多蓝色按钮不显示字」。

**根因是两条互不相干的缺陷，都被同一个页面同时暴露出来：**

### ① 图表空白 = Next 16 dev server 把 JS chunk 判成跨站，全部 403

`next dev` 默认只放行 `localhost` 来源的 `/_next/*` 请求（`server/lib/router-utils/block-cross-site-dev.js`，
允许名单 = `**.localhost` + `localhost` + `allowedDevOrigins` + 启动时的 hostname）。
统一平台按 SERVICE_REGISTRY 用 **`http://127.0.0.1:3001`** 挂载 P02，浏览器为 `<script type=module>`
带上 `Origin: http://127.0.0.1:3001` → hostname `127.0.0.1` 不在名单 → **HTTP 403 `Unauthorized`**。

- 实测：`curl -H "Origin: http://127.0.0.1:3001" .../_next/static/chunks/_1a9x3t3._.js` → **403**；去掉该头 → 200。
- 后果链：HTML 与 CSS 正常（`<link rel=stylesheet>` 不发 Origin，所以样式在、页面看着"没坏"），
  但 **3 个 chunk 403 → React 从不水合 → `EChart` 的 `useEffect` 不执行 → 一张 canvas 都不画**，
  四张图表卡片只剩标题和空白。HMR 的 WebSocket 同样被 403（`ERR_INVALID_HTTP_RESPONSE`）。

**修复**：`projects/p02-ecommerce-ops-assistant/web/next.config.ts` 增加 `allowedDevOrigins: ["127.0.0.1"]`
（Next 官方口子，不是绕过），重启 dev server 生效。

### ② 蓝底无字 = ui-kit 令牌表里的裸 `a{}` 未分层，压掉了 Tailwind 的文字色工具类

`shared/ui-kit/tokens.css` 的 `a { color: var(--cp-brand) }` 与 `a:hover {...}` 是**未分层**声明，
而 Tailwind 的 `.text-white` / `.text-ink-2` 在 `@layer utilities` 内 —— 按 CSS 层叠规则，
未分层声明优先级高于**所有**层。于是凡是 `<a>` 扮演的按钮（`buttonVariants()` 走 `<Link>`）
都被染成品牌蓝，配 `bg-brand-500` 就是**蓝底蓝字、文字消失**；侧栏 `<a>` 导航也被染蓝，
违反了「单一强调色只用于按钮与关键信息」的设计门禁。

**修复**：把这两条规则包进 `@layer base`（`utilities` 层在其后，工具类重新生效），
并在令牌表里写清为什么必须分层。对不用 Tailwind 的静态模块（外壳 / P04~P10）无行为变化：
`components.css` 里没有裸 `a{}` 规则，未分层声明原本就赢，现在仍然赢。
改完由 `npm run copy:tokens` 同步进 P02 的构建期副本 `web/src/app/tokens.css`。

### 验证（无头 Edge + CDP，带真实登录态）

探针已固化为常驻工具 **`_tools/contrast_probe.py`**（WCAG 2.1 对比度 + 4xx 脚本 + 页面异常 + canvas 数）：
`python _tools/contrast_probe.py http://127.0.0.1:3001/ --login-form p02 --out x.png`

| 页面 | 修复前 | 修复后 |
|---|---|---|
| `/`（工作台） | `canvases=0`、3 个 chunk 403、4 个 `<a>` 蓝底蓝字（全部平台 / 店铺详情 ×3） | `canvases=4`、`badScripts=[]`、`errors=[]`、蓝底蓝字清零 |
| `/products` | — | `badScripts=[]`、`errors=[]` |
| `/dashboard` | — | 同上 |

证据：
- `p02/2026-10-13_图表空白_修复前.png` —— 四张图表卡片全空、三个蓝色按钮无字（与用户截图同一状态）
- `p02/2026-10-13_图表与按钮文字_修复后.png` —— 双环形图 + 横/纵柱状图齐全，按钮文字可读，侧栏导航回到次文本灰
- `p02/2026-10-13_外壳挂载P02.png` —— 经 `http://127.0.0.1:8800/#/workspace/ecommerce-ops` 挂载路径正常
  （iframe 内是 P02 自己的登录页，属 ADR-0003 的有意识例外，不是回归）
- `p02/2026-10-13_工作台_对比度探针.png` —— 修复后工作台整页（探针同时输出的位图）

### ⚠️ 探针顺带量出来的存量欠账（**已定口径：暂不动，登记为已知欠账**）

`.qoder/rules/02-技术规范.md` 的门禁是「任何文字色在其底色上对比度 ≥ 4.5:1」。
修复后的 P02 工作台仍有 **64 个元素不达标**，全部来自**令牌本身**而不是这次的改动：

| 用法 | 实测 | 出现处 |
|---|---|---|
| `--cp-ink3 #8A94A3` 当正文/表头字色 | 2.71:1（灰底）/ 2.86:1（白底） | 商品池表头、页面副标题、登录页演示账号邮箱 |
| `--cp-success #16A34A` 叠 `--cp-success-bg #E7F6EC` 的标签 | 2.95:1 | 店铺「启用」、商品「性价比」等状态 Tag |

**2026-10-14 用户定口径：本轮不改。** 理由是改这两个令牌会同时动到外壳与十个模块（含 P05 的强调色回指），
属全站视觉决策，不该塞进收尾窗口。

- **触发条件**（何时必须回来收口）：任何一次涉及 `shared/ui-kit/tokens.css` 的改动，
  或作品集对外发布/换肤前 —— 届时按下面方向一次改对，并全站重截图复验；
- **收口方向**：`--cp-ink3` 只留给禁用态，正文弱文本一律 `--cp-ink2`；
  成功/警告 Tag 改用更深的字色配浅底；
- **约束生效范围**：欠账只允许「维持现状」，**不允许扩大** ——
  本轮新增页面一律不得用 `--cp-ink3` 当文字色（例：P09 `web/label.html` 的正文/次要文本
  统一用 `--cp-ink1` / `--cp-ink2`，`--cp-ink3` 只出现在注释里说明该约定）。

### 本轮顺带发现 / 遗留

- **同类隐患未逐个排查**：P03（Vite + Tailwind）也 `@import` 了同一份 tokens.css，修复①对它同样受益；
  其余用 Tailwind 的模块若将来改用 `127.0.0.1` 访问 dev server，同样需要各自的 `allowedDevOrigins`。
- **手机/局域网预览仍会踩坑**：`allowedDevOrigins` 只加了 `127.0.0.1`。用 LAN IP 打开外壳时，
  iframe 的 Origin 变成该 IP → P02 的 chunk 会再次 403，需要把那个 IP 追加进名单（IP 会变，未预先写死）。
- **服务现状**：排查期间共享控制台被 `^C`，除 shell / p02-api / p02-web 外其余 12 个服务掉线，
  本轮未擅自全量重启（`supervisor.py status` → 3/15 在线）。
- 改动均在工作区，**未 commit、未 push**。


---

## D15 · 用户反馈：P04 文档删不掉 / 检索问答请求失败 + 两处更名（2026-10-13 晚）

用户原话：「BOSS智库有问题上传文件不能删除，知识库检索问答回答请求失败，请稍后重试，然后把 BOSS 智库名字改为 RAG 知识库，Deep Research 问数改为 NL2SQL 问数」。

### 根因（一句话）

**8040 上跑的是 10-12 22:56 启动的旧进程**，而级联删除等修复是 10-13 14:10 才写进磁盘的 —— 服务从未重启，用户点到的仍是「只删 Mongo、不清 Milvus」的旧接口；同时 SERVICE_REGISTRY 里 p04=8041 无人监听，外壳挂载区显示「未启动」。陈旧判定用的是那条老规矩：`console.html`=200 但 `/shared/ui-kit/tokens.css`=404。

### 做了什么

| 项 | 处理 | 证据 |
|---|---|---|
| 文档删除 | 重启到注册表端口 8041 跑当前代码（先按 `file_title` 清向量、最后删 Mongo 记录）；UI 侧确认框与结果提示带真实清理条数 | `_evidence/p04/verify-cascade-delete.log`（上传→1 条向量→删除→向量与记录双清→不再命中，PASS） |
| 检索问答「请求失败」 | 控制台改走 `is_stream=true` + `EventSource`（阶段进度→逐字→final 带 4 条引用）；非流式分支从「在 `async def` 里直接跑 35s 流程图」改成 `asyncio.to_thread`，不再阻塞事件循环；失败时把 HTTP 状态 / 后端 detail / SSE error 原文显示出来，另加 120s 看门狗 | `_evidence/p04/stream-query-evidence.log`（317 个 SSE 事件、1861 字回答、引用带 score）、`console-qa-dom.json`（浏览器真实渲染）、`console-tab-qa.png` |
| 上传列表不能移除 | 每行加「✕ 移除」+ 列表级「清空列表」，确认框写明「移除不中断服务器端导入，删文档请到文档管理」 | `console-tab-upload.png` + 浏览器内交互实测（1 行→点 ✕→0 行、列表条隐藏） |
| 页头数字与表格行数对不上 | `/statistics` 数全库、列表按 `owner=public` 过滤（库里躺着 1 条历史 `owner=test`）→ 统计改为同口径 | `stream-query-evidence.log` 末尾（两边均 5 文档 / 36 切片） |
| 降级路径自带炸弹 | `node_answer_output` 在 LLM 流式异常时 `push_to_session(SSEEvent.END,…)`，而 `SSEEvent` 没有 `END` → AttributeError 把整条流程带崩；删掉，终止事件统一由 FINAL 发 | 代码 `processor/query_processor/nodes/node_answer_output.py` |
| 直跑入口谎报端口 | `console_service.__main__` 写死 8100（与注册表 8041 漂移，正是今天 8040/8041 漂移的同类病）→ 改从 `services.json` 解析 | 代码 `web/api/console_service.py:_registry_port` |
| 更名 | 「BOSS智库 / 掌柜智库」→「RAG 知识库」：P04 页面标题/侧栏/欢迎语、FastAPI 标题与日志、`start.bat`、README、docs；「Deep Research 问数」→「NL2SQL 问数」：`services.json` 真源 + `build_js.py` 重生成、supervisor 标签、P03 页面标题与 `dist`、门户/画廊/README/AGENTS/规则。**历史归档不动**（`_evidence/`、`.workbuddy/`、`work/eval_report/`、`00-总纲/`、源项目名、GitHub 仓库名 `-BOSS-RAG-`） | `shared/config/services.js`、`curl :8800/shared/config/services.js` → p03=NL2SQL 问数 / p04=RAG 知识库；`:5174` 标题、`console-tab-docs.png` 侧栏 |

### 顺带修掉的平台级缺陷（被这次重启暴露）

- **P07 起不来**：`ModuleNotFoundError: No module named 'cloudpivot_config'` —— 真因是 `__editable__.cloudpivot_config-1.0.0.pth` 被写成 UTF-8 字节，而 Windows `site.py` 按 ANSI(GBK) 读 `.pth`，含中文的仓库路径解不出来，该目录从未进 `sys.path`（同 venv 里 GBK 写的 `llm_gateway.pth` 一切正常）。已把 p07/p09 两个 `.pth` 重写为 GBK，实测 `port('p07')=8070`、`api_url('p01',…)` 解析成功。**连带发现 P09 此前是静默走 env 兜底**，SERVICE_REGISTRY 其实一直没生效。
- **P07 第二个坑**：`uv run python app/main.py` 下 `from app import config` 报 `No module named 'app'`（`sys.path[0]` 是 `app/`），按 p06 既有做法在入口补项目根。
- **服务面**：接手时 3/15（D14 那轮被 `^C`），现已 `supervisor start` 全量拉起 → **15/15 在线**，外壳 `GET /api/services/health` 对 p03/p04/p07/p09 均报 online。

### 未跑通 / 遗留（不当成已完成）

- **P04 pytest 套件当前跑不完**：`tests/` 只有重排相关两个文件，复跑先 9 failed/14 passed、随后直接段错误，栈顶是 `torch/storage.py` mmap 读权重 + `FlagEmbedding` 重排器构造 —— 原生崩溃；机器可用内存 3.3/15.7 GB，且**停掉 p04 服务复跑仍崩**，与本轮改动文件无交集。详见 `_evidence/p04/pytest-reranker-crash-20261013.log`（基线 `full_testsuite_p1.log` 的 23 passed 是机器上没起这么多服务时跑出来的）。
- 控制台「全部导入任务」表是内存态，重启即空 —— 已在 README「已知限制与 mock 边界」写明（该节本轮补齐，之前缺）。
- 库里那条历史 `owner=test` 文档没动（属数据删除，需用户点头）。
- P04 README「快速开始」里的 `git clone https://github.com/liyibo0410/-BOSS-RAG-.git` 未改：本机 curl 不出网，无法核实仓库是否还在，**若已改名需用户确认后一并更新**（简历两处也引用了该仓库名）。
- 更名顺带同步了 `03-resume/` 两版简历里的「P04 BOSS 智库」字样（纯产品名，未动任何主张/数字）—— 如希望简历保留旧称，说一声即可回退。
- 改动均在工作区，**未 commit、未 push**。


## D16 · 用户反馈：品牌定制「logo 与名字还是不能自定义」全站返工（2026-10-13 晚）

详情见 `_evidence/shell/D16-brand-fullsite.md`（七条根因逐条实测 + 改动清单 + 13 个入口取证）。

**外壳 8800 的读写本来就通**（改名 / 传 logo / 刷新持久化均实测通过），坏的是「全站生效」那一半：

| 根因 | 修复 |
|---|---|
| **8801 上跑着 8:26 启动的旧 `serve.py`**（品牌接口 18:52 才加），`/api/brand` 一律 404 → 该入口改品牌必然失败 | 按用户决定 `taskkill /PID 5220`，只保留 8800 一个网关 |
| P04 `chat.html` 根本没引 ui-kit/services，`data-cp-brand` 是死绑定；`console.html` 缺 company 与 brand-src | 补齐引入与绑定 |
| P05 七页有 ui-kit 但**零品牌节点**，公司名写死在 `app.js` 的 `BRAND` 常量 | 顶栏/页脚/登录页接品牌位，注入后重放 `applyBrand` |
| P01 / P03 运行时桥只有 `cp:theme`/`cp:auth`，没有 `cp:brand` | 新增共用 ES 模块 `shared/ui-kit/brand-bridge.js`（含 MutationObserver 补挂） |
| P02 无桥 + `layout.tsx` 硬编码标题 + Next origin 上 `/shared/brand.json` 404 | 新增 `/api/brand` 路由 + `useBrand()` store + `CpBrandBridge` + `generateMetadata` 读盘 |
| 门户 / 画廊只有相对路径 brand-src 且没引 services.js → 既无同源可读也无端口兜底 | 补 `services.js`；画廊 h1 加 logo 位 |
| 构建型模块与 `file://` 页面没有同源 `/shared` | 注册表新增顶层 `gateway.web_port`；网关 `GET /api/brand` 开 CORS；`CP.loadBrand` 改成「同源 → 网关」来源链；新增 `[data-cp-brand-logo-src]`（自定义 logo 优先、否则用模块自带标识）与 `cp:brand-applied` 事件 |

**取证**：临时改名「启明科技 / Qiming Tech」→ 13 个入口逐张出图（`D16-brand-*.png`，含 `file://` 打开的门户与画廊）→ 脚本自动还原；P01/P02/P03/P06 另做 `cp:brand` 实时下发实测（DOM 与标题即时更新）。

**遗留**：外壳 iframe 内的下发只能靠代码路径证明（跨源读不到 iframe DOM）；P01/P03 网关端口是构建期注入，改端口需重启 dev server；P02 容器化未挂 `shared/` 时回落默认值；**`shared/config/brand.json` 至今不在 git 里**（内含用户上传的 logo dataURL，是否入库待用户定口径）。


## D17 · P07 AI 素材中心功能返工：补齐上传/打标/检索/预览/生成入库全链路（2026-10-14 凌晨）

用户反馈「AI 素材中心有些功能不完善」。先做实测诊断（隔离临时库跑探针，不碰真实 `data/assets.db`），确认不是「不完善」而是**三处关键环节根本不存在**：

| 诊断结论 | 证据 |
|---|---|
| 前端零上传入口：后端有 multipart 上传与删除，`web/index.html` 里 `type="file"` 出现 **0 次**，fetch 只有 search/generate | 代码实测 + 门禁「上传素材→打标→以文搜图」当时只有 pytest 能证明，人点不出来 |
| **「智能打标」端点不存在**：README 架构图与 `services.json` 描述都写着打标，routes 实测只有 assets/search/generate/stats/reports | 探针打印 `app.routes` |
| 上传的文件无法预览：落盘了但无任何读取路由，`/uploads/…`、`/files/…`、`/data/uploads/…` 全 404；素材库整屏只有「IMG」文字块 | 探针 4 条 GET 全 404 |
| 检索是 `query.lower().split()` + 子串包含 → 中文只有字面连写命中 | 8 条自然语言查询实测 6 条 0 命中（`春季护肤品`/`夏天清爽的防晒霜`/`有没有直播用的背景板`…） |
| `created_at` 写死 `2026-10-12T10:00:00`；上传不读宽高（`width=None`）；`tags` 原样入库 → 用户输 `护肤,夏季` 时前端 `JSON.parse` 抛错、素材库整块空白 | 上传真实 1×1 PNG 后回读接口 |
| `generate` 是写死模板且引用 `via.placeholder.com` 外链，结果不落库（检索「AI生成」0 命中）；未走 `shared/llm-gateway` | 响应体 + 库内检索 |
| P02↔P07 联动只存在于 README 架构图里，P02 侧对应项仍是未勾选的 `[ ]` | 两仓交叉 grep |
| README 三个「量化指标」（`<100ms`/`1000+`/`关联覆盖率>80%`）无任何测量依据，实际关联覆盖率 58% | 违反红线 2，已删 |

**修复**（`projects/p07-ai-asset-center/`）：

- 后端从单文件 `app/main.py` 拆成分层：`config`（根 `.env` + 端点解析）/`db`（建表 + 就地列迁移 + 演示图回填）/`repository`/`services/{search,tagging,generation,media,data_platform,llm}`/`api`，prompt 版本化进 `prompts/*.md`；
- **智能打标接真模型**：`shared/llm-gateway` + 主 Key 为空自动落备用端点；凭证不齐退回词表规则并返回 `tag_source=rule` + `degraded_reason`；
- **检索重写**：中文 n-gram + 同义组归一 + tags/name/description 字段加权 + IDF + 0.18 拒答阈值，命中理由回显用户原词与字段；
- **上传链路补全**：文件头嗅探（不信客户端 Content-Type）、Pillow 读真实宽高、`GET /api/v1/assets/{id}/file` 预览、删除连带磁盘文件、真实时间戳、`tags` 读侧统一为数组；
- **生成补全**：文案与视频分镜走真实 LLM（结构化 JSON），图片为 Pillow 投放规格卡并在接口/页面/README 三处标注「非 AI 出图」，两者均可 `save_to_library` 直接入库；
- **跨模块**：报表新增真实调用 P06 `/api/v1/metrics/summary` 的大盘对照（端口经 SERVICE_REGISTRY），P06 不可达时返回原因不编造；新增 `POST /api/v1/ingest` 供 P02 推送（来源白名单 + 可选令牌）；
- 前端补齐上传面板（拖拽 + 自动打标勾选）、缩略图与大图预览、删除、打标覆盖/追加、投放数据录入（漏斗校验）、生成入库、检索命中理由与拒答态、动态 LLM 徽章与网关成本、`#asset/ID`/`#search/<词>` 深链；所有动态文本经 `esc()` 转义。

**评测与测试**（数字全部实测，条件写进 README）：

- `eval/search_eval.py` 新旧策略对照（26 条人工标注查询）：Recall@5 **1.0 vs 0.05**、Precision@1 1.0 vs 0.05、MRR 1.0 vs 0.05、拒答准确率 1.0，延迟 avg 0.78ms / P95 0.87ms（12 条语料、本机进程内，不外推）；
- `eval/tagging_eval.py`（12 次真实网关调用、7963 tokens、0 mock）：LLM 概念覆盖率 **0.97** vs 词表规则 0.879，平均 7.4s/次（qwen3.8-flash）；
- pytest **18 → 68 passed**，模型与 P06 全部打桩，测试进程不发真实请求。

**取证**：`_evidence/p07-ai-asset-center/` 七张无头 Edge 截图（概览 / 上传与缩略图 / 详情打标 / 检索命中 / 检索拒答 / 生成入库 / 报表含 P06 大盘）+ `pytest-20261014.log` + 两份评测 json/md，逐条对应门禁见该目录 `INDEX.md`。上传→打标→预览→检索→删除也在浏览器里用真实文件跑过一轮（`upload_file` + 点击），入库素材 `AST-B1AB14` 即截图中的「本地上传」卡。

**未闭环（不当成已完成）**：① 图片仍非 AI 出图（`wan2.7-image` 接口形状未验证，验证需消耗配额）；② 以文搜图仍是文本检索，非 CLIP 向量（token-plan 端点 embeddings 实测 404）；③ **P02 侧「一键推送到素材中心」仍未接线**（P07 的 ingest 已就绪）；④ P07 API 未接统一鉴权，与 P06/P08/P09/P10 一致属平台级待办；⑤ 无并发压测。

**改动均在工作区，未 commit、未 push。**

---

## D18 · 收尾前诚信复核：P02 测试补证 / P04 指标口径 / D7 反向错误 / P10 去编造指标（2026-10-14 凌晨）

用户要求「看看还有什么需要优化的地方，明天收尾」。先做全仓复核（15 端口探活全在线），
把问题按「面试官一戳就破的诚信硬伤 / 门禁真缺口 / 收尾卫生」分档，本条记录已动手的第一档。

**判据统一**：凡是「没有测量来源的数字」，要么改成真实测量，要么显式变成 `null` + 原因，
不允许继续以数字形式出现在接口或文档里（红线 2、红线 3）。

### A1 · P02 旗舰的测试数字终于有日志了

`INDEX.md:51` 长期写着「157 → 162 tests passed」，而 P02 是**十个模块里唯一没有 pytest 运行日志**的
（其余 9 个都有 `pytest-*.log`）。2026-10-13 23:52 在 `api/` 内真实重跑：
**162 passed / 0 failed / 24.13s**，与结论一致 → `p02/pytest-20261013.log` + 新建 `p02/INDEX.md`
（含跑法、内存库隔离方式、以及「覆盖率未测 / 前端无套件 / 部署上线未满足」三项声明）。

### A2 · P04 评测口径三处对齐

- `_evidence/INDEX.md` 与 P04 README 原先引用的是 **3 条样本 + Cloud 降级 passthrough** 那一版
  （Faithfulness 0.9778 / Relevancy 0.5585，结论「Local 略优」）；
- 现行报告 `_evidence/p04/rag_compare_report.json` 是 **36 条 × 2 后端 = 72 次请求、两侧均为真实后端**：
  Cloud 五项指标全部更高（Context Precision 0.919 vs 0.681、Recall 0.9583 vs 0.8681），
  延迟 18.69s vs 51.37s（**快 2.75×**），Local 唯一优势是**不出网** → 结论与旧版相反，已改写；
  旧版归档在 `p04/_archive_D5-01_baseline/`。
- 顺带修掉两处**指向不存在文件的登记**：`p04/e2e_result.json` 根本不存在、`p04/e2e_test.log` 是 0 字节，
  却登记为「端到端验证结果」；改指真实的 `stream-query-evidence.log`（317 个 SSE 事件 + 4 条引用）等。
- README 补记两项门禁未满足：**拒答率从未被计算**（`eval/eval.py` 只有 5 个 Ragas 指标）、
  **父子分块 vs 定长的策略对比实验没做过**（只有一种分块长度）。

### A5 · `D7-全服务验证报告.md` 的反向错误（把自己写得更假）

Mock 边界表里「**P04 向量化 mock（随机向量）**」是错的：`utils/embedding_utils.py` 用
`pymilvus.model.hybrid.BGEM3EmbeddingFunction`，全文件 `random` 命中数为 0；
运行日志 `eval_compare_run.log:22` 有 `FlagEmbedding...loading existing colbert_linear and sparse_linear`，
`:69` 有本地 `BAAI--bge-reranker-large` 加载记录。同表另两处一并更正：
P03「LLM 为占位 Key 会失败」（D12 已接通，仍缺的是 3306 数据源）、
P05「全功能真实运行」（审批侧是 `mock/feishu.py` 模拟实现）。报告末尾新增「更正记录」一节，保留审计痕迹。

### A4 · P10 去掉全部无测量来源的数字

| 位置 | 改前 | 改后 |
|---|---|---|
| 种子评测 `details` | 写死 `response_latency_p50/p95_ms = 320/890、410/1120、280/750` | `null` + `latency_note`，整条带 `simulated: true` |
| 种子模型 `model-001` | `status="deployed"` + `endpoint_url="http://127.0.0.1:8101/v1"` + `endpoint_status="healthy"`（8101 是 P10 自己的 FastAPI 端口，`/v1/*` 只会 404） | `deployed_simulated` + `endpoint_url=null` + `endpoint_status="simulated"`，`openai_compatible: false` |
| `POST /models/{id}/deploy` | `random.randint(8101,8199)` 拼一个看起来能调的地址 | 不返回任何地址，响应里写明「没有启动推理服务」 |
| 数据集统计 | 上传了文件仍返回 `random.randint(5_000_000,50_000_000)` 等假统计；标签分布/Token 分位是写死常量（注释还称「保持真实口径」） | 真算字节数、非空行数、重复行数、字符长度分位、可解析时的标签分布；`avg_tokens`/`token_histogram` 为 `null` 并列入 `unmeasured`；预置数据带 `provenance="seed_demo"`，UI 数字后加 `*` + 图例 |
| 训练时长 | `random.uniform(3600, 28800)` 冒充实测 GPU 时长 | `null`（曲线是瞬时生成的，报时长只会误导成本） |
| `/api/v1/stats` | `avg_accuracy` 无口径说明 | 加 `real_served_models: 0` + `metrics_provenance` |

**证据**：`p10-model-finetune/pytest-20261014.log`（**26 → 28 passed**，新增 3 条防回归：
真测上传统计 / 不造假端点 / 无真实服务）、`live-verify-20261014.md`（**运行中 8101 端口**的接口输出，
服务经 `supervisor.py restart p10 --takeover` 重启）、两张无头截图（评测页模拟声明、模型卡「服务地址：无」）、
新建 `p10-model-finetune/INDEX.md` 逐条对应门禁。顺带补了 `#evaluation` 这类页签深链。

**P10 门禁仍未满足**（真实训练 / loss 曲线 / 前后评测对比 / OpenAI 兼容接口调通，四项全空），
按红线 8 保持「明确未完成」，不做假系统 —— 方案在 `00-总纲/07-P10微调算力方案.md`。

### 复核中确认「已不需要动」的两条旧账

- `agents.md`「已知未闭环 ②」（P02 浅色态被 `/`→`/login` 丢掉 `?cp-theme`）**已修复**：
  `web/src/app/layout.tsx:29` 从 Cookie 读主题供 SSR，`src/middleware.ts:21-31` 在重定向里显式带 `cp-theme`。
- P07 的「未提交且证据过期」由 D17 那轮返工解决（68 passed + 7 张截图 + 2 份评测），本轮不再触碰。

### 本轮未做（用户已定口径）

- P02 的 64 处令牌级对比度欠账（`--cp-ink3` 2.71:1、`--cp-success` 叠底 2.95:1）：**暂不动，登记为已知欠账**；
- P01 50 并发压测、P08 真实 ffmpeg 出片、P03 数据源、P04 拒答率与分块对比：本轮未排进；
- P09「与人工评分一致性」：改为**真人评分出真 Kappa**，工具与脚本见 D19。

---

## D19 · P09 删掉「AI 分 + 噪声」的假一致性 + 修复证据从未入库的系统性漏洞（2026-10-14 凌晨）

### 1. P09 人机一致性：从自我相关改成真人盲评

原实现 `app/main.py`：`conv.human_score = conv.score.overall + random.uniform(-12, 12)`，
再用它算 Cohen's Kappa —— **让 AI 和它自己比**，Kappa 必然虚高；README 还预写「预期 Moderate-Substantial」。
按用户选定的路线（真人评 20~30 条出真 Kappa）改造：

- 预置人工分一律 `None`；只能由真人经**评分台**写入，落盘 `data/human_labels.json`（重启自动回填）；
- 新增 `web/label.html` + `GET /api/v1/labeling{,/queue}` + `GET/POST/DELETE /api/v1/labeling/{id}`；
- **盲评**：队列与单条视图在接口层就不返回 AI 分，提交后才揭示差值，防锚定；
- 人工分沿用与 `_rule_based_score()` 同一套五维权重（25/25/15/20/15），否则两边分数不可比；
- 真人评分不足 5 条时 `GET /api/v1/agreement` 返回 `kappa: null` + 原因，**不出数**；
  出数时响应自带 `provenance`（评分者 / 时间范围 / 是否盲评 / 权重 / 被评会话是 P01 真实导入还是演示预置）
  与 `limitations`（单人评分无 inter-rater 校验、四档阈值影响结果、小样本置信区间宽）。

**证据**：`p09-ai-sales-assessment/pytest-20261014.log`（**30 → 41 passed**，新增
`tests/test_labeling.py` 5 条：盲评无 AI 分、按权重算分且落盘、四类非法入参被 422、撤销清干净、
**用混淆矩阵独立反算 Kappa 校验公式**；`test_agreement_statistics` 从「断言假样本量 22」改为
「真人评 6 条后断言 + 断言 `mock_notice` 必须消失」）+ 运行中 8090 端口实测
（`/api/v1/labeling` → `labeled_count:0, pending:22`；`/api/v1/agreement` → `kappa:null`；
`/api/v1/conversations` 前 5 条 `human_score` 全 `null`）+ 评分台截图。
`tests/conftest.py` 新增 `_isolate_human_labels`，把 `LABELS_PATH` 指向 `tmp_path`，
**避免跑测试污染真人标注**。

**门禁状态**：工具与口径已就位，**报告尚未出具**（要等真人评分，见 README「人工质检评分台」一节）。

### 2. 系统性漏洞：`_evidence/` 下的日志从来没进过仓库

`.gitignore:27` 有一条全局 `*.log`，而验收证据按规则 04 正是以 `*.log` 形式存放 ——
`git ls-files _evidence | grep -c '\.log$'` 实测为 **0**，即：

> 远端仓库里只有 INDEX.md 的结论数字（「162 tests passed」「36/36 一致」…），
> **一份可复核的日志都没有**，53 个日志文件（约 2.4 MB）全部只在本地。

已加例外规则 `!_evidence/**/*.log` / `!_evidence/*.log`（`_runtime/` 仍整体忽略），
并为 `projects/p09-ai-sales-assessment/data/human_labels.json` 开了白名单
（真人标注是 Kappa 的唯一数据来源，必须可被复核；该文件只含分数/评语/署名，不含客户对话内容）。

### 3. 顺带纠正一处历史数字

`_evidence/INDEX.md` 记 P09 为「34 全绿」，而 `p09-ai-sales-assessment/pytest-20261013.log` 实际是
**30 passed** → 已在 `p09-ai-sales-assessment/INDEX.md` 里以日志为准登记。



## D20 · 用户反馈：「启动之后好多黑色弹窗」→ 静默一键启动 + 桌面应用程序（2026-10-14 上午）

详情见 `_evidence/shell/D20-silent-launch-desktop-app.md`（三条根因逐条实测 + A/B 取证 + 时间线）。

**根因不是「没做静默」，是标志位在本机失效**：`_tools/supervisor.py` 用 `DETACHED_PROCESS` 起服务，
但 Win11「默认终端应用 = Windows Terminal」会照样接管并给每个控制台子进程开一个可见窗口 ——
探针复用 `spawn()` 真实路径实测 **10 个服务 → 11 个 `CASCADIA_HOSTING_WINDOW_CLASS` 窗口**。
A/B 对照（同一条命令行只换标志位）：`DETACHED_PROCESS` 弹 1 个 / `CREATE_NO_WINDOW` 弹 0 个
（`_evidence/shell/D20-flags-ab-test.log`）。改标志位后，`DETACHED_PROCESS` 原本保证的
「父脚本退出服务仍活」没有丢。

**顺带照出来一个真 bug**：`p01-commerce` 在无控制台路径下必崩 ——
`external/ecommerce-service-backend/main.py:14` 的 `print("🚀 …")` 在 stdout 被重定向成日志后按
GBK 编码 → `UnicodeEncodeError`，进程直接退出。老路径每个服务都带窗口，所以从没暴露；
15 端口探活也一直把它记成「未启动」而不是「起不来」。修法：`spawn()` 给子进程加
`PYTHONIOENCODING=utf-8`（只动 stdio，不改各模块读中文文件的默认编码）。
第三条：桌面入口是 `pythonw`，`resolve_python()` 会跟着把 shell 网关跑成 `pythonw serve.py`
（GUI 子系统不吃 `CREATE_NO_WINDOW`），已归一化回同目录 `python.exe`。

**新入口**：`_tools/launcher.py`（静默编排 start/stop/status/open，命名互斥量防连点，
只在服务没起来时弹一个框）+ `_tools/make_desktop_app.py`（brand.json logo → 多尺寸 ico →
系统自带 `csc.exe` 编 `_tools/dist/云枢智能.exe`，41,984 字节零额外依赖 → 桌面三个快捷方式：
一键启动 / 停止服务 / 服务状态）。

**实测**：双击图标后 170s 窗口监视「合计新窗口 6，其中控制台类 **0**」；
`08:48:07` 起 15 个服务 → `08:48:09` 门户就绪并自动开浏览器（+2s）→ `08:48:19` **15/15 在线**（+12s，暖启动）；
「停止服务」`08:52:02 → 08:52:10` **全部端口已释放**（8s，复测 0/15）；再次双击后 `status` = 15/15。
日志 `_evidence/shell/D20-launcher.log`、`D20-supervisor-status.log`、`D20-window-watch-silent-start.log`。

**边界**：`start-all.bat` 仍开它自己那一个窗口（它就是给人看进度并 `pause` 的，但不再弹服务窗口）；
P01 自带 `tools/dev_up.py` 的 `CREATE_NEW_CONSOLE` 是它文档写明的模块级设计，统一平台路径不经过它；
12s 是依赖已装的暖启动，首次冷启动含 `uv sync` / `npm install` 未测；**没有公网入口这条不变**。

## D21 · 用户反馈：客服页「加载历史消息失败 / 加载订单列表失败」→ 一键启动现在带起 MySQL 容器（2026-10-14 上午）

**根因不在 P01 代码里**：P01 后端(18082) 与商城中台(18081) 都连 Docker 容器 `customer-service-mysql`
（`projects/p01-ai-customer-service/external/docker/docker-compose.yml` 发布 `127.0.0.1:3307:3306`）。
D20 的桌面「一键启动」只管 SERVICE_REGISTRY 里那 15 个业务进程，**不管 Docker** ——
本轮 Docker Desktop 引擎没运行 → 3307 无监听 → 两个接口 500，日志是
`OperationalError (2003, "Can't connect to MySQL server on '127.0.0.1'")`。
`_evidence/shell/INDEX.md:90` 记过一次同名报错（那次是 18081 没起、MySQL 在听），这次正好相反。

**修法（根因，不是绕过）**：`_tools/launcher.py` 新增 `ensure_mysql()`，在起业务进程之前：
3307 已在听就直接过；没在听则先 `docker info` 探引擎，引擎没跑就 `Popen` 拉起 Docker Desktop 并轮询等它，
再 `docker compose -f <那份 compose> up -d`，最后等端口出现。**宿主端口从 compose 解析**（`mysql_host_port()`），
不另抄常量，避免与唯一真源漂移。失败不静默：并进 D20 那条「有依赖没就绪」提示框，
文案点名「客服页会报加载历史消息/订单列表失败」。不想碰 Docker 用 `pythonw _tools\launcher.py start --no-mysql`。

**实测**：引擎已跑时把容器 `docker stop` 掉，`ensure_mysql()` **1.8s** 把它带回 3307；
引擎冷启动那条分支（`Popen` Docker Desktop + 轮询 `docker info`）本轮是手工走通的 —— **15.9s 就绪**，
代码是同一段逻辑，但没有在引擎关闭状态下端到端复跑，按未测对待。
复验走浏览器同一条 vite 代理路径：`/api/chat/history?sender_id=u1001` → **200、106 条真实历史消息**；
`/commerce/users/u1001/orders` → **200**（iPhone 15 Pro ¥8999 待发货、小米恒温电热水壶 ¥149 运输中等）；
页面 DOM 断言 `err_history=false, err_orders=false` → 截图 `p01-ai-customer-service/P01-mysql-restored.png`。
逐条见 `_evidence/p01-ai-customer-service/INDEX.md` 新增节。

**边界**：只并入了 P01 的 MySQL。同一台 Docker 上 `milvus-standalone / milvus-minio / milvus-etcd`
本轮实测仍是 `Exited`（P04 的向量库），P03 的 MySQL(3306)/RAGFlow(9380) 也仍未启动 ——
**P04 端口 8041 在听不等于检索可用**，这两条要不要一起并进启动器，属需确认的动作，未擅自动手。

## D22 · 作品集首页文案重设计（2026-10-14）

**问题**：首页文案是「自证清单」口吻 —— 开篇先立靶子再辩解（"不是十个各自为战的 demo"）、数字与业务后果脱钩、
"关于作者"只有 30 字、六条 ADR 只写结论不写代价。

**改了什么**（只改文案，未动视觉令牌与布局）：
- hero：主张从「能点开就跑」改为「十个模块跑在同一套中台里」；lead 先讲给谁做、闭环怎么转，再讲统一形态，
  把「每个指标可在 _evidence/ 复核 / 没测过的明写未测」下沉为第二句。
- 四个小节标题与导语重写：`十大能力模块 · 四层架构`、`一条数据闭环，六个工程决策`、`实测数据，以及它从哪来`、
  `真实 / 模拟边界`；六张 ADR 卡每条补上「为什么 + 代价」（如 ADR-0002 写清起因是 P03 前端把 8030 写成 8000 的真实故障）。
- 十张模块卡统一为「实测数字 / Mock 边界（真实… 模拟… 未闭环…）」两行式，数字一律照抄证据文件未作改动。
- 「关于作者与阅读路线」三条卡从「视角标签」改为「按 AI-FDE / 应用开发 / 工程化分别怎么聊、现场走哪条路径」。
- 登录模态与模块拦截文案改为说明真实行为（五种角色；服务没起来给启动命令而不是空白页）。
- statbar 新增「跨模块真实取数 3」：P02→P06、P07→P06（`app/services/data_platform.py:20` `api_url("p06", ...)`）、P09→P01。

**顺手修掉的两处不实文案**：
1. 边界节原写「P02 浅色态在 `/`→`/login` 跳转时会丢 `?cp-theme`（尚未修）」—— 实际已修：
   `web/src/middleware.ts:24-29` 显式把 `cp-theme` 带进重定向，`web/src/app/layout.tsx` 从 Cookie 读主题供 SSR。
2. 草稿曾把「非老板角色访问 P02 老板看板被 403」挂在**外壳登录**语境下 —— 与 ADR-0003 的 P02 例外冲突
   （外壳令牌不下发给 P02，P02 用自身 Cookie RBAC），已改为不暗示角色跨模块传递的表述。

**核对后主动删掉的表述**：「与各项目 README 的 mock 边界一节一一对应」—— P02 README 无该章节，P05 用
「七、边界与不做的事」，P06/P08/P09 只写「已知限制」，故改为指向 UI 标注 / 接口字段 / `_evidence/`。
> 由此暴露一条规范缺口：`.qoder/rules/02-技术规范.md` 要求每项目 README 含「已知限制与 mock 边界」，
> **P02 目前缺这一节**，未擅自动手补，登记待办。

**静态门户同步（`01-portfolio/index.html`）**：它是「不依赖这台笔记本、随时可打开」的那一版，hero 与文案与外壳同源，
因此同一套重写一并落上去（含 `<title>` 与 meta description），并重跑 `_tools/build_portfolio.py` 生成 `dist/index.html`。
顺带修掉该文件里两处与实测冲突的旧内容：

| 位置 | 原文 | 实况 | 依据 |
|---|---|---|---|
| P09 卡 | `34 项测试` | 41 项（同一文件下方的 565 卡里也写着 P09 41，自相矛盾） | `_evidence/p09-ai-sales-assessment/pytest-*.log` |
| P10 卡 / 边界卡 | `生命周期编排与部署形态真实可调用`、`真实：…OpenAI 兼容部署形态` | **不存在可调用的端点**，部署仅登记状态、`endpoint_url` 返回 null —— 原表述属把模拟当真实 | `projects/p10-model-finetune/` 接口与 AGENTS.md ⑥ |

另删去静态页与外壳都出现过的「与 README 第六节一一对应」——P02 README 无该章节（规范缺口，见上）。

**证据**：`_evidence/shell/2026-10-14_首页文案重设_hero.png`（1280×1500，未登录访客态首屏）、
`_evidence/shell/2026-10-14_首页文案重设_整页.png`（1440×7200，含十模块卡、六条 ADR、Ragas 对照表、边界节与关于作者）、
`_evidence/shell/2026-10-14_静态门户文案重设.png`（1280×4200，`01-portfolio/dist/index.html` 整页，十张模块截图正常渲染）。
前两张是 Edge headless 直抓 `http://127.0.0.1:8800/`，第三张抓的是构建产物。

**未做**：本轮没有新跑测试或评测，文案里的数字全部沿用 D1–D21 已登记的实测值；
`01-portfolio/index.html` 的源文件（非 dist）在本地直接打开时十张模块截图是坏的 —— 仓库里只有 `dist/img/`，
源目录 `01-portfolio/img/` 从未入库。属既有状态，未擅自改动，登记备查。

## D23 · P02 商品池「不能删除」→「点了没反应」：补删除能力 + 去掉对 window.confirm 的依赖（2026-10-14）

> 编号说明：先前误登记为 D21，与上面「一键启动带起 P01 MySQL 容器」（根 `agents.md` 亦按 D21 引用）撞号，
> 现改记 D23。模块内证据文件同步改名 `_evidence/p02/D23-商品池删除.md`。

**第一轮**：反馈「商品池商品不能删除」。不是权限或业务规则拦截，而是**两层都缺** —— `products.py` 只有
GET/POST/PATCH（全 api 目录唯一的 `@router.delete` 在 `stores.py`），`product-row.tsx` 行内只有「进入」链接。
补齐 `DELETE /api/v1/products/{product_id}`（编辑权限 + Workspace 归属，客服 403 / 未登录 401 / 跨 Workspace 404）
+ 三个入口（商品池列表行、工作台首页行、商品详情页头部）。级联清除 SKU 与库存档案/流水、平台映射、
竞品与监控快照、创意、生成任务、素材、推广链接与点击、经营数据、复盘、广告建议与实验、诊断、解析任务；
**`agent_runs` / `agent_approvals` 只置空 `product_id` 保留审计** —— 用 mapper 内省核过 Product 的级联子图
（24 表可达），唯一的洞就是 `agent_approvals.run_id` 没配外键级联，连删 AgentRun 会抛约束错误。

**第二轮**：上线后用户接着反馈**「点删除没反应」**。根因不在 P02：统一外壳 `shell/index.html:347` 把模块挂在
`sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-downloads"` 的 iframe 里，**缺
`allow-modals`** —— 沙箱帧内 `window.confirm()` 不弹窗、直接返回 `false`，而第一轮的守卫正是
`if (!confirmed) event.preventDefault()`，于是恒被判定成「用户取消」，浏览器根本不提交。
顺着这条还查出一个**早于本次就存在的缺陷**：店铺删除按钮（`store-delete-button.tsx`）是同一写法，
所以它在外壳里一直点不动；全站源码用 `confirm()` 的就这两处。
修法两条各自独立成立：① 商品删除改成**服务端渲染的两步确认页**（`/products/{id}/delete` 读出本次会连带
清除的**真实数量**并写明 Agent 审计只解除关联 → 按「确认删除商品」才 POST `/products/{id}/delete/confirm` →
回跳 `/products?product=deleted`），入口降级成普通 `<Link>`，**零 JS 依赖**；
② 外壳 sandbox 补 `allow-modals`（并把原因写成注释），店铺删除及各模块弹窗恢复可用。

**实测**：`_evidence/p02/pytest-20261014.log` **166 passed**（较 10-13 的 162 新增 4 条；级联用例连接层开
`PRAGMA foreign_keys=ON`，漏删任一张子表即像在 PostgreSQL 上一样抛约束错误，并先断言 18 张子表「删除前各有
数据」防止断言空过）；`_evidence/p02/product_delete_live.log` 实机 HTTP 序列（201 建临时商品+SKU+竞品 →
403/401 → 204 → 详情 404 → 商品池无残留）；删除后只读 SQL 复核 product_id 对应的 SKU/库存档案/库存流水/竞品/
推广链接与全库孤儿行均为 0，演示数据两轮跑完都回到原状 6 商品 / 3 店铺。
两步确认链路在「内置浏览器面板未打开 → 页面不水合（`document.hidden=true`、DOM 无 `__react*` 键）」的环境里
**反而能端到端验完**：入口 → 确认页（`SKU:1 竞品:1 推广链接:1`）→ 确认删除 → 回跳提示，以及上一轮没验成的
**取消分支**（确认页点「返回商品」→ `/products/7`，h1 仍是原商品名、未被删）。外壳回归：`127.0.0.1:8800/`
仍正常渲染，iframe `sandbox` 实测已含 `allow-modals`。

**边界**：店铺删除只改了外壳，它自己的 `confirm()` 写法没动，「在 iframe 里点店铺删除能弹窗」**没实测**
（自动化环境不水合 React，真点下去还会删掉演示店铺）；本条**没有截图**（无可视 surface
`NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`）；覆盖率未测量；PostgreSQL 侧未实机复跑，本机 P02 用 SQLite。
是否把店铺删除也改成同款两步确认页，等一句话。
