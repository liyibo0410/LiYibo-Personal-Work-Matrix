# D5 任务卡 A 验收报告 · P1 独立复核

> 复核对象：Qoder 交付的「Reranker 双后端（local / cloud）+ 三级降级」
> 复核人：P1 启明　｜　复核时间：2026-10-12 19:30–19:40
> 复核原则：**不复用 P2 的自检脚本**，从外部独立取证；「P2 说完成了 → P1 必须实跑」

---

## 一、结论速览

| 项 | 结论 |
|---|---|
| 卡 A 主功能（双后端 + 三级降级） | ✅ **实现正确**，15/15 测试独立复跑通过 |
| 代码质量 | ✅ 高：签名不变、依赖缺失不崩、单例延迟加载、状态可查询 |
| **新引入缺陷 D5-01** | 🔴 **中高**：本地 logits 量纲与断崖阈值失配 → **全相关文档被砍到下限 3 条** |
| 附带发现 D5-02 | 🟡 cloud 通路当前不可用（`sk-sp-` Token Plan Key 调不动 DashScope 原生 API） |
| **验收裁定** | **有条件通过** —— 主功能可用，但 D5-01 必须在卡 B 之前修掉 |

**一句话**：`rerank_documents()` 这个函数本身写得没问题；问题出在**它的输出喂给下游断崖检测时，量纲变了，而下游阈值没跟着变**。Qoder 只测了自己的函数，没测下游链路。

---

## 二、独立验证（P1 自写脚本，不复用 Qoder 的 verify_reranker.py）

脚本：`_evidence/p04/verify_reranker_p1.py`、`_evidence/p04/verify_cliff_scale_p1.py`
日志：`verify_reranker_p1.log` / `verify_reranker_p1.json`、`verify_cliff_scale_p1.log` / `.json`

### 2.1 复跑 Qoder 的 15 项测试（确认数字属实）

```
platform win32 -- Python 3.11.15, pytest-9.1.1
collected 15 items ... 15 passed, 4 warnings in 26.41s
```

与 Qoder 自报的 15/15 **一致**。且抽查了测试代码质量：

- `test_local_fails_cloud_succeeds` 用 mock 的 dashscope，**断言了具体分数 0.95/0.30/0.70 且 `backend=="cloud"`** → 是真验证，不是"只要不抛异常就算过"的假阳性 ✅
- `test_top1_consistency` 在注释里**诚实说明**"cloud 需真实 API Key，测试环境不可用，只验证 local 排序" ✅（但**测试名有误导性**，见第四节）
- 依赖缺失、路径不存在、非法 backend 三条降级路径都断言了 `backend` 的实际取值，而非仅断言"不抛异常" ✅

### 2.2 P1 独立验证结果（8 项：7 PASS / 1 FAIL）

| # | 验证项 | 结果 | 实测证据 |
|---|---|---|---|
| 1 | 真实 `.env` 下 backend=local 且模型路径存在 | ✅ PASS | `backend=local, device=cuda:0, fp16=True, path_exists=True` |
| 1b | CUDA 自动检测生效 | ✅ PASS | `device=cuda:0`（RTX 4060 被正确识别，不再是 cpu） |
| 2 | local 语义排序高相关 > 不相关 | ✅ PASS | 最弱高相关 `-1.6885` > 最强不相关 `-7.6875` |
| 3 | local 输出为 logits 量纲（非 0~1） | ✅ PASS | 范围 `-9.4844 ~ +5.0547` |
| **4** | **全相关文档未被过度截断** | 🔴 **FAIL** | **6 条全相关 → 只保留 3 条** |
| 5 | 单例缓存 | ✅ PASS | 首次 11.70s（含 CUDA 初始化）→ 后续 0.0324s，**361x** |
| 6 | 降级路径 local 失败 → passthrough | ✅ PASS | `backend=passthrough`，不抛异常 |
| 7 | 真实配置下主入口走 local | ✅ PASS | `backend=local, degrade=''` |

### 2.3 语义排序实测（P1 自己的样本，未用 Qoder 的）

