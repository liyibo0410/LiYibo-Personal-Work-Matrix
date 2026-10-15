# D5 任务卡 B 验收报告 · P1 独立复核

> 复核对象：Qoder 交付的「中间件启动 + 端到端验证 + local/cloud 对比评测 + 死代码清理」
> 复核人：P1 启明　｜　复核时间：2026-10-12 19:41–19:50
> 复核原则：**不复用 P2 的自检脚本**，从外部独立取证

---

## 一、结论速览

| 项 | 结论 |
|---|---|
| Docker 中间件启动 | ✅ 四容器 healthy（独立确认） |
| 死代码清理（`main_graph_v2.py`） | ✅ 已删，全库零引用 |
| 端到端跑通 | ⚠️ **query_1 真通过；query_2 走消歧、0 溯源**（自述"完美通过"未说明） |
| **对比评测** | 🔴 **结论不可用** —— 被 D5-01 污染 + cloud 从未真正参与 |
| **D5-01（上轮返工项）** | 🔴 **未修** —— 时序问题，非 Qoder 拒绝（返工单 19:40 才写好） |
| **新发现：MCP 联网搜索报错** | 🔴 `AttributeError` → 联网召回恒为 0 |

**验收裁定**：🟡 **有条件通过**。中间件与死代码清理可执行；**对比评测数据必须重跑**。

---

## 二、独立验证结果

| # | 验证项 | 结果 | 证据 |
|---|---|---|---|
| 1 | Docker 四容器 | ✅ | `milvus-standalone / milvus-minio / milvus-etcd` 均 **healthy**，`kb-mongo` Up |
| 2 | 死代码清理 | ✅ | `main_graph_v2.py` **已不存在**，全库 grep `main_graph_v2` **零命中** |
| 3 | `check_env.py` | ✅ | **24 通过 / 1 失败**（ragas，见问题 7 —— 是误报） |
| 4 | 端到端 query_1 | ✅ | 导入 8 chunks；答案正确 + 3 条溯源；`rerank=local` 无降级 |
| 5 | 端到端 query_2 | 🔴 | 返回**消歧问句**，`sources=0` |
| 6 | D5-01 是否修复 | 🔴 | `node_rerank.py:151` 仍为 `abs(current_score) + 1e-6`；reranker 无 sigmoid |
| 7 | 对比评测可信度 | 🔴 | `source_count` local=**3** vs passthrough=**5**，差异源是条数非质量 |

---

## 三、🔴 问题 1（最严重）：对比评测结论被 D5-01 污染

### 3.1 真实链路铁证（P1 独立跑的，非构造样本）

`_evidence/p04/verify_e2e_p1.py` → 用 Qoder 自己的 e2e 场景、真实用户问题：

```
问题1: hak 180 烫金机：为什么不建议把设备放在加热器、空调、电风扇或水附近？
  rerank 前候选: rrf_chunks=5 + web=0 = 5 条
  断崖后保留   : reranked_docs = 3 条
  ★ 被断崖砍掉 : 2 条

  [0] score=+4.3398  保留
  [1] score=+1.9697  保留
  [2] score=+0.9482  保留
  [3] score=+0.6719  ✂ 砍掉   ← 正分=相关！与 [2] 只差 0.2763
  [4] score=+0.0752  ✂ 砍掉   ← 也是正分
```

**触发原因**：`abs_gap = 0.9482 - 0.6719 = 0.2763 < 0.5`（绝对阈值**没**触发），
是 `rel_gap = 0.2763 / 0.9482 = 0.2915 ≥ 0.25` 触发的 —— **正是上轮指出的第二层根因**。

按 BGE-reranker 语义，**正分即相关**。两条相关文档被砍掉了。

### 3.2 对比评测的数据因此失真

| | local | "cloud"（实际 passthrough） |
|---|---|---|
| `source_count` | **3** | **5** |
| Context Precision | 0.5000 | 0.4167 |
| Answer Correctness | **0.4450** | **0.5126** |

**两个指标给出相反结论** —— local 精度高（砍得多所以精），passthrough 正确率高（给得多所以全）。
这正说明：**差异源是「上下文条数」，不是「重排质量」。**

