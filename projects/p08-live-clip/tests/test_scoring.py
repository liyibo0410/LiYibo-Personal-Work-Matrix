# P08 评分/ASR 生成逻辑单元测试
# 注意：_score_clip 用 hash(text[:30]) 作种子，Python 字符串 hash 每进程随机化，
# 因此跨进程分数不固定。测试只断言「同进程内确定性」与「结构/相对关系」，不硬编码分值。

import app.main as m


# ---------- _ts 时间格式化（纯函数，确定性） ----------

def test_ts_seconds_format():
    assert m._ts(0) == "00:00"
    assert m._ts(65) == "01:05"
    assert m._ts(59) == "00:59"


def test_ts_hours_format():
    assert m._ts(3661) == "01:01:01"
    assert m._ts(3600) == "01:00:00"


# ---------- _score_clip 结构确定性 ----------

def test_score_clip_deterministic_within_process():
    text = "现在下单立减50元买一送一，宝宝们赶紧抢，上链接"
    a = m._score_clip(text, 0, 20, "beauty")
    b = m._score_clip(text, 0, 20, "beauty")
    assert a.keyword_density == b.keyword_density
    assert a.energy_level == b.energy_level
    assert a.speech_rate == b.speech_rate
    assert a.interaction == b.interaction
    assert a.keyword_hits == b.keyword_hits


def test_score_clip_components_in_range():
    sb = m._score_clip("这款精华液含有烟酰胺和玻尿酸，保湿效果拉满", 0, 20, "beauty")
    for val in (sb.keyword_density, sb.energy_level, sb.speech_rate, sb.interaction):
        assert 0 <= val <= 95  # 算法上限 min(95, ...)


def test_score_clip_keyword_hits_match_theme():
    text = "这款精华液和面膜还有防晒霜，含有烟酰胺和玻尿酸"
    sb = m._score_clip(text, 0, 20, "beauty")
    # 命中的关键词必须都属于 beauty 主题词表
    beauty_kws = {"精华", "面膜", "防晒", "烟酰胺", "玻尿酸", "买一送一", "立减", "链接", "敏感肌", "回购", "福利", "下单"}
    assert set(sb.keyword_hits) <= beauty_kws
    assert "精华" in sb.keyword_hits
    assert "面膜" in sb.keyword_hits
    # 有命中时 explanation 必须点名
    assert "命中关键词" in sb.explanation


def test_score_clip_interaction_and_promo_boost_isolated():
    # base 与 boosted 前 30 字符完全一致 -> hash(text[:30]) 种子相同，
    # 因此 energy/rate/kw_density 基线一致，差异只来自互动词/促销词的加成。
    base = "这是一段用于测试基准评分的中性文本不包含任何互动或者促销相关的词汇内容哦"
    assert len(base) >= 30
    boosted = base + "宝宝弹幕扣1赶紧下单链接立减买一送一福利"
    assert base[:30] == boosted[:30]

    sb_base = m._score_clip(base, 0, 20, "beauty")
    sb_boost = m._score_clip(boosted, 0, 20, "beauty")

    # 互动词加成：interaction 只增不减（上限 95 截断）
    assert sb_boost.interaction >= sb_base.interaction
    # 促销词 + 命中促销关键词：kw_density 只增不减
    assert sb_boost.keyword_density >= sb_base.keyword_density
    # 促销信息写进评分理由（可解释性门禁）
    assert "促销" in sb_boost.explanation


def test_score_clip_explanation_nonempty():
    sb = m._score_clip("一段平平无奇没有任何关键词的描述", 0, 20, "food")
    assert isinstance(sb.explanation, str)
    assert len(sb.explanation) > 0


# ---------- _gen_asr_segments ----------

def test_gen_asr_segments_respects_duration():
    # duration=50：只保留 start <= 50 的段落（beauty 脚本 t=0,15,35 满足，t=55 起被截断）
    segs = m._gen_asr_segments("s-test", "beauty", 50)
    assert len(segs) >= 1
    assert all(s.start <= 50 for s in segs)
    assert all(s.end <= 50 for s in segs)


def test_gen_asr_segments_unknown_theme_falls_back_to_beauty():
    segs = m._gen_asr_segments("s-x", "nonexistent-theme", 360)
    assert len(segs) >= 1
    # 回退到 beauty 脚本：首句应包含「欢迎来到直播间」
    assert "直播间" in segs[0].text


def test_gen_asr_segments_speaker_and_confidence():
    segs = m._gen_asr_segments("s-y", "food", 330)
    for s in segs:
        assert s.speaker in ("主播", "助播")
        assert 0.88 <= s.confidence <= 0.99


# ---------- _generate_clips 结构 ----------

def test_generate_clips_structure():
    segs = m._gen_asr_segments("s-gen", "beauty", 360)
    clips = m._generate_clips("s-gen", "测试直播", "beauty", segs)
    assert isinstance(clips, list)
    for c in clips:
        # 每个切片必须字段齐全、时长 >= 15（短片段被丢弃）
        for key in ("id", "stream_id", "title", "start_time", "end_time", "duration", "score", "score_breakdown", "tags", "status"):
            assert key in c
        assert c["duration"] >= 15
        assert c["status"] == "completed"
        assert len(c["tags"]) >= 1
        # 评分理由必须存在（可解释性）
        assert c["score_breakdown"].explanation
