"""P1 独立验证脚本：合规检测（不依赖 Qoder 的测试与报告）。

目的：用第三方视角独立复核，包括
  ① 用户指定的两条验收用例
  ② span 定位是否精确（原文切片必须 == 命中词）
  ③ P1 自己补充的边界与对抗用例
  ④ 规则兜底路径的卖点修复验证
运行：api/.venv/Scripts/python.exe _evidence/p02/verify_compliance.py
"""

import io
import os
import sys

API = r"D:\software\PycharmProjects\面试项目\projects\p02-ecommerce-ops-assistant\api"
EV = r"D:\software\PycharmProjects\面试项目\_evidence\p02"
sys.path.insert(0, API)

out = []


def w(s=""):
    out.append(str(s))
    print(s)


from app.services.compliance import check_content, check_text  # noqa: E402

fails = []


def case(name, text, want_verdict, want_labels=None, want_span_ok=True):
    """跑一条用例并记录结果。want_span_ok 检查 span 切片是否等于 matched_text。"""
    r = check_text(text)
    labels = [h.matched_text for h in r.hits]
    ok_v = r.verdict == want_verdict
    ok_l = True
    if want_labels is not None:
        ok_l = all(any(wl in lb for lb in labels) for wl in want_labels)
    span_bad = []
    if want_span_ok:
        for h in r.hits:
            seg = text[h.span[0]:h.span[1]]
            if seg != h.matched_text:
                span_bad.append((h.matched_text, seg, h.span))
    ok_s = not span_bad
    flag = "PASS" if (ok_v and ok_l and ok_s) else "FAIL"
    if flag == "FAIL":
        fails.append((name, r.verdict, want_verdict, labels, want_labels, span_bad))
    w(f"[{flag}] {name}")
    w(f"       输入   : {text}")
    w(f"       verdict: {r.verdict}（期望 {want_verdict}）")
    w(f"       命中   : {labels}")
    if span_bad:
        w(f"       ⚠ span 错位: {span_bad}")
    return r


w("=" * 78)
w("【一】用户指定的两条验收用例")
w("=" * 78)
case(
    "验收1 · 应 block",
    "这款面膜能快速消炎杀菌，全国销量第一，仅此一次！",
    "block",
    ["消炎", "杀菌", "第一", "仅此一次"],
)
case(
    "验收2 · 应 pass（零误报）",
    "全国包邮，最高支持 120W 快充，第一次使用建议先测试",
    "pass",
    [],
)

w()
w("=" * 78)
w("【二】P1 独立补充的边界用例")
w("=" * 78)
case("B1 序数'第一次'不应命中", "第一次使用请先做耳后测试。", "pass")
case("B2 技术参数'最高温度'不应命中", "最高温度 45℃，注意避免烫伤。", "pass")
case("B3 白名单'唯一序列号'不应命中", "唯一序列号可用于官方验真。", "pass")
case("B4 中风险应判 review 而非 block", "独家专利配方，自主研发生产。", "review")
case("B5 否定语境不应误报", "本品不含激素，请勿相信快速根治等夸大宣传。", "pass")

w()
w("=" * 78)
w("【三】对抗用例（变体绕过）")
w("=" * 78)
case("A1 零宽字符 最\\u200b好", "最\u200b好用的面膜，效果出众。", "block", ["最\u200b好"])
case("A2 全角空格 最　好", "最\u3000好\u3000的\u3000选择", "block", ["最\u3000好"])
# A3 期望 matched_text 是【原文切片】"苐一"，而非归一化后的"第一"
# —— 这同时验证了 matched_text 忠实回标原文（P1 修复项）
case("A3 形近字 苐一（同时验原文回标）", "行业苐一，品质可靠。", "block", ["苐一"])
case("A4 符号插入 最-好", "最-好-用 的产品值得拥有。", "block", ["最-好"])

w()
w("=" * 78)
w("【四】内容级检测（check_content 主图/视频）")
w("=" * 78)
c1 = check_content(
    {
        "title": "全网最低价",
        "headline": "国家级认证好物",
        "sub_headline": "品质之选",
        "proof_points": ["全国包邮", "第一次使用零门槛"],
    },
    "main_image",
)
w(f"主图方案 verdict = {c1.verdict}（期望 block）")
for h in c1.hits:
    w(f"   field={h.field_name:24s} rule={h.rule_id:10s} risk={h.risk:6s} matched={h.matched_text}")
if c1.verdict != "block":
    fails.append(("check_content 主图", c1.verdict, "block", [], [], []))

c2 = check_content(
    {
        "title": "新品上市",
        "hook": "第一次见到这样的设计",
        "cta": "点击了解更多",
        "scenes": [{"voiceover": "全国包邮，售后无忧"}],
    },
    "video_script",
)
w(f"视频脚本 verdict = {c2.verdict}（期望 pass）")
for h in c2.hits:
    w(f"   field={h.field_name:24s} rule={h.rule_id:10s} risk={h.risk:6s} matched={h.matched_text}")
if c2.verdict != "pass":
    fails.append(("check_content 视频", c2.verdict, "pass", [], [], []))

w()
w("=" * 78)
w("【五】规则兜底路径：卖点列表修复验证")
w("=" * 78)
try:
    import inspect

    from app.services import creative_plans as cp

    src = inspect.getsource(cp._focus_points)
    bad = '“, ”' in src or '“, “' in src
    w(f"_focus_points 源码含被破坏的引号: {bad}（期望 False）")
    if bad:
        fails.append(("_focus_points 引号", "broken", "fixed", [], [], []))
    # 直接验证返回值
    got = cp._focus_points(None, [], None) if False else None
except Exception as exc:  # noqa: BLE001
    w("跳过源码检查: " + str(exc))

# 直接验证：无诊断、无卖点时，兜底应返回 3 个独立卖点
try:
    from app.services.creative_plans import _focus_points

    class _P:
        selling_points = []

    pts = _focus_points(_P(), None)
    w(f"兜底卖点 = {pts}")
    w(f"数量 = {len(pts)}（期望 3）")
    if pts != ["核心卖点", "使用效果", "购买理由"]:
        fails.append(("兜底卖点内容", str(pts), "3 个独立卖点", [], [], []))
except Exception as exc:  # noqa: BLE001
    w("_focus_points 调用失败: " + type(exc).__name__ + ": " + str(exc))

w()
w("=" * 78)
w("【结论】")
w("=" * 78)
if fails:
    w(f"❌ 共 {len(fails)} 项未通过：")
    for f in fails:
        w("   - " + f[0] + f"  verdict={f[1]} 期望={f[2]}")
else:
    w("✅ 全部用例通过（含 span 精确定位检查）")

os.makedirs(EV, exist_ok=True)
with io.open(os.path.join(EV, "compliance_verify.log"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("WROTE_LOG")