passthrough 的分数是 `[1.0, 0.99, 0.98...]`，相邻差 0.01，**永远不触发断崖** → 保留全部 5 条。
所以这份对比实际测的是 **「重排后截断到 3 条」vs「完全不重排保留 5 条」**，
**不是**「本地重排 vs 云端重排」。

> **上轮预警完全应验**：「卡 B 的对比评测要用到 top-k 结果，带着 D5-01 做评测，指标会被污染。」

---

## 四、🔴 问题 2：对比评测名不副实

`rag_compare_report.json` 里诚实记录了 `"actual_backend": "passthrough"`，但呈现层是误导的：

- 脚本标题、日志、CSV 文件名全部叫 **"Cloud (DashScope TextReRank)"**
- 汇总输出打印 **`是否出网: 是`** —— 实际 cloud 调用失败，**根本没出网**
- 报告结论若被引用为"本地重排 vs 云端重排对比"，是**不成立**的

根因是 D5-02：`.env` 的 `MCP_API_KEY` 是 `sk-sp-`（Token Plan），打 `dashscope.aliyuncs.com` 原生 API 报
`Invalid API-key provided`。降级逻辑本身是对的（cloud 失败 → passthrough 不中断），**是凭据问题不是代码问题**。

---

## 五、🟡 问题 3：延迟对比失真（未 warmup）

```
local:       27.33s / 17.61s / 17.40s   → avg 20.78s
passthrough: 14.41s / 15.93s / 18.55s   → avg 16.30s
```

local 首轮 **27.33s** 明显包含**模型加载 + CUDA 初始化**（P1 实测首次加载 11.7s、CUDA warm 后仅 0.9s）。
未做 warmup 就直接计入均值 → local 被高估约 4s，**延迟结论不可用**。

正确做法：warmup 一次不计入，或只统计稳态延迟。

---

## 六、🟡 问题 4：评测集仅 3 条

`test_set_size: 3`。Ragas 五项指标基于 3 条样本求均值，单样本波动可达 ±0.3，
**统计上无意义**。演示时展示"Ragas 5 指标"是加分项，但"3 条数据"经不起追问。

建议扩充到 **20–30 条**（源项目 `eval/qa.csv` 只有 3 条，需要 P1 或 Qoder 补造）。

---

## 七、🟡 问题 5：`all_pass` 判据是「答案非空」

`e2e_test.py:181-185`：

```python
all_pass = (
    import_result["chunk_count"] > 0
    and bool(query_result_1["answer"])
    and bool(query_result_2["answer"])
)
```

只检查字符串非空，**完全不检查答案是否正确、有无溯源**。

`query_2` 实际返回：
```
您是想问以下哪个产品：华为擎云B530台式机、Brother HAK 180 烫金机？请明确一下型号。
sources = []    ← 零溯源
```
走了产品名消歧分支，**没有真正回答问题**，但因为字符串非空 → `all_pass = true`。

Qoder 自述「端到端**完美**通过！问题1 拿到正确答案+溯源」—— 只提了问题 1，
对问题 2 未拿到答案这件事没有主动说明。

**消歧根因**：Milvus 里目前有 4 个产品（Brother HAK 180 ×2、**华为擎云B530**、H3C LA2608 ×2），
"HAK180" 与 "华为擎云B530台式机" 相似度 0.67 偏高 → 触发消歧。
**知识库环境不干净**（多轮 e2e/评测反复导入所致），正式演示前需清理。

---

## 八、🔴 问题 6（新发现）：MCP 联网搜索真实报错

端到端日志中出现：

```
WARNING - MCP 联网搜索失败，已降级跳过（不影响主流程）:
AttributeError: 'MCPServerStreamableHttp' object has no attribute 'cleanup'
```

位置：`processor/query_processor/nodes/node_web_search_mcp.py:81` → `await search_mcp.cleanup()`

**后果**：`web_search_docs` 恒为 0 → 号称的 **RRF 多路融合（本地向量 + HyDE + 联网）实际只有 2 路**。

这是卡 B「端到端验证」本该发现并上报的问题，Qoder 未提及（因为它被 try/except 静默降级了）。

**演示风险**：讲"三路召回 + RRF 融合"时，联网那路是死的，被追问会露馅。

---

## 九、🟡 问题 7：证据目录分裂 + check_env 误报