```
query: 员工报销差旅费需要提交哪些凭证
  Top-1: +5.0547 | 差旅费报销需提供机票行程单、酒店发票、打车票据...   ← 高度相关
  Top-2: +3.2637 | 报销凭证包括增值税发票、行程单和付款记录...        ← 高度相关
  Top-3: -1.6885 | 报销流程：员工提交 → 部门审批 → 财务复核...        ← 高度相关
  Top-4: -1.8506 | 差旅报销标准按职级划分，一线城市住宿上限...        ← 弱相关
  Top-5: -7.6875 | 公司年会将于下周五举行...                          ← 不相关
  Top-6: -9.4844 | 园区食堂本周起供应夜宵...                          ← 不相关
```

**语义排序完全正确** —— 三条高相关占据 Top-3，两条不相关垫底，弱相关居中。本地 BGE-reranker-large 推理本身没问题。

---

## 三、🔴 缺陷 D5-01：断崖检测与本地 logits 量纲失配

### 3.1 现象

`processor/query_processor/nodes/node_rerank.py:91-93` 的断崖阈值是按**云端 0~1 分**调的：

```python
RERANK_GAP_ABS: float = 0.5      # 绝对阈值
RERANK_GAP_RATIO: float = 0.25   # 相对阈值
```

而本地 BGE-reranker 输出的是 **logits，范围约 -10 ~ +5**（实测 `-9.48 ~ +5.05`），跨度是云端的 **15 倍**。

### 3.2 实测证据（两个场景，输入均为 6 条）

| 场景 | 断崖保留 | 判定 |
|---|---|---|
| **6 条全部语义相关** | **3 / 6** | 🔴 砍掉 3 条相关内容 |
| 6 条混合（3 高相关 + 1 弱 + 2 不相关） | **3 / 6** | 🟡 恰好等于下限，动态性丧失 |

`RERANK_MIN_TOPK = 3` 是硬下限 → **local 模式下 top-k 事实上退化成恒定 3 条**，断崖检测失去"动态截断"的设计意图。

### 3.3 根因（两层）

**第一层：绝对阈值量纲失配**
logits 相邻分差动辄 1~5，`abs_gap >= 0.5` 几乎恒成立。

**第二层（更致命）：相对阈值分母趋零 → 数值爆炸**
```python
rel_gap = abs_gap / (abs(current_score) + 1e-6)
```
logits 的**正负分界就在 0 附近**，而 logits 落在 0 附近是高频事件。分母趋 0 时 `rel_gap` 爆炸 → 必然触发。

实测这一对：
```
idx=2: -0.6636 -> -0.8687 | abs_gap=0.2051  rel_gap=0.3091  <== 触发断崖
```
`abs_gap` 只有 **0.2051**（语义上几乎无差别，本不该触发），却因为 `rel_gap = 0.2051 / 0.6636 = 0.309 ≥ 0.25` 被截断。**这是分母放大的假信号。**

### 3.4 影响

- **静默降低召回质量**：RAG 召回 10 条 → rerank 后本应保留 5~6 条喂给 LLM，**实际只喂 3 条** → 答案漏信息
- **不报错、不崩溃**，只有对比 top-k 数量才看得出 → 典型的"埋着未爆"
- **面试场景风险**：如果被问到"你的 top-k 为什么是 3"，答不出所以然
- 原项目纯 cloud 模式下**不存在**此问题 → **卡 A 新引入的回归**

### 3.5 修复方案（P1 建议，按优先级）

| 方案 | 做法 | 评价 |
|---|---|---|
| **A（推荐）** | `_rerank_local()` 返回前对 logits 做 **sigmoid** 归一到 0~1，与 cloud 对齐；原始 logits 保留在内部供 debug | 最小改动、阈值不用动、分数可直接展示。实测：全相关场景由 3 条 → **4 条** |
| B | 阈值按 backend 自适应（local 用更大的 `GAP_ABS`），并把 `rel_gap` 分母改为**全局分数跨度** `(max-min+ε)` | 保留 logits 区分度，但阈值要维护两套 |
| C | logits 天然以 **0 分为相关/不相关分界**，改用"截断在最后一个非负分之后" | 最贴合 BGE 语义，但与 cloud 模式不统一 |

**无论选哪个，第 3.6 节的测试都必须补。**

### 3.6 必须补的防回归测试

