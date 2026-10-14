"""P07 智能打标评测：LLM 打标 vs 词表规则兜底，在同一份人工标注上对比概念覆盖率。

跑法（模块 venv 内；会发出真实模型调用，走 shared/llm-gateway）：
    .venv/Scripts/python.exe -u eval/tagging_eval.py

产出：_evidence/p07-ai-asset-center/eval-tagging-<日期>.{json,md}
"""
from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from app import config  # noqa: E402

EVIDENCE = BASE.parent.parent / "_evidence" / "p07-ai-asset-center"


def build_corpus() -> dict[str, dict]:
    tmp = Path(tempfile.mkdtemp(prefix="p07_tag_eval_"))
    config.DATA_DIR = tmp
    config.UPLOAD_DIR = tmp / "uploads"
    config.DB_PATH = tmp / "assets.db"
    (tmp / "uploads").mkdir(parents=True, exist_ok=True)
    from app import db, repository

    db.init_db()
    return {a["asset_id"]: a for a in repository.active_assets()}


def coverage(tags: list[str], concepts: dict[str, list[str]]) -> tuple[int, int, list[str]]:
    lowered = [t.lower() for t in tags]
    covered, missing = 0, []
    for name, variants in concepts.items():
        if any(v.lower() in t for t in lowered for v in variants):
            covered += 1
        else:
            missing.append(name)
    return covered, len(concepts), missing


def grounded(tags: list[str], source_text: str) -> list[str]:
    """产出的标签里，哪些在素材自身文本中找不到任何依据（可能为模型臆造）。"""
    text = source_text.lower()
    return [t for t in tags if not any(ch in text for ch in (t[:2] if len(t) >= 2 else t))]


def main() -> int:
    from app.services import llm, tagging

    expectations = json.loads((BASE / "eval" / "tagging_expectations.json").read_text(encoding="utf-8"))["assets"]
    corpus = build_corpus()
    state = llm.status()

    rows, llm_covered, total_concepts, tokens, latencies, ungrounded_total = [], 0, 0, [], [], 0
    rule_covered = 0
    for item in expectations:
        asset = corpus[item["asset_id"]]
        text = f"{asset['name']} {asset['description']} {' '.join(asset['tags'])}"
        t0 = time.perf_counter()
        result = tagging.tag_asset(asset["name"], asset["description"], asset["asset_type"])
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        llm_tags, source = result["tags"], result["tag_source"]
        rule_tags = tagging.rule_tags(text)

        c, n, missing = coverage(llm_tags, item["concepts"])
        rc, _, _ = coverage(rule_tags, item["concepts"])
        llm_covered += c
        rule_covered += rc
        total_concepts += n
        tokens.append(result["meta"]["total_tokens"])
        latencies.append(result["meta"]["latency_ms"] or elapsed)
        ug = grounded(llm_tags, text)
        ungrounded_total += len(ug)
        rows.append({
            "asset_id": item["asset_id"], "name": asset["name"], "source": source,
            "llm_tags": llm_tags, "rule_tags": rule_tags, "manual_tags": asset["tags"],
            "concepts_covered": f"{c}/{n}", "missing_concepts": missing,
            "ungrounded_tags": ug, "tokens": result["meta"]["total_tokens"],
            "latency_ms": result["meta"]["latency_ms"],
        })

    out = {
        "evaluated_at": date.today().isoformat(),
        "llm_status": {k: state[k] for k in ("configured", "model", "endpoint", "reason")},
        "assets": len(rows),
        "llm_concept_coverage": round(llm_covered / total_concepts, 3),
        "rule_concept_coverage": round(rule_covered / total_concepts, 3),
        "avg_tags_per_asset": round(statistics.mean(len(r["llm_tags"]) for r in rows), 2),
        "ungrounded_tag_count": ungrounded_total,
        "avg_tokens_per_call": round(statistics.mean(tokens), 1),
        "avg_latency_ms": round(statistics.mean(latencies), 1),
        "max_latency_ms": round(max(latencies), 1),
        "gateway_cost_snapshot": llm.cost_snapshot(),
        "per_asset": rows,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stem = f"eval-tagging-{date.today():%Y%m%d}"
    (EVIDENCE / f"{stem}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# P07 智能打标评测（{out['evaluated_at']}）",
        "",
        f"- 模型：{out['llm_status']['model'] or '未配置'} @ {out['llm_status']['endpoint'] or '-'}"
        f"（configured={out['llm_status']['configured']}）",
        f"- 样本：{out['assets']} 条 demo 素材，人工标注概念共 {total_concepts} 个",
        "",
        "| 指标 | LLM 打标 | 词表规则兜底 |",
        "|---|---|---|",
        f"| 概念覆盖率 | {out['llm_concept_coverage']} | {out['rule_concept_coverage']} |",
        f"| 平均标签数 | {out['avg_tags_per_asset']} | — |",
        f"| 平均 token/次 | {out['avg_tokens_per_call']} | 0 |",
        f"| 平均延迟 | {out['avg_latency_ms']} ms | <1 ms |",
        f"| 最大延迟 | {out['max_latency_ms']} ms | — |",
        f"| 无文本依据的标签数 | {out['ungrounded_tag_count']} | 0 |",
        "",
        "## 逐条结果",
        "",
        "| 素材 | 来源 | LLM 标签 | 覆盖概念 | 未覆盖 | 无依据标签 |",
        "|---|---|---|---|---|---|",
    ]
    for r in out["per_asset"]:
        md.append(f"| {r['asset_id']} {r['name']} | {r['source']} | {'、'.join(r['llm_tags'])} | "
                  f"{r['concepts_covered']} | {','.join(r['missing_concepts']) or '-'} | "
                  f"{','.join(r['ungrounded_tags']) or '-'} |")
    md += ["", "> 「无依据标签」= 该标签在素材自身文本里找不到字面依据，可能是模型基于常识的合理扩展，也可能是臆造；",
           "> 本模块不接入商品事实库，因此这类标签一律不用于生成对外宣称的事实性结论。"]
    (EVIDENCE / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_asset"}, ensure_ascii=False, indent=2))
    print(f"\n已写入 {EVIDENCE / stem}.json / .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
