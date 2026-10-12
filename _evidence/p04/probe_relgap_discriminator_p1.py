# probe_relgap_discriminator_p1.py
# P1 独立取证：找出能区分 rel_gap 新旧分母公式的输入，供 P2 补测试使用。
#
# 背景：P1 双向验证发现——现有 7 个测试在「把 rel_gap 改回旧公式」后依然 7/7 全绿，
#       即 D5-01 的第二层根因（rel_gap 分母爆炸）没有任何测试覆盖。
#
# 数学分析：
#   新公式 rel_gap = abs_gap / score_span          （分母 = 全局跨度，大）
#   旧公式 rel_gap = abs_gap / (|current| + 1e-6)  （分母 = 当前分数，低分区趋零 → 爆炸）
#   两者差异最大的位置：current_score 很小、但全局跨度很大。
#   即「少量高相关文档 + 大量近乎零分的不相关文档」，且高→低跃迁发生在
#   lower_bound 之前，使遍历得以进入低分区。
#
# 本脚本用真实 BGE 取分，打印全精度分数并跑真实 _step_3_cliff_cutoff，
# 分别在【新公式】与【旧公式(变异)】两种源码状态下各跑一次，对比保留条数。

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\software\PycharmProjects\面试项目\projects\p04-rag-knowledge-base")
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

OUT = Path(r"D:\software\PycharmProjects\面试项目\_evidence\p04\probe_relgap_discriminator_out.txt")
_buf = []


def log(msg: str = "") -> None:
    print(msg)
    _buf.append(str(msg))


def build_profile():
    """用真实 BGE 取一组「1 条高相关 + 若干条几乎零分」的分数。"""
    from utils.reranker_http_utils import _rerank_local

    query = "电磁炉不加热的故障排查步骤"
    docs = [
        "电磁炉不加热通常是 IGBT 功率管击穿，需断电后更换并检测谐振电容。",  # 高相关
        "红烧肉的做法：五花肉切块焯水，冰糖炒色后小火慢炖两小时。",
        "今天北京天气晴朗，最高气温 28 度，适合户外散步。",
        "唐朝第二位皇帝李世民发动玄武门之变，随后登基为帝。",
        "篮球比赛每队上场五名球员，分控球后卫、得分后卫等位置。",
        "海南三亚是热门旅游城市，亚龙湾与天涯海角游客众多。",
    ]
    scores = _rerank_local(query, docs)
    ranked = sorted(
        [{"content": d, "score": s, "source": "local"} for d, s in zip(docs, scores)],
        key=lambda x: x["score"],
        reverse=True,
    )
    return query, ranked


def run_cutoff(ranked):
    from processor.query_processor.nodes.node_rerank import NodeRerank

    node = NodeRerank()
    return node._step_3_cliff_cutoff(list(ranked))


def analyze(ranked, tag):
    from processor.query_processor.nodes.node_rerank import (
        RERANK_GAP_ABS,
        RERANK_GAP_RATIO,
        RERANK_MAX_TOPK,
        RERANK_MIN_TOPK,
    )

    scores = [d["score"] for d in ranked]
    upper = min(RERANK_MAX_TOPK, len(ranked))
    lower = min(RERANK_MIN_TOPK, upper)
    span = max(scores) - min(scores) + 1e-6

    log(f"\n──────── {tag} ────────")
    log(f"  分数(全精度): {[f'{s:.8f}' for s in scores]}")
    log(f"  span = {span:.8f}   lower_bound={lower} upper_bound={upper}")

    # 用「新公式」推演
    new_cut = upper
    for idx in range(lower - 1, upper - 1):
        cur, nxt = scores[idx], scores[idx + 1]
        gap = cur - nxt
        rel_new = gap / span
        rel_old = gap / (abs(cur) + 1e-6)
        flag_new = gap >= RERANK_GAP_ABS or rel_new >= RERANK_GAP_RATIO
        flag_old = gap >= RERANK_GAP_ABS or rel_old >= RERANK_GAP_RATIO
        log(
            f"  idx={idx} cur={cur:.8f} nxt={nxt:.8f} abs_gap={gap:.8f} "
            f"| rel_new={rel_new:.6f}{'←TRIG' if flag_new else '     '} "
            f"| rel_old={rel_old:.6f}{'←TRIG' if flag_old else '     '}"
        )
        if flag_new:
            new_cut = idx + 1
            break
    log(f"  >>> 新公式推演保留: {new_cut} 条")

    real = run_cutoff(ranked)
    log(f"  >>> 真实 _step_3_cliff_cutoff 保留: {len(real)} 条")
    return len(real)


def main():
    # 检测当前源码用的是哪个公式
    src = (
        PROJECT_ROOT / "processor" / "query_processor" / "nodes" / "node_rerank.py"
    ).read_text(encoding="utf-8")
    if "rel_gap = abs_gap / score_span" in src:
        tag = "当前源码 = 新公式 (abs_gap / score_span)"
    elif "abs(current_score) + 1e-6" in src and "MUTATION" not in src:
        tag = "当前源码 = 新公式"
    elif "MUTATION-B" in src:
        tag = "当前源码 = 【变异】旧公式 (abs_gap / (|current|+1e-6))"
    else:
        tag = "当前源码 = 未知"

    log("=" * 70)
    log(f"P1 探针 · rel_gap 公式辨别力取证")
    log(f"{tag}")
    log("=" * 70)

    query, ranked = build_profile()
    log(f"\nquery: {query}")
    n = analyze(ranked, tag)

    OUT.write_text("\n".join(_buf), encoding="utf-8")
    print(f"\n[已写入] {OUT}")
    print(f"[RESULT] {tag} -> 保留 {n} 条")


if __name__ == "__main__":
    main()
