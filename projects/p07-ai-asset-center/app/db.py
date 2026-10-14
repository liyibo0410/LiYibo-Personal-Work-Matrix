"""P07 数据库：SQLite 建表、列迁移与演示数据播种。

演示素材里的图片文件由 Pillow 程序化绘制（纯色卡片 + 文案），不是真实商品图 ——
`assets.source` 标为 `demo`，README 与 UI 均标注该边界。

路径一律经 `app.config` 在调用时读取（而非 import 期绑定），测试才能把它重定向到临时目录。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'image',
    tags TEXT NOT NULL DEFAULT '[]',
    description TEXT DEFAULT '',
    content TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    file_size INTEGER DEFAULT 0,
    width INTEGER,
    height INTEGER,
    source TEXT DEFAULT 'upload',
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS performance_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    store_name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'douyin',
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend REAL DEFAULT 0,
    revenue REAL DEFAULT 0,
    period_start TEXT,
    period_end TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at);
CREATE INDEX IF NOT EXISTS idx_perf_asset ON performance_links(asset_id);
"""

# 旧库就地补齐的列（不要求删库重建）
_ADDED_COLUMNS = {
    "mime_type": "TEXT DEFAULT ''",
    "tag_source": "TEXT DEFAULT 'manual'",
    "content": "TEXT DEFAULT ''",
}

DEMO_SEED_DATE = datetime(2026, 10, 12, 10, 0, 0)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def to_json_list(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


def get_db() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(assets)")}
    for name, ddl in _ADDED_COLUMNS.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE assets ADD COLUMN {name} {ddl}")
    # 早期版本把演示素材 created_at 写死成同一时刻，列表排序失效 —— 就地摊开成可解释的历史日期
    seed_ts = DEMO_SEED_DATE.isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT id FROM assets WHERE source='demo' AND created_at=? ORDER BY asset_id", (seed_ts,)
    ).fetchall()
    for i, r in enumerate(rows):
        ts = (DEMO_SEED_DATE - timedelta(days=len(rows) - i)).isoformat(timespec="seconds")
        conn.execute("UPDATE assets SET created_at=?, updated_at=? WHERE id=?", (ts, ts, r["id"]))


def _backfill_demo_previews(conn: sqlite3.Connection) -> None:
    """给缺文件的演示素材补上程序化演示图（只动 source='demo' 的行，不碰用户上传文件）。

    旧版本播种时没有落盘文件，素材库整屏只有「IMG」文字块 —— 用户看不到任何图，
    也无法演示「上传→预览→检索」闭环。
    """
    lookup = {a[0]: a for a in _DEMO_ASSETS}
    rows = conn.execute(
        "SELECT asset_id, name, asset_type, width, height FROM assets"
        " WHERE source='demo' AND (file_path='' OR file_path IS NULL)"
    ).fetchall()
    if not rows:
        return
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for r in rows:
        spec = lookup.get(r["asset_id"])
        if not spec or not spec[7]:  # 无主色 = 文案类素材，本就没有图
            continue
        w, h = spec[5], spec[6]
        path = config.UPLOAD_DIR / f"{r['asset_id']}.png"
        draw_demo_card(path, r["name"], (w, h), spec[7])
        conn.execute(
            "UPDATE assets SET file_path=?, file_size=?, width=?, height=?, mime_type='image/png'"
            " WHERE asset_id=?",
            (str(path), path.stat().st_size, w, h, r["asset_id"]),
        )


def init_db() -> None:
    conn = get_db()
    conn.executescript(SCHEMA)
    _migrate(conn)
    if conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0:
        seed_demo_data(conn)
    _backfill_demo_previews(conn)
    conn.commit()
    conn.close()