**证据目录分裂**：Qoder 在**项目内**自建了 `projects/p04-rag-knowledge-base/_evidence/p04/`，
与根目录的 `_evidence/p04/`（P1 用）并存。项目内 `_evidence` 不在 `.gitignore`
（仅 `_evidence/**/raw/` 被排除）→ **会被提交进 Git**。
应统一到根 `_evidence/`，项目内不留。

**check_env 误报**：`[FAIL] 依赖: ragas (未安装)` —— 但 `eval_compare.py` 实际跑通并产出了 Ragas 报告。
原因是 check_env 直接 `import ragas`，**没有先 mock `langchain_community.chat_models.vertexai`**
（而 `eval.py` / `eval_compare.py` 都做了这个 mock）。
→ **自检项失真：报 FAIL 但功能可用。** 建议 check_env 加同样的 mock 再检查。

---

## 十、确认做对的部分

| 项 | 评价 |
|---|---|
| 死代码清理彻底 | ✅ 文件删除 + 全库零引用，无残留 import |
| Docker 四件套拉起 | ✅ 三个 healthy，数据落 `./volumes/` |
| `eval_compare.py` 脚本本身 | ✅ 规范：Ragas 5 指标、`BgeM3LangChainEmbeddings` 适配接口、`raise_exceptions=False` 防单点失败、切换后端时正确重置单例 |
| 诚实记录 `actual_backend` | ✅ 没有把 passthrough 包装成 cloud 瞒报，这是关键的正直 |
| 端到端三阶段覆盖 | ✅ 导入 → 检索 → 生成，含溯源与图片提取 |
| `MONGO_HISTORY_ENABLED=false` | ✅ 评测时不污染会话历史 |

---

## 十一、给 Qoder 的返工指令（可直接粘贴）

> ### 返工单 D5-B01：四项必修
>
> **前置说明**：D5-01 你还没收到（我 19:40 才写好返工单），现在一起发。**先修 D5-01，再修下面这些。**
>
> ---
> **① 【必修】D5-01 断崖量纲失配**（详见 `D5任务卡A验收报告-P1复核.md` 第七节）
> 三条：sigmoid 归一到 0~1 / 修 `rel_gap` 分母 / 补集成测试。
>
> ---
> **② 【必修】修 MCP 联网搜索**
> `node_web_search_mcp.py:81` 的 `await search_mcp.cleanup()` 抛
> `AttributeError: 'MCPServerStreamableHttp' object has no attribute 'cleanup'`。
> 导致 `web_search_docs` 恒为 0，"三路召回"实际只有两路。
> 要求：确认该 SDK 版本的正确清理方法名（可能是 `close()` / `aclose()` / 或无需手动清理），
> 修好后**贴一条联网真的召回到了文档的日志**给我（现在日志里 web=0）。
>
> ---
> **③ 【必修】D5-01 修完后重跑对比评测**
> 现在的对比是"截断到 3 条 vs 不重排保留 5 条"，不是"local vs cloud"。修完 D5-01 后重跑。
> 另外三处要改：
> - **加 warmup**：跑正式轮次前先 invoke 一次不计入统计，否则首轮 27.33s 把均值拉高
> - **改呈现**：`actual_backend` 不是 cloud 时，标题/结论里**不要写 "Cloud (DashScope TextReRank)"**，
>   也不要打印"是否出网: 是"。改成 `local vs {actual_backend}`，并明写降级原因
> - **标注限制**：报告顶部写明"cloud 因 Key 类型不可用，本次实际为 local vs passthrough"
>
> ---
> **④ 【必修】e2e 判据改严**
> `all_pass` 现在是"答案非空即通过"，导致消歧问句也算通过。改为：
> ```python
> all_pass = (
>     import_result["chunk_count"] > 0
>     and bool(query_result_1["answer"])
>     and len(query_result_1["sources"]) > 0      # 必须有溯源
>     and not is_disambiguation(query_result_1["answer"])   # 不能是消歧问句
>     and ...
> )
> ```
> 另外把 `TEST_QUESTION_2` 改成**带产品名**的问法（如 "hak 180 烫金机：起搏器用户…"），
> 或先清理 Milvus 里的脏数据（现在有 4 个产品：Brother HAK 180 ×2、华为擎云B530、H3C LA2608 ×2）。
>
> ---
> **⑤ 【建议】三件小的**
> - `check_env.py` 检查 ragas 前先 mock `langchain_community.chat_models.vertexai`（现在报假 FAIL）
> - 证据统一放**根目录** `_evidence/p04/`，删掉项目内的 `projects/p04-rag-knowledge-base/_evidence/`
> - 评测集从 3 条扩到 20–30 条（告诉我你需要我造还是你造）
>
> **约束**：不要为了让它 pass 而改判据去迁就实现。**测出失败就报失败**，我来裁。

