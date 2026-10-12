# _evidence/p04/verify_cliff_scale_p1.py
# P1 独立验证：local(logits) vs cloud(0~1) 两种量纲下，同一组文档喂给
# 真实 NodeRerank._step_3_cliff_cutoff 的截断结果对比。
# 目的：证明断崖阈值 RERANK_GAP_ABS=0.5 / RERANK_GAP_RATIO=0.25 存在量纲失配。

import os
import sys
import json
import io

ROOT = r"D:\software\PycharmProjects\面试项目\projects\p04-rag-knowledge-base"
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def log(m):
    print(m, flush=True)


QUERY = "员工报销差旅费需要提交哪些凭证"
ALL_RELATED = [
    "差旅费报销需要提供机票行程单和登机牌。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
    "市内交通费凭打车发票报销，需注明起止地点。",
    "报销单须经部门负责人审批签字后提交财务。",
    "财务复核通过后由出纳在五个工作日内打款。",
    "差旅补贴按职级与城市类别计算，随工资发放。",
]
MIXED = [
    "差旅费报销需提供机票行程单、酒店发票、打车票据，并填写报销单经部门负责人签字。",
    "公司年会将于下周五举行，请各部门提前安排好工作并报名参会。",
    "报销凭证包括增值税发票、行程单和付款记录，发票抬头须与公司税号一致。",
    "园区食堂本周起供应夜宵，营业时间延长至晚上十点。",
    "差旅报销标准按职级划分，一线城市住宿上限每晚六百元。",
    "报销流程：员工提交、部门审批、财务复核、出纳打款，全流程约五个工作日。",
]

from utils.reranker_http_utils import (
    _rerank_local,
    _rerank_cloud,
    reset_local_reranker,
    get_last_rerank_status,
)
from processor.query_processor.nodes.node_rerank import NodeRerank

node = NodeRerank()


def cliff(scores):
    ranked = sorted(
        [{"content": d, "score": s} for d, s in zip(DOCS_REF, scores)],
        key=lambda x: x["score"],
        reverse=True,
    )
    return len(node._step_3_cliff_cutoff(ranked)), ranked


def dump(tag, ranked):
    log(f"    {tag} 排序后的相邻 gap：")
    for i in range(len(ranked) - 1):
        cs, ns = ranked[i]["score"], ranked[i + 1]["score"]
        ag = cs - ns
        rg = ag / (abs(cs) + 1e-6)
        flag = "  <== 触发" if (ag >= 0.5 or rg >= 0.25) else ""
        log(f"      idx={i}: {cs:+.4f} -> {ns:+.4f} | abs={ag:.4f} rel={rg:.4f}{flag}")


report = {}

for scene_name, DOCS_REF in (("全相关6条", ALL_RELATED), ("混合6条", MIXED)):
    log("")
    log("=" * 70)
    log(f"场景：{scene_name}")
    log("=" * 70)

    # local
    try:
        ls = _rerank_local(QUERY, DOCS_REF)
        n_local, rl = cliff(ls)
        log(f"  [local]  分数 {[round(s,3) for s in ls]}")
        log(f"  [local]  断崖保留 {n_local} / {len(DOCS_REF)} 条")
        dump("local", rl)
    except Exception as e:
        n_local, ls = None, None
        log(f"  [local] 失败: {e}")

    # cloud（真实 API）
    try:
        cs_ = _rerank_cloud(QUERY, DOCS_REF)
        n_cloud, rc_ = cliff(cs_)
        log(f"  [cloud]  分数 {[round(s,3) for s in cs_]}")
        log(f"  [cloud]  断崖保留 {n_cloud} / {len(DOCS_REF)} 条")
        dump("cloud", rc_)
    except Exception as e:
        n_cloud, cs_ = None, None
        log(f"  [cloud] 失败（真实 API）: {type(e).__name__}: {e}")

    # sigmoid 归一化后的 local（修复方案 A 的预演）
    if ls is not None:
        import math

        sig = [1.0 / (1.0 + math.exp(-s)) for s in ls]
        n_sig, rs = cliff(sig)
        log(f"  [local+sigmoid] 分数 {[round(s,3) for s in sig]}")
        log(f"  [local+sigmoid] 断崖保留 {n_sig} / {len(DOCS_REF)} 条")
        dump("sigmoid", rs)
    else:
        n_sig = None

    report[scene_name] = {
        "local_raw": [round(s, 4) for s in ls] if ls else None,
        "local_keep": n_local,
        "cloud_raw": [round(s, 4) for s in cs_] if cs_ else None,
        "cloud_keep": n_cloud,
        "local_sigmoid_keep": n_sig,
        "total": len(DOCS_REF),
    }

log("")
log("=" * 70)
log("结论表：断崖保留条数（总数 6，下限 RERANK_MIN_TOPK=3）")
log("=" * 70)
for k, v in report.items():
    log(
        f"  {k}: local={v['local_keep']} | cloud={v['cloud_keep']} | "
        f"local+sigmoid={v['local_sigmoid_keep']}"
    )

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_cliff_scale_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