```python
def test_cliff_does_not_over_truncate_related_docs():
    """回归防线：N 条全部语义相关的文档，断崖后应保留 >= N-2 条，不能砍到下限。"""
    # 1. 构造 6 条全部与 query 相关的文档
    # 2. 用真实 NodeRerank._step_3_cliff_cutoff 跑（不是自己复写逻辑）
    # 3. 断言 len(cut) >= 4
```

> 现有 15 项测试**没有一条**触及 `node_rerank.py` 的下游链路 —— 这正是缺陷类型学第 ④ 条
> 「函数层测了、传输层没测」。卡 A 的 blast radius 不止 `rerank_documents()` 本身。

---

## 四、🟡 附带发现 D5-02：cloud 通路当前不可用

真实调用云端重排：

```
RuntimeError: DashScope rerank 调用失败: Invalid API-key provided.
```

**根因**：`.env` 里 `MCP_API_KEY` 是 **`sk-sp-` 前缀（Token Plan）**，而 `dashscope.TextReRank.call` 打的是
`dashscope.aliyuncs.com` 原生 API。

这与总纲 `09-凭据与套餐配置说明.md` 第六轮的结论**完全一致**：

| 前缀 | 套餐 | 可用端点 |
|---|---|---|
| `sk-` | 按量付费 | `dashscope.aliyuncs.com` 原生 API ✅ |
| `sk-sp-` | Token Plan | **仅** `token-plan.cn-beijing.maas.aliyuncs.com` ❌ 打原生 API 报 401 |
| `sk-ws-` | Coding Plan | 仅编程工具 |

**影响**：
1. 三级降级里的 `local → cloud` 这一级**当前永远失败**，实际是 `local → passthrough`
2. 卡 B 要求的「local vs cloud 对比评测」**做不了**，除非换 `sk-` 按量付费 Key
3. 降级逻辑本身没错，是**凭据配置**问题，不是代码问题

**给 P0 的决策点**：是否开通按量付费 `sk-` Key 以启用 cloud 通路与对比评测？（¥50-100 量级）

---

## 五、确认正确的部分（不只挑毛病）

| 项 | 评价 |
|---|---|
| `rerank_documents()` **签名未变** | ✅ `node_rerank.py:98` 零改动接入 |
| 三级降级链路 | ✅ local → cloud → passthrough，每层都有日志记录，绝不向上抛异常 |
| `_try_import_flag_reranker()` | ✅ try/except 包 import，缺 FlagEmbedding 不崩溃 |
| 单例延迟加载 | ✅ 首次 11.70s（含 CUDA init）→ 后续 0.0324s，**361x**；失败态不缓存，下次会重试 |
| `get_last_rerank_status()` | ✅ 暴露实际后端与降级原因，让"静默降级"变得**可观测** —— 这是好设计 |
| `_rerank_passthrough` 保序递减 | ✅ `[1.0, 0.99, 0.98...]`，喂给断崖检测不会误触发 |
| CUDA 自动检测 `_auto_device()` | ✅ `BGE_RERANKER_DEVICE=cuda:0` 生效，RTX 4060 不再闲置 |
| `.env` / `.env.example` 同步 | ✅ `RERANK_BACKEND=local` 已写入；`.gitignore` 第 6 行含 `.env`，**未泄露** |
| 降级测试真实性 | ✅ 用 mock 并断言具体分数值与 backend，不是"不抛异常就算过" |

**对比上一轮 D4 的 3 个缺陷，本轮仅 1 个且是跨模块集成问题 —— Qoder 的实现质量在稳步提升。**

---

## 六、待改进（不阻塞，建议后续处理）

1. `test_top1_consistency` **名不副实**：叫"local vs cloud 一致性"，实际只测了 local 排序（注释里已诚实说明）。建议改名为 `test_local_top1_is_most_relevant`，或在有 Key 时跳过（`pytest.mark.skipif`）。
2. `pytest.mark.needs_model` **未在 `pyproject.toml` 注册** → 4 条 `PytestUnknownMarkWarning`。建议在 `[tool.pytest.ini_options]` 加 `markers = ["needs_model: 需要真实模型权重的集成测试"]`。
3. `backend=cloud` 失败时**直接跳到 passthrough，不再回退 local**（`reranker_http_utils.py:239`）——设计取舍，当前可接受，但建议注释写清理由。