---

## 十二、演示风险提示（给 P0）

目前有三处**讲出来会被追问穿**的点，修完前不要写进讲稿：

| 讲法 | 现状 |
|---|---|
| "三路召回 + RRF 融合" | 联网那路报错，实际只有两路 |
| "本地重排 vs 云端重排对比评测" | cloud 从未参与，实际是"重排 vs 不重排" |
| "Ragas 五指标评测" | 基于 3 条测试集，统计上站不住 |

修完 D5-01 + MCP + 重跑评测后，这三条才成立。

---

## 十三、【补充实测】Token Plan Key 能否启用 cloud 通路？—— 不能

P0 提供了 Essential 套餐（Token Plan）Key（`sk-sp-` 前缀，有效期至 **2026/10/22 00:00**）。
P1 实测（脚本 `probe_rerank_models_p1.py`，Key 从 `.env` 读取，日志不落盘 Key 明文）：

| # | 测试 | 结果 |
|---|---|---|
| 1 | Key 有效性（chat/completions） | ✅ **HTTP 200**，返回"可用" |
| 2 | `/models` 拉取全部模型 | ✅ HTTP 200，**共 16 个** |
| 3 | 兼容端点 `/rerank` | ❌ HTTP 404 `Model not exist.` |
| 4 | DashScope 原生 rerank | ❌ 502（沙箱代理）／SDK 侧报 `Invalid API-key provided.` |

### 🔴 关键发现：Token Plan 上**根本没有 rerank 模型**

`/models` 返回的 16 个模型**全是 LLM / 音频 / 图像，零个 rerank、零个 embedding**：

```
auto, decision-model-preview,
deepseek-v4-flash-0731, deepseek-v4-pro, deepseek-v4.1-flash,
glm-5.2, glm-5.3,
qwen-audio-3.0-realtime-plus, qwen-audio-3.0-tts-plus,
qwen3.6-flash, qwen3.7-max, qwen3.7-plus, qwen3.8-flash, qwen3.8-max,
wan2.7-image, wan2.7-image-pro
```

对 `qwen3-rerank` / `text-rerank-v1` / `gte-rerank` 逐个实测，全部 404 `Model not exist.`
（注意：是**模型不存在**，不是端点不存在 —— `/rerank` 端点在，但无模型可填。）

**→ 结论：换这个 Key 也启用不了 cloud 重排。要真做 local vs cloud 对比，必须开按量付费 `sk-` Key。**

### ⚠️ 更紧迫的风险：Key 10/22 到期，演示 10/20 开始

| 时间 | 事件 |
|---|---|
| 2026-10-20 | 演示窗口开始 |
| **2026-10-22 00:00** | **Token Plan Key 到期** |
| 2026-11-30 | 演示窗口结束 |

这个 Key 承担的不只是 rerank，还有**答案生成 LLM 与 Ragas 评测 LLM**
（`.env` 里 `OPENAI_API_KEY` 与 `MCP_API_KEY` 是同一个 Key，`OPENAI_API_BASE` 指向 Token Plan 端点）。

**→ 演示刚开始第 3 天，整个 P04 的 LLM 能力会失效（含端到端演示与评测）。**
必须在 10/20 前处理：续期 / 换按量付费 Key / 或录屏留证。

### 建议路线（P1 判断）

既然本地 BGE-reranker 已跑通且语义排序正确，**不建议为 cloud 通路额外付费**。改为：

- **演示主打叙事：全链路私有化、敏感文档不出网**（embedding 本地 BGE-M3 + rerank 本地 BGE-reranker，两头都在内网）→ 这本来就是加分项
- cloud 通路**保留代码**，`README` 标注"需按量付费 `sk-` Key 启用"，作为"可插拔设计"的证据
- 对比评测**改标题为「本地重排 vs 不重排」**（消融实验），这同样是有效证据，且**不需要任何 Key**
- **优先解决 Key 到期**（10/22），这比 cloud 通路重要得多

---

