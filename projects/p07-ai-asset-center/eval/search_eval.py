"""P07 以文搜图评测：新策略（中文 n-gram + 同义归一 + 字段加权）与旧策略（split + 子串包含）对照。

跑法（模块 venv 内，不依赖服务在跑）：
    .venv/Scripts/python.exe -u eval/search_eval.py

产出：_evidence/p07-ai-asset-center/eval-search-<日期>.{json,md}
指标全部来自真实执行，不做任何估算。
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
K = 5


def build_corpus() -> list[dict]:
    """在临时目录里初始化一份干净的 demo 库，避免读写真实 data/assets.db。"""
    tmp = Path(tempfile.mkdtemp(prefix="p07_eval_"))
    config.DATA_DIR = tmp
    config.UPLOAD_DIR = tmp / "uploads"
    config.DB_PATH = tmp / "assets.db"
    (tmp / "uploads").mkdir(parents=True, exist_ok=True)
    from app import db, repository

    db.init_db()
    return repository.active_assets()


def legacy_search(assets: list[dict], query: str, top_k: int = K) -> list[str]:
    """改造前的实现：`query.lower().split()` + 子串包含（中文连写基本命中不了）。"""
    terms = set(query.lower().split())
    scored = []
    for a in assets:
        text = f"{a['name']} {' '.join(a['tags'])} {a['description']}".lower()
        score = sum(1 for t in terms if t in text)
        if score > 0:
            scored.append((score, a["asset_id"]))
    scored.sort(key=lambda x: -x[0])
    return [aid for _, aid in scored[:top_k]]


def run(assets: list[dict], queries: list[dict], engine) -> dict:
    hits, top1, mrr, latencies, refuse_ok, refuse_total = [], [], [], [], 0, 0
    misses = []
    for item in queries:
        q, expected = item["query"], item.get("expected", [])
        t0 = time.perf_counter()
        ids = engine(q, expected)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)
        if item.get("expect_refuse"):
            refuse_total += 1
            refuse_ok += int(len(ids) == 0)
            continue
        rank = next((i + 1 for i, x in enumerate(ids) if x in expected), None)
        mrr.append(1 / rank if rank else 0.0)
        hits.append(rank is not None)
        top1.append(bool(ids and ids[0] in expected))
        if not ids:
            misses.append(q)
    out = {
        "queries_evaluated": len(queries),
        "recall_at_5": round(sum(hits) / len(hits), 3) if hits else 0,
        "precision_at_1": round(sum(top1) / len(top1), 3) if top1 else 0,
        "mrr": round(sum(mrr) / len(mrr), 3) if mrr else 0,
        "refusal_accuracy": round(refuse_ok / refuse_total, 3) if refuse_total else None,
        "missed_queries": misses,
        "latency_ms_avg": round(statistics.mean(latencies), 2),
        "latency_ms_p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 2),
    }
    return out


def main() -> int:
    from app.services import search

    dataset = json.loads((BASE / "eval" / "queries_labeled.json").read_text(encoding="utf-8"))
    queries = dataset["queries"]
    assets = build_corpus()

    def new_engine(q, _expected):
        return [i["asset_id"] for i in search.search(assets, q, top_k=K)["items"]]

    result = {
        "evaluated_at": date.today().isoformat(),
        "corpus_size": len(assets),
        "dataset": str((BASE / "eval" / "queries_labeled.json").relative_to(BASE.parent.parent)),
        "new_engine": run(assets, queries, new_engine),
        "legacy_engine": run(assets, queries, lambda q, _e: legacy_search(assets, q)),
        "engine_labels": {
            "new_engine": "cn-ngram + 同义组归一 + 字段加权 + IDF + 阈值拒答",
            "legacy_engine": "query.split() + 子串包含（改造前）",
        },
    }

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stem = f"eval-search-{date.today():%Y%m%d}"
    (EVIDENCE / f"{stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    n, o = result["new_engine"], result["legacy_engine"]
    md = [
        f"# P07 以文搜图评测（{result['evaluated_at']}）",
        "",
        f"- 语料：{result['corpus_size']} 条 demo 素材；评测集：{n['queries_evaluated']} 条查询（{n['refusal_accuracy'] is not None and '含拒答用例'}）",
        f"- 数据集：`{result['dataset']}`（人工标注期望命中素材）",
        "",
        "| 指标 | 新策略 | 改造前（split+子串） |",
        "|---|---|---|",
        f"| Recall@5 | {n['recall_at_5']} | {o['recall_at_5']} |",
        f"| Precision@1 | {n['precision_at_1']} | {o['precision_at_1']} |",
        f"| MRR | {n['mrr']} | {o['mrr']} |",
        f"| 拒答准确率 | {n['refusal_accuracy']} | {o['refusal_accuracy']} |",
        f"| 平均延迟 | {n['latency_ms_avg']} ms | {o['latency_ms_avg']} ms |",
        f"| P95 延迟 | {n['latency_ms_p95']} ms | {o['latency_ms_p95']} ms |",
        "",
        f"新策略未命中的查询：{n['missed_queries'] or '无'}",
        f"改造前未命中的查询：{o['missed_queries'] or '无'}",
        "",
        "> 延迟为本机进程内测量（12 条语料、无并发），不代表生产吞吐；真实数字仅此一处，不外推。",
    ]
    (EVIDENCE / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n已写入 {EVIDENCE / stem}.json / .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
