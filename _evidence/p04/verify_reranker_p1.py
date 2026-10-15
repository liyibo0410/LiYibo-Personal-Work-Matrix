# _evidence/p04/verify_reranker_p1.py
# P1 独立验证脚本 —— 不复用 Qoder 的 verify_reranker.py
# 重点：① 真实配置下 backend 是否真为 local ② 语义排序是否真一致
#      ③ 【P1 假设】本地 logits 量纲 vs 断崖阈值 0.5 的尺度失配 → 过度截断
#      ④ 单例缓存 ⑤ 降级路径

import os
import sys
import time
import json
import io

ROOT = r"D:\software\PycharmProjects\作品矩阵\projects\p04-rag-knowledge-base"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

OUT = []


def log(msg):
    print(msg, flush=True)


def check(name, ok, detail=""):
    OUT.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    log(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")


log("=" * 70)
log("P1 独立验证 · P04 Reranker 双后端（卡 A）")
log("=" * 70)

# ── 1. 真实配置（读 .env，不打印 Key 明文）──
from config.reranker_config import reranker_config as rc

key_set = bool(rc.text_rerank_api_key)
key_len = len(rc.text_rerank_api_key) if rc.text_rerank_api_key else 0
path_exists = os.path.exists(rc.bge_reranker_path) if rc.bge_reranker_path else False
check(
    "1 真实配置: backend=local 且模型路径存在",
    rc.backend == "local" and path_exists,
    f"backend={rc.backend}, device={rc.bge_reranker_device}, fp16={rc.bge_reranker_fp16}, "
    f"path_exists={path_exists}, cloud_key_set={key_set}(len={key_len})",
)

check(
    "1b CUDA 自动检测生效（4060 应得 cuda:0）",
    rc.bge_reranker_device.startswith("cuda"),
    f"device={rc.bge_reranker_device}",
)

# ── 2. local 真实推理：P1 自己的样本（不用 Qoder 的）──
from utils.reranker_http_utils import (
    _rerank_local,
    rerank_documents,
    get_last_rerank_status,
    reset_local_reranker,
)

QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单、酒店发票、打车票据，并填写报销单经部门负责人签字。",  # 0 高度相关
    "公司年会将于下周五举行，请各部门提前安排好工作并报名参会。",                      # 1 不相关
    "报销凭证包括增值税发票、行程单和付款记录，发票抬头须与公司税号一致。",            # 2 高度相关
    "园区食堂本周起供应夜宵，营业时间延长至晚上十点。",                                # 3 不相关
    "差旅报销标准按职级划分，一线城市住宿上限每晚六百元。",                            # 4 弱相关
    "报销流程：员工提交 → 部门审批 → 财务复核 → 出纳打款，全流程约五个工作日。",       # 5 高度相关
]

t0 = time.time()
reset_local_reranker()
local_scores = _rerank_local(QUERY, DOCS)
first_call = time.time() - t0

log("")
log(f"  query: {QUERY}")
ranked = sorted(enumerate(local_scores), key=lambda x: x[1], reverse=True)
for rank, (idx, sc) in enumerate(ranked):
    log(f"  Top-{rank+1}: score={sc:+.4f} | [{idx}] {DOCS[idx][:34]}...")

high = {0, 2, 5}
low = {1, 3}
min_high = min(local_scores[i] for i in high)
max_low = max(local_scores[i] for i in low)
check(
    "2 local 语义排序：高相关全体 > 不相关全体",
    min_high > max_low,
    f"最弱高相关 {min_high:+.4f} > 最强不相关 {max_low:+.4f}",
)

# ── 3. 量纲实测 + 断崖检测副作用（P1 核心假设）──
log("")
log("  ── 量纲与断崖检测 ──")
score_min, score_max = min(local_scores), max(local_scores)
log(f"  local 分数范围: {score_min:+.4f} ~ {score_max:+.4f}（logits，非 0~1）")
check(
    "3 local 输出为 logits 量纲（绝对值可 >1）",
    abs(score_min) > 1 or abs(score_max) > 1,
    f"range=[{score_min:+.4f}, {score_max:+.4f}]；云端 relevance_score 恒在 0~1",
)

# 用真实 NodeRerank 的断崖逻辑做截断（import 真实类，不复写逻辑）
cliff_local_n = None
try:
    from processor.query_processor.nodes.node_rerank import NodeRerank

    node = NodeRerank()
    ranked_docs = [
        {"content": DOCS[i], "score": s}
        for i, s in sorted(enumerate(local_scores), key=lambda x: x[1], reverse=True)
    ]
    cut = node._step_3_cliff_cutoff(ranked_docs)
    cliff_local_n = len(cut)
    log(f"  真实 NodeRerank 断崖截断: 输入 {len(ranked_docs)} 条 → 保留 {cliff_local_n} 条")
    # 逐对打印 gap，说明在哪触发
    for i in range(len(ranked_docs) - 1):
        cs = ranked_docs[i]["score"]
        ns = ranked_docs[i + 1]["score"]
        ag = cs - ns
        rg = ag / (abs(cs) + 1e-6)
        flag = "  <== 触发断崖" if (ag >= 0.5 or rg >= 0.25) else ""
        log(f"    idx={i}: {cs:+.4f} -> {ns:+.4f} | abs_gap={ag:.4f} rel_gap={rg:.4f}{flag}")