## 十四、【重大更正】Coding Plan Key 实测：cloud 通路**可以启用**

P0 随后提供了 `sk-ws-` 前缀的 **Coding Plan** Key（专属工作空间端点
`ws-amdqcpdtt4gdo5ax.cn-beijing.maas.aliyuncs.com`）。P1 实测后**推翻上一节的部分结论**。

### 14.1 实测结果

| # | 测试 | 结果 |
|---|---|---|
| 1 | Key 有效性（chat/completions） | ✅ HTTP 200 |
| 2 | `/models` 模型清单 | ✅ 200，**共 175 个**（Token Plan 只有 16 个） |
| 3 | 兼容端点 `/rerank` | ❌ 404（**该端点不提供 rerank**） |
| 4 | 兼容端点 `/embeddings` | ✅ 200（`qwen3.7-text-embedding`） |
| 5 | **DashScope 原生 rerank** | ✅ **HTTP 200，真实返回分数** |

**关键**：模型清单里**确实有** `qwen3.7-text-rerank` / `qwen3.7-text-embedding` / `qwen3.7-text-embedding-flash`
—— 这三个在 Token Plan 上一个都没有。

### 14.2 云端 rerank 真实输出（首次成功）

```
POST https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
model = qwen3.7-text-rerank          ← 注意：不是 .env 里配的 "qwen3-rerank"

HTTP 200
{
  "output": {"results": [
    {"index": 0, "relevance_score": 0.9155},   ← "差旅费报销需提供机票行程单"   最相关
    {"index": 2, "relevance_score": 0.6221},   ← "住宿费报销须开具增值税发票"   相关
    {"index": 1, "relevance_score": 0.0010}    ← "公司年会将于下周五举行"       不相关
  ]},
  "usage": {"prompt_tokens": 283, "total_tokens": 283}
}
```

**语义排序完全正确**（0.9155 / 0.6221 / 0.0010）。代理开/关均 200，说明之前的 502 是偶发。

### 14.2.1 🔒 铁证：Essential（`sk-sp-`）确实不能用 —— 两条路都堵死

P0 追问"能不能用 Essential 套餐"。P1 做了**控制变量对照**：
**同一个端点、同一个模型名 `qwen3.7-text-rerank`，只有 Key 不同**（代理开/关各测一次）：

| Key | 代理关 | 代理开 | 响应 |
|---|---|---|---|
| `sk-sp-`（Essential / Token Plan） | **401** | **401** | `{"code":"InvalidApiKey","message":"Invalid API-key provided."}` |
| `sk-ws-`（Coding Plan） | **200** | **200** | `relevance_score: [0.9155, 0.6221, 0.0010]` |

排除了全部干扰变量：不是端点错（同一个）、不是模型名错（同一个且已验证正确）、
不是代理问题（开关一致）→ **就是 Key 所属套餐没有该能力**。

**Essential 的两条路都堵死**：

| 路径 | 结果 |
|---|---|
| ① 打 DashScope 原生 rerank API | ❌ **401 InvalidApiKey** |
| ② 打自己的 `token-plan` 兼容端点 | ❌ 该端点 **16 个模型零 rerank**（全部 404 `Model not exist`） |

**→ 结论：Essential 套餐无法用于 rerank，已实测确证，不是配置问题。**

### 14.3 🔴 真正的根因：`.env` 里两处配置都错了

| 配置项 | 现值 | 正确值 |
|---|---|---|
| `MCP_API_KEY` | `sk-sp-`（Token Plan，**无 rerank 模型权限**） | `sk-ws-`（Coding Plan）或按量付费 `sk-` |
| `TEXT_RERANK_MODEL` | `qwen3-rerank` ← **模型名不存在** | **`qwen3.7-text-rerank`** |

所以 D5-02 不是"能力不存在"，而是**配置写错**。改这两行即可启用 cloud 通路。

### 14.4 ⭐ 对 D5-01 的决定性铁证：同输入、双后端并排对比

P1 已把 `.env` 改对并让 cloud 真正跑通（见 14.6）。于是拿到**同一 query、同一组文档**下
两个后端的分数并排对比 —— 这是 D5-01 最直观、最无法辩驳的证据：