---

## 七、给 Qoder 的返工指令（可直接粘贴）

> ### 返工单 D5-01：修复「本地 logits 量纲 × 断崖阈值」失配
>
> **问题**：你交付的 `utils/reranker_http_utils.py` 本身实现正确（15/15 通过，P1 已复跑确认）。但它的输出喂给下游 `processor/query_processor/nodes/node_rerank.py` 的断崖检测后，行为被改变了。
>
> **实测证据**（P1 独立跑的，脚本在 `_evidence/p04/verify_cliff_scale_p1.py`）：
> ```
> 本地 BGE-reranker 输出 logits，实测范围 -9.4844 ~ +5.0547（云端是 0~1）
> node_rerank.py:91-93  RERANK_GAP_ABS=0.5  RERANK_GAP_RATIO=0.25  ← 按云端 0~1 调的
>
> 场景「6 条全部语义相关」→ 断崖只保留 3 条（= RERANK_MIN_TOPK 下限），砍掉 3 条相关内容
> 场景「6 条混合」        → 断崖只保留 3 条
> ```
> **具体触发点**（全相关场景）：
> ```
> idx=2: -0.6636 -> -0.8687 | abs_gap=0.2051  rel_gap=0.3091  <== 触发断崖
> ```
> `abs_gap` 只有 0.2051（语义上几乎无差别），却被 `rel_gap` 放大触发了。
> 根因：`rel_gap = abs_gap / (abs(current_score) + 1e-6)`，**current_score 接近 0 时分母趋零 → 比值爆炸**。logits 的正负分界就在 0 附近，这是高频事件。
>
> **要求你做三件事**：
>
> 1. **【必修】量纲对齐**：在 `_rerank_local()` 返回前，用 **sigmoid** 把 logits 归一到 0~1，与 cloud 后端语义一致。原始 logits 保留在内部变量里供 debug。改完 P1 会复测。
> 2. **【必修】修 rel_gap 的数值稳定性**：分母不能是 `abs(current_score) + 1e-6`，改为全局分数跨度 `(max_score - min_score + ε)` 或加一个常数项，避免分母趋零时比值爆炸。**这一条即使做了 sigmoid 也要修**，它是独立的数值 bug。
> 3. **【必修】补集成测试**（最重要）：
>    ```python
>    def test_cliff_does_not_over_truncate_related_docs():
>        """6 条全部语义相关 → 断崖后应保留 >= 4 条，不能砍到下限 3"""
>        from processor.query_processor.nodes.node_rerank import NodeRerank
>        node = NodeRerank()
>        scores = _rerank_local(query, docs_6_all_related)
>        ranked = sorted([...], key=lambda x: x["score"], reverse=True)
>        cut = node._step_3_cliff_cutoff(ranked)      # 用真实类，不要自己复写逻辑
>        assert len(cut) >= 4
>    ```
>
> **约束**：
> - `rerank_documents()` 签名不变，不要动 `node_rerank.py` 的常量（除非你论证了必须改）
> - 不要改测试去迁就实现 —— 如果 6 条全相关还是被砍到 3 条，说明修复没到位
> - 改完把「场景 / 修复前保留条数 / 修复后保留条数」三列对比表发我
>
> **顺带修两个小的**（不阻塞，一起做了）：
> - `pytest.mark.needs_model` 在 `pyproject.toml` 注册，消除 4 条 `PytestUnknownMarkWarning`
> - `test_top1_consistency` 改名（它只测了 local，没测一致性）或加 `skipif` 标注

---

## 八、当前状态与下一步

| 项 | 状态 |
|---|---|
| 卡 A 主功能 | ✅ 通过（15/15 + P1 独立 7/8） |
| D5-01 断崖量纲失配 | 🔴 **待 Qoder 返工** |
| D5-02 cloud Key 无效 | 🟡 待 P0 决策（是否开按量付费 Key） |
| 卡 B（中间件 + 端到端 + 对比评测） | ⏳ Qoder 进行中，未交付 |

**P1 建议顺序**：先修 D5-01（半天内可完成）→ 再继续卡 B。因为卡 B 的对比评测要用到 top-k 结果，带着这个缺陷做评测，指标会被污染。