except Exception as exc:
    log(f"  [!] 无法 import NodeRerank: {exc}")
    OUT.append({"name": "3b NodeRerank 断崖截断", "ok": None, "detail": f"import 失败: {exc}"})

# ── 4. 全相关文档场景（检验过度截断）──
log("")
log("  ── 场景：6 条全部语义相关（检验是否误截）──")
ALL_RELATED = [
    "差旅费报销需要提供机票行程单和登机牌。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
    "市内交通费凭打车发票报销，需注明起止地点。",
    "报销单须经部门负责人审批签字后提交财务。",
    "财务复核通过后由出纳在五个工作日内打款。",
    "差旅补贴按职级与城市类别计算，随工资发放。",
]
rel_scores = _rerank_local(QUERY, ALL_RELATED)
log(f"  分数: {[round(s, 3) for s in rel_scores]}")
rel_ranked = sorted(
    [{"content": d, "score": s} for d, s in zip(ALL_RELATED, rel_scores)],
    key=lambda x: x["score"],
    reverse=True,
)
try:
    cut_rel = node._step_3_cliff_cutoff(rel_ranked)
    log(f"  全相关 6 条 → 断崖保留 {len(cut_rel)} 条")
    for i in range(len(rel_ranked) - 1):
        cs = rel_ranked[i]["score"]
        ns = rel_ranked[i + 1]["score"]
        ag = cs - ns
        rg = ag / (abs(cs) + 1e-6)
        flag = "  <== 触发断崖" if (ag >= 0.5 or rg >= 0.25) else ""
        log(f"    idx={i}: {cs:+.4f} -> {ns:+.4f} | abs_gap={ag:.4f} rel_gap={rg:.4f}{flag}")
    check(
        "4 全相关场景未被过度截断（期望 >=4 条）",
        len(cut_rel) >= 4,
        f"6 条全相关 → 保留 {len(cut_rel)} 条",
    )
except Exception as exc:
    log(f"  [!] 全相关场景失败: {exc}")
    OUT.append({"name": "4 全相关场景", "ok": None, "detail": str(exc)})

# ── 5. 单例缓存 ──
log("")
t1 = time.time()
for _ in range(50):
    _rerank_local(QUERY, ["文档甲", "文档乙"])
avg = (time.time() - t1) / 50
check(
    "5 单例缓存：首次加载显著慢于后续",
    first_call > avg * 3,
    f"首次 {first_call:.2f}s（含加载） vs 后续平均 {avg:.4f}s，加速 {first_call/max(avg,1e-4):.0f}x",
)

# ── 6. 降级路径：模型路径改坏 ──
log("")
from unittest.mock import patch

reset_local_reranker()
with patch("utils.reranker_http_utils.reranker_config") as mc:
    mc.backend = "local"
    mc.bge_reranker_path = r"D:\this\path\does\not\exist"
    mc.bge_reranker_device = "cpu"
    mc.bge_reranker_fp16 = False
    mc.text_rerank_api_key = None
    mc.text_rerank_model = None
    mc.text_rerank_instruct = None
    scores_d = rerank_documents("测试查询", ["A", "B", "C"])
    st = get_last_rerank_status()
check(
    "6 降级路径：local 失败 → passthrough，不抛异常",
    len(scores_d) == 3 and st["backend"] == "passthrough",
    f"backend={st['backend']}, reason={st['degrade_reason'][:60]}",
)

# ── 7. 真实主入口（不 mock 配置）──
reset_local_reranker()
scores_main = rerank_documents(QUERY, ALL_RELATED[:3])
st_main = get_last_rerank_status()
check(
    "7 真实 .env 配置下主入口走 local",
    st_main["backend"] == "local" and st_main["degrade_reason"] == "",
    f"backend={st_main['backend']}, degrade='{st_main['degrade_reason']}'",
)

# ── 汇总 ──
passed = sum(1 for r in OUT if r["ok"] is True)
failed = sum(1 for r in OUT if r["ok"] is False)
unknown = sum(1 for r in OUT if r["ok"] is None)
log("")
log("=" * 70)
log(f"汇总: PASS={passed} FAIL={failed} UNKNOWN={unknown} / 共 {len(OUT)}")
log("=" * 70)

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_reranker_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        {
            "results": OUT,
            "local_scores_sample": [round(s, 4) for s in local_scores],
            "local_score_range": [round(min(local_scores), 4), round(max(local_scores), 4)],
            "cliff_local_n": cliff_local_n,
            "first_call_sec": round(first_call, 3),
            "avg_subsequent_sec": round(avg, 4),
        },
        f,
        ensure_ascii=False,
        indent=2,
    )