# (asset_id, 名称, 类型, 标签, 描述, 宽, 高, 演示图主色)
_DEMO_ASSETS = [
    ("AST-001", "春季护肤主图A", "image", ["护肤", "春季", "主图", "清爽"], "春季主推护肤品主图方案A", 800, 800, "#3370FF"),
    ("AST-002", "口红试色短视频脚本", "video", ["口红", "试色", "短视频", "种草"], "口红试色种草视频脚本", 1080, 1920, "#E4474B"),
    ("AST-003", "618大促Banner", "image", ["618", "大促", "Banner", "红色"], "618年中大促活动Banner", 1200, 400, "#D92D20"),
    ("AST-004", "运动鞋详情页长图", "image", ["运动鞋", "详情页", "长图", "科技"], "运动鞋科技卖点详情页", 750, 1400, "#475467"),
    ("AST-005", "直播间背景板", "image", ["直播", "背景板", "品牌"], "品牌直播间背景板设计", 1280, 720, "#7B5CFA"),
    ("AST-006", "面膜种草文案", "copy", ["面膜", "种草", "文案", "保湿"], "面膜保湿种草文案合集", 0, 0, ""),
    ("AST-007", "防晒霜对比图", "image", ["防晒", "对比", "夏天", "清爽"], "防晒霜SPF50 vs SPF30对比图", 800, 600, "#16A34A"),
    ("AST-008", "品牌故事短视频", "video", ["品牌", "故事", "情感", "短视频"], "品牌创立故事短视频脚本", 1080, 1920, "#B4690E"),
    ("AST-009", "双11预售海报", "image", ["双11", "预售", "海报", "狂欢"], "双11预售启动海报", 1080, 1920, "#D92D20"),
    ("AST-010", "洗发水成分解析图", "image", ["洗发水", "成分", "解析", "科普"], "洗发水核心成分科普图", 800, 1200, "#475467"),
    ("AST-011", "零食大礼包主图", "image", ["零食", "大礼包", "主图", "美食"], "零食大礼包产品主图", 800, 800, "#B4690E"),
    ("AST-012", "家电以旧换新Banner", "image", ["家电", "以旧换新", "Banner", "绿色"], "家电以旧换新活动Banner", 1200, 400, "#16A34A"),
]

_DEMO_PERFORMANCE = [
    ("AST-001", "云枢旗舰店", "douyin", 125000, 8750, 437, 3200, 28800, "2026-09-01", "2026-09-30"),
    ("AST-002", "云枢旗舰店", "douyin", 89000, 7120, 356, 5600, 42000, "2026-09-01", "2026-09-30"),
    ("AST-003", "云枢美妆店", "taobao", 210000, 14700, 735, 8000, 96000, "2026-06-01", "2026-06-20"),
    ("AST-004", "云枢运动店", "tmall", 67000, 4020, 201, 4500, 31500, "2026-09-01", "2026-09-30"),
    ("AST-007", "云枢旗舰店", "douyin", 156000, 10920, 546, 4100, 38200, "2026-07-01", "2026-07-31"),
    ("AST-009", "云枢全店", "taobao", 380000, 26600, 1330, 15000, 195000, "2025-11-01", "2025-11-11"),
    ("AST-011", "云枢零食店", "pinduoduo", 95000, 6650, 332, 2800, 16800, "2026-09-01", "2026-09-30"),
    ("AST-012", "云枢家电店", "jd", 74000, 5180, 259, 3600, 25900, "2026-08-01", "2026-08-31"),
]


def draw_demo_card(path: Path, name: str, size: tuple[int, int], color: str) -> None:
    """程序化绘制演示素材图（纯色卡片 + 名称），不依赖外部图片资源。"""
    from PIL import Image, ImageDraw

    from app.services.media import load_font

    w, h = size
    img = Image.new("RGB", (w, h), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, int(h * 0.6), w, h], fill="#FFFFFF")
    big, small = load_font(max(18, w // 22)), load_font(max(14, w // 34))
    draw.text((int(w * 0.06), int(h * 0.08)), "云枢智能 · 演示素材", fill="#FFFFFF", font=small)
    draw.text((int(w * 0.06), int(h * 0.66)), name, fill="#111826", font=big)
    draw.text((int(w * 0.06), int(h * 0.8)), f"{w}×{h} · 程序化占位图，非真实商品图",
              fill="#5A6472", font=small)
    img.save(path, "PNG")


def seed_demo_data(conn: sqlite3.Connection) -> None:
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    total = len(_DEMO_ASSETS)
    for i, (asset_id, name, atype, tags, desc, w, h, color) in enumerate(_DEMO_ASSETS):
        ts = (DEMO_SEED_DATE - timedelta(days=total - i)).isoformat(timespec="seconds")
        file_path, file_size, mime = "", 0, ""
        if color:
            p = config.UPLOAD_DIR / f"{asset_id}.png"
            draw_demo_card(p, name, (w, h), color)
            file_path, file_size, mime = str(p), p.stat().st_size, "image/png"
        conn.execute(
            "INSERT INTO assets (asset_id, name, asset_type, tags, description, file_path,"
            " file_size, width, height, source, status, created_at, updated_at, mime_type, tag_source)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (asset_id, name, atype, to_json_list(tags), desc, file_path, file_size, w, h,
             "demo", "active", ts, ts, mime, "manual"),
        )
    ts = now_iso()
    for p in _DEMO_PERFORMANCE:
        conn.execute(
            "INSERT INTO performance_links (asset_id, store_name, platform, impressions, clicks,"
            " conversions, spend, revenue, period_start, period_end, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (*p, ts),
        )
