# verify_eval_compare_p1.py
# P1 独立复核第③项：36 条 Ragas 对比评测结论是否可用。
# 核心：判断差异来源是「重排质量」还是「上下文条数（source_count）量纲失配」。
# 上轮污染症状：local source_count=3 vs passthrough=5，导致指标给出相反结论。

from __future__ import annotations

import io
import json
import statistics
from pathlib import Path

EVID = Path(r"D:\software\PycharmProjects\作品矩阵\_evidence\p04")
OUT = EVID / "verify_eval_compare_p1_out.txt"
buf = []


def log(m=""):
    print(m)
    buf.append(str(m))


def main():
    report = json.loads((EVID / "rag_compare_report.json").read_text(encoding="utf-8"))

    log("=" * 72)
    log("P1 独立复核 · 第③项 Ragas 36 条对比评测")
    log("=" * 72)

    log(f"\n测试集规模: {report['test_set_size']}")
    log(f"降级记录  : {report.get('degrade_notes', [])}  (空=两条链路均真实执行)")

    # ── 1. 指标对比 ──
    log("\n【1】Ragas 五项指标（cloud - local）")
    loc = report["local"]["ragas_scores"]
    cld = report["cloud"]["ragas_scores"]
    log(f"  {'指标':<22}{'local':>10}{'cloud':>10}{'差值':>10}   方向")
    agree = 0
    for k in loc:
        d = cld[k] - loc[k]
        direction = "cloud 优" if d > 0.005 else ("local 优" if d < -0.005 else "持平")
        if d > 0.005:
            agree += 1
        log(f"  {k:<22}{loc[k]:>10.4f}{cld[k]:>10.4f}{d:>+10.4f}   {direction}")
    log(f"\n  → cloud 优于 local 的指标数: {agree}/5")
    log("  上轮症状: Context Precision 说 local 好 / Answer Correctness 说 cloud 好（矛盾）")
    log(f"  本轮结论: {'方向一致，结论可用 ✅' if agree >= 4 else '仍存在方向矛盾 ⚠️'}")

    # ── 2. source_count 量纲核对（污染源头）──
    log("\n【2】source_count 分布 —— 判断差异是否来自上下文条数")
    details = report.get("latency_details", [])
    by_backend = {}
    for d in details:
        by_backend.setdefault(d["backend"], []).append(d)

    summary = {}
    for bk, rows in by_backend.items():
        sc = [r.get("source_count", 0) for r in rows]
        lt = [r.get("elapsed_seconds", 0) for r in rows]
        summary[bk] = {
            "n": len(rows),
            "source_count_mean": statistics.mean(sc) if sc else 0,
            "source_count_min": min(sc) if sc else 0,
            "source_count_max": max(sc) if sc else 0,
            "count_at_min_topk_3": sum(1 for x in sc if x == 3),
            "latency_mean": statistics.mean(lt) if lt else 0,
            "latency_median": statistics.median(lt) if lt else 0,
            "latency_max": max(lt) if lt else 0,
            "latency_min": min(lt) if lt else 0,
        }
        s = summary[bk]
        log(
            f"  [{bk}] n={s['n']}  source_count 均值={s['source_count_mean']:.2f} "
            f"(min={s['source_count_min']}, max={s['source_count_max']})  "
            f"被砍到下限3的条数={s['count_at_min_topk_3']}/{s['n']}"
        )
        log(
            f"        延迟 均值={s['latency_mean']:.2f}s 中位={s['latency_median']:.2f}s "
            f"(min={s['latency_min']:.2f}, max={s['latency_max']:.2f})"
        )

    if "local" in summary and "cloud" in summary:
        dl = summary["local"]["source_count_mean"]
        dc = summary["cloud"]["source_count_mean"]
        log(f"\n  source_count 均值差: local={dl:.2f}  cloud={dc:.2f}  差值={dc - dl:+.2f}")
        if abs(dc - dl) < 0.5:
            log("  → 两侧上下文条数量级一致，指标差异可归因于【重排质量】而非条数 ✅")
        else:
            log("  → ⚠️ 两侧上下文条数差异显著，指标差异仍受【条数量纲】污染，结论不可直接归因")

    # ── 3. 与 D5-01 修复前基线对比 ──
    base = EVID / "_archive_D5-01_baseline" / "rag_compare_report.json"
    if base.exists():
        b = json.loads(base.read_text(encoding="utf-8"))
        log("\n【3】与 D5-01 修复前基线对比")
        for k in b.get("local", {}).get("ragas_scores", {}):
            bl = b["local"]["ragas_scores"][k]
            log(f"  {k:<22} 基线local={bl:.4f} → 现local={loc.get(k, 0):.4f}  ({loc.get(k, 0) - bl:+.4f})")
    else:
        log("\n【3】基线报告不存在（_archive_D5-01_baseline 无 rag_compare_report.json），跳过对比")

    OUT.write_text("\n".join(buf), encoding="utf-8")
    print(f"\n[已写入] {OUT}")


if __name__ == "__main__":
    main()
