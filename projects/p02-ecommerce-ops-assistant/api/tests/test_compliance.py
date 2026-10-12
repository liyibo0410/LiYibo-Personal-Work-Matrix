"""广告法合规词检测单元测试。

覆盖：正例 / 负例 / 对抗例 / 边界例。
"""

import pytest

from app.services.compliance import ComplianceChecker, ComplianceResult


@pytest.fixture(scope="module")
def checker() -> ComplianceChecker:
    return ComplianceChecker()


# ── 正例：必须拦截 ──────────────────────────────────────────────


class TestPositiveBlock:
    def test_化妆品医疗加绝对化(self, checker: ComplianceChecker) -> None:
        """验收用例：面膜文案含消炎/杀菌/第一/仅此一次 → block。"""
        result = checker.check_text("这款面膜能快速消炎杀菌，全国销量第一，仅此一次！")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert {"消炎", "杀菌", "第一", "仅此一次"}.issubset(surfaces)

    def test_多违规叠加(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("全网最低价，仅此一次，错过不再有！")
        assert result.verdict == "block"
        surfaces = [h.surface for h in result.hits]
        assert "全网最低价" in surfaces
        assert "仅此一次" in surfaces
        assert "错过不再有" in surfaces

    def test_绝对化加虚假承诺(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("国家级认证，行业第一品牌，100%有效。")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "国家级" in surfaces
        assert "第一" in surfaces

    def test_权威背书(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("免检产品，特供渠道，政府指定采购")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "免检" in surfaces
        assert "特供" in surfaces
        assert "政府指定" in surfaces

    def test_虚假承诺(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("本品无任何副作用，一次见效，永久有效")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "无任何副作用" in surfaces
        assert "一次见效" in surfaces
        assert "永久有效" in surfaces

    def test_投资收益(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("稳赚不赔，保本保息，年化收益 15%")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "稳赚不赔" in surfaces
        assert "保本保息" in surfaces

    def test_安全性断言(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("权威认证，绝对安全，零风险")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "绝对安全" in surfaces
        assert "零风险" in surfaces


# ── 负例：不应拦截 ──────────────────────────────────────────────


class TestNegativePass:
    def test_全国包邮(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("全国包邮，偏远地区除外。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_技术参数(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("最高支持 120W 快充，最大容量 20000mAh。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_序数用法_第一次(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("第一次使用建议先做耳后测试。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_否定语境(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("本品不含激素，请勿相信快速根治等夸大宣传。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_技术性唯一(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("唯一序列号可用于官方验真。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_全网通(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("全网通手机，支持三大运营商。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_第一款第二款(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("第一款配色为雾霾蓝，第二款为珍珠白。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_第一时间(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("第一时间联系客服可加急处理。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_最高温度(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("最高温度可达 45℃，注意避免烫伤。")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"

    def test_合规时限表述(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("本次活动时间为 10月12日至 10月15日。")
        assert result.verdict == "pass"

    def test_验收用例_零误报(self, checker: ComplianceChecker) -> None:
        """验收用例：合规文案 → pass，零误报。"""
        result = checker.check_text("全国包邮，最高支持 120W 快充，第一次使用建议先测试")
        assert result.verdict == "pass", f"误报: {[h.surface for h in result.hits]}"


# ── 对抗例：绕过手段必须被捕获 ──────────────────────────────────


class TestAdversarial:
    def test_零宽字符(self, checker: ComplianceChecker) -> None:
        text = "最\u200b好用的面膜，全网\u3000最低价。"
        result = checker.check_text(text)
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "最好" in surfaces or "最" in surfaces
        assert "全网最低价" in surfaces or "最低价" in surfaces

    def test_形近字_苐(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("NO.1 销量，行业苐一。")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "第一" in surfaces

    def test_全角空格插入(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("最 好 的 选 择")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "最好" in surfaces

    def test_符号插入(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("最-好-用 的产品，仅-此-一-次")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "最好" in surfaces
        assert "仅此一次" in surfaces

    def test_谐音形近字(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("蕞好用的产品，坠低价促销")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "最好" in surfaces
        assert "最低价" in surfaces

    def test_符号插入_顶级(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("顶级*品质*，仅此*一次")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "顶级" in surfaces
        assert "仅此一次" in surfaces


# ── 边界例：中风险 → review ────────────────────────────────────


class TestBoundary:
    def test_限时缺时间窗(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("限时优惠，先到先得。")
        assert result.verdict == "review"
        surfaces = {h.surface for h in result.hits}
        assert "限时" in surfaces

    def test_独家中风险(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("独家专利配方，销量领先，7天无理由退换。")
        assert result.verdict == "review"
        surfaces = {h.surface for h in result.hits}
        assert "独家" in surfaces

    def test_无效退款(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("无效退款，无效果可申请售后。")
        assert result.verdict == "review"
        surfaces = {h.surface for h in result.hits}
        assert "无效退款" in surfaces

    def test_无添加(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("本品无添加香精和色素，成分简单。")
        assert result.verdict == "review"
        surfaces = {h.surface for h in result.hits}
        assert "无添加" in surfaces

    def test_杀菌需资质(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("杀菌湿巾，已取得卫生许可。")
        assert result.verdict == "review"
        surfaces = {h.surface for h in result.hits}
        assert "杀菌" in surfaces

    def test_终身免费(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("终身免费提供软件更新服务。")
        assert result.verdict == "review"
        surfaces = {h.surface for h in result.hits}
        assert "终身免费" in surfaces


# ── 上下文升权 ──────────────────────────────────────────────────


class TestContext:
    def test_第一_行业升权(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("行业第一品牌")
        assert result.verdict == "block"
        hit = next(h for h in result.hits if h.surface == "第一")
        assert hit.risk == "high"

    def test_第一_纯序数不升权(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("第一步操作说明")
        assert result.verdict == "pass"

    def test_第一_右侧序数阻断(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("第三批次产品")
        assert result.verdict == "pass"


# ── 输出结构 ──────────────────────────────────────────────────


class TestOutputStructure:
    def test_hit包含必要字段(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("国家级产品")
        assert len(result.hits) >= 1
        hit = result.hits[0]
        assert hit.rule_id
        assert hit.span[0] >= 0
        assert hit.span[1] > hit.span[0]
        assert hit.suggestions
        assert hit.legal_basis

    def test_to_dict序列化(self, checker: ComplianceChecker) -> None:
        result = checker.check_text("顶级产品")
        d = result.to_dict()
        assert d["verdict"] == "block"
        assert isinstance(d["hits"], list)
        assert len(d["hits"]) >= 1
        assert "rule_id" in d["hits"][0]
        assert "span" in d["hits"][0]

    # ── P1 补充：matched_text 必须忠实回标原文（防回归）────────────────
    # 背景：归一化会移除零宽字符、把全角空格转空格、替换形近字，
    # 若 matched_text 直接取归一化文本，前端拿它去原文匹配会失配、
    # 高亮也会标错位置。正确实现应返回「原文切片」，与 span 严格自洽。

    def test_matched_text回标原文_零宽字符(self, checker: ComplianceChecker) -> None:
        text = "最\u200b好用的面膜"
        result = checker.check_text(text)
        assert result.verdict == "block"
        hit = result.hits[0]
        # matched_text 必须含零宽字符（是原文切片），而非被清洗后的 "最好"
        assert "\u200b" in hit.matched_text
        assert text[hit.span[0]:hit.span[1]] == hit.matched_text

    def test_matched_text回标原文_形近字(self, checker: ComplianceChecker) -> None:
        text = "行业苐一，品质可靠。"
        result = checker.check_text(text)
        assert result.verdict == "block"
        hit = result.hits[0]
        # 原文是形近字「苐一」，matched_text 应保持原文，不是「第一」
        assert hit.matched_text == "苐一"
        assert text[hit.span[0]:hit.span[1]] == hit.matched_text

    def test_matched_text回标原文_全角空格(self, checker: ComplianceChecker) -> None:
        text = "最\u3000好\u3000的\u3000选择"
        result = checker.check_text(text)
        assert result.verdict == "block"
        hit = result.hits[0]
        assert "\u3000" in hit.matched_text
        assert text[hit.span[0]:hit.span[1]] == hit.matched_text

    def test_span与matched_text全局自洽(self, checker: ComplianceChecker) -> None:
        """对所有用例：原文[span] 必须恒等于 matched_text。"""
        samples = [
            "这款面膜能快速消炎杀菌，全国销量第一，仅此一次！",
            "最\u200b好用的面膜，全网\u3000最低价。",
            "NO.1 销量，行业苐一。",
            "顶级产品，绝对安全",
            "最-好-用 的产品，仅-此-一-次",
        ]
        for text in samples:
            for hit in checker.check_text(text).hits:
                assert text[hit.span[0]:hit.span[1]] == hit.matched_text, (
                    f"span 与 matched_text 不自洽: text={text!r} "
                    f"span={hit.span} matched={hit.matched_text!r}"
                )

    def test_最X型表述被判中风险(self, checker: ComplianceChecker) -> None:
        """P1 补充词库：口语化「最+形容词」应命中 medium，而非漏检。"""
        for text in ["这是我用过最满意的产品", "全网最划算的选择", "最实惠的套装"]:
            result = checker.check_text(text)
            assert result.verdict in ("review", "block"), f"{text} 漏检"
            assert any("最" in h.matched_text for h in result.hits), f"{text} 未命中最X表述"

    def test_check_content主图(self, checker: ComplianceChecker) -> None:
        content = {
            "title": "顶级面膜",
            "headline": "全国销量第一",
            "sub_headline": "限时特惠",
            "proof_points": ["消炎配方"],
        }
        result = checker.check_content(content, "main_image")
        assert result.verdict == "block"
        field_names = {h.field_name for h in result.hits}
        assert "headline" in field_names or "title" in field_names

    def test_check_content视频脚本(self, checker: ComplianceChecker) -> None:
        content = {
            "title": "产品介绍",
            "hook": "这款顶级产品你绝对不能错过",
            "cta": "仅此一次，立即购买",
            "scenes": [
                {"shot": "0-3s", "visual": "展示", "voiceover": "全网最低价"},
            ],
        }
        result = checker.check_content(content, "video_script")
        assert result.verdict == "block"
        surfaces = {h.surface for h in result.hits}
        assert "顶级" in surfaces
        assert "仅此一次" in surfaces


# ── 归一化 ──────────────────────────────────────────────────────


class TestNormalization:
    def test_零宽字符移除(self, checker: ComplianceChecker) -> None:
        norm, pos_map = checker.normalize("最\u200b好")
        assert norm == "最好"
        assert len(pos_map) == 2

    def test_形近字替换(self, checker: ComplianceChecker) -> None:
        norm, _ = checker.normalize("苐一")
        assert norm == "第一"

    def test_多种绕过叠加(self, checker: ComplianceChecker) -> None:
        norm, _ = checker.normalize("蕞\u200b佳")
        assert norm == "最佳"