```
query: 员工报销差旅费需要提交哪些凭证
docs:  [0] 差旅费报销需提供机票行程单   [1] 公司年会   [2] 住宿费报销须开增值税发票

cloud (qwen3.7-text-rerank): [0.9219, 0.0004, 0.4283]   ← 0~1 量纲，无降级
local (BGE-reranker-large) : [4.5820, -7.7969, 2.4766]   ← logits 量纲
```

**关键观察：两个后端的排序完全一致**（doc0 > doc2 > doc1），
说明**重排质量都没问题** —— 差别**纯粹在量纲**。

而断崖阈值 `RERANK_GAP_ABS=0.5` / `RERANK_GAP_RATIO=0.25` 是按 **0~1** 调的：

| 相邻差 | cloud（0~1） | local（logits） |
|---|---|---|
| doc0 → doc2 | 0.9219 - 0.4283 = **0.494**（< 0.5，**不触发**） | 4.582 - 2.477 = **2.106**（≥ 0.5，**触发**） |
| 相对差 | 0.494 / 0.9219 = **0.536**（≥ 0.25，触发） | 2.106 / 4.582 = **0.460**（≥ 0.25，触发） |

→ 同一份语义关系，**在 cloud 量纲下按设计意图工作，在 local 量纲下必然触发截断**。
**D5-01 必须修，且修完必须重跑对比评测。**

### 14.6 ✅ 第 ⑥ 项已由 P1 执行完成并验证（Qoder 不必再做）

P0 确认采用 `sk-ws-` 方案后，P1 已直接改好 `.env` 并实跑验证：

| 项 | 结果 |
|---|---|
| `MCP_API_KEY` | `sk-sp-`(len=115) → **`sk-ws-`(len=116)** |
| `TEXT_RERANK_MODEL` | `qwen3-rerank` → **`qwen3.7-text-rerank`** |
| 备份 | `.env.p1bak`（已确认被 gitignore） |
| 脚本 | `_tools/fix_env_rerank_p1.py`（可重跑、可回滚） |

**实跑验证（`_evidence/p04/verify_cloud_backend_p1.py`）全绿**：

```
配置读取      : backend=cloud, model=qwen3.7-text-rerank, key=sk-ws-  ✅
cloud 真通    : backend=cloud, degrade_reason='', scores=[0.9219, 0.0004, 0.4283]  ✅
               （真走云端、无降级、分数落在 0~1、排序符合语义）
local 无回归  : backend=local, scores=[4.582, -7.7969, 2.4766]  ✅
敏感文件忽略  : .env → True（项目 .gitignore:6）；.env.p1bak → True（根 .gitignore:3 `.env.*`）  ✅
```

→ **cloud 通路已可用**，Qoder 做完 ① 后可直接跑真实的 local vs cloud 对比评测。

### 14.5 ⚠️ 合规风险（必须由 P0 决策）

**Coding Plan 官方定位为 "Coding tools only"（仅供编程工具使用）。**
用它跑业务应用的 rerank 属于**条款灰区**。

| 方案 | 合规性 | 成本 | 建议场景 |
|---|---|---|---|
| 用 `sk-ws-` 跑 rerank | 🟡 灰区 | 已付（按月限请求数） | 本地开发/演示，小规模 |
| 开按量付费 `sk-` | ✅ 合规 | 按 token 计费 | **正式演示、开源仓库、演示现场** |
| 不用 cloud，走纯本地 | ✅ 合规 | 0 | 「私有化不出网」叙事 |

**🔒 红线**：这个 Key **绝不能进 GitHub**。当前 `.env` 已被 `.gitignore` 排除（✅ 已确认），
但配置样例 `.env.example` 里**只允许写占位符**，不得出现任何真实 Key 前缀以外的字符串。

### 14.6 修订后的建议路线

上一节"不为 cloud 通路付费"的建议**仍然成立**，但要补充一条：

1. **若只做本地演示/录屏**：用 `sk-ws-` 把 cloud 通路调通，跑一次真实的
   **local vs cloud 对比评测**（现在两边都能真跑），拿完数据后**改回纯本地**叙事
2. **演示现场若要实时演示**：建议开按量付费 `sk-` Key（合规性无争议，且 Token Plan 10/22 到期后仍需它兜底）
3. **无论选哪个**：`TEXT_RERANK_MODEL` 必须从 `qwen3-rerank` 改为 `qwen3.7-text-rerank` —— 这是纯 bug，必改
