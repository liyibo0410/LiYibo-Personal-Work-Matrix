# -*- coding: utf-8 -*-
"""清理 P04 向量库里的「孤儿切片」—— MongoDB 已无对应文档、但仍会被检索命中的向量。

删除前先把被删的行完整导出到 _runtime/（已被 git 忽略），出问题可以人工回灌。
只删 kb_chunks / kb_item_names 里查不到 Mongo 记录的 file_title，
有主的一律不动。

用法：
    python _tools/clean_orphan_vectors.py            # 只看清单，不删
    python _tools/clean_orphan_vectors.py --apply     # 备份后真删
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"D:/software/PycharmProjects/作品矩阵/projects/p04-rag-knowledge-base")
BACKUP_DIR = Path(r"D:/software/PycharmProjects/作品矩阵/_runtime/orphan-backup")

sys.path.insert(0, str(PROJECT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真删（默认只出清单）")
    args = ap.parse_args()

    from config.milvus_config import milvus_config
    from utils.milvus_utils import get_milvus_client, delete_vectors_by_file_title
    from utils.mongo_document_utils import get_document_mongo_tool

    client = get_milvus_client()
    rows = client.query(
        collection_name=milvus_config.chunks_collection,
        filter="chunk_id > 0",
        output_fields=["chunk_id", "file_title", "content", "item_name", "owner"],
        limit=16384)
    titles = sorted({r.get("file_title") for r in rows if r.get("file_title")})

    tool = get_document_mongo_tool()
    known = set()
    for doc in tool.get_all_documents(limit=500):
        fn = doc.get("filename") or ""
        known.add(Path(fn).stem)

    orphans = [t for t in titles if t not in known]
    print("kb_chunks 共 %d 条，涉及 %d 个 file_title" % (len(rows), len(titles)))
    print("Mongo 文档可反查到的 file_title：%d 个" % len(known))
    if not orphans:
        print("没有孤儿向量，无需清理。")
        return 0

    print("\n孤儿（Mongo 已无记录、但向量仍在库里会被检索命中）：")
    for t in orphans:
        n = sum(1 for r in rows if r.get("file_title") == t)
        print("   %-44s %d 条" % (t, n))

    if not args.apply:
        print("\n（未加 --apply，只列清单，没有删除任何东西）")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for t in orphans:
        dump = BACKUP_DIR / ("%s.%s.json" % (stamp, t))
        payload = [r for r in rows if r.get("file_title") == t]
        dump.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("备份 -> %s（%d 条）" % (dump.name, len(payload)))
        removed = delete_vectors_by_file_title(t)
        print("删除 %-40s 切片 %d 条 / 主体 %d 条" % (t, removed["chunks"], removed["item_names"]))

    left = client.query(collection_name=milvus_config.chunks_collection,
                        filter="chunk_id > 0", output_fields=["chunk_id"], limit=16384)
    print("\n清理后 kb_chunks 剩 %d 条" % len(left))
    return 0


if __name__ == "__main__":
    sys.exit(main())
