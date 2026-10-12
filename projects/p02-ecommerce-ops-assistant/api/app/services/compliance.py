"""广告法合规词与极限词检测模块。

三级匹配：精确词 → 容错正则（对抗插符号/形近字/全角空格/零宽字符）→ 上下文升权。
输出三态判定：block / review / pass。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LEXICON_PATH = Path(__file__).parent.parent / "resources" / "compliance_lexicon.json"


@dataclass
class ComplianceHit:
    rule_id: str
    surface: str
    matched_text: str
    span: tuple[int, int]
    category: str
    risk: str
    suggestions: list[str] = field(default_factory=list)
    legal_basis: str = ""
    field_name: str = ""


@dataclass
class ComplianceResult:
    verdict: str
    hits: list[ComplianceHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "hits": [
                {
                    "rule_id": h.rule_id,
                    "surface": h.surface,
                    "matched_text": h.matched_text,
                    "span": list(h.span),
                    "category": h.category,
                    "risk": h.risk,
                    "suggestions": h.suggestions,
                    "legal_basis": h.legal_basis,
                    "field_name": h.field_name,
                }
                for h in self.hits
            ],
        }


class ComplianceChecker:
    _RANK_ORDER = {"pass": 0, "hint": 1, "review": 2, "block": 3}
    _RISK_RANK = {"low": 0, "medium": 1, "high": 2}
    _RISK_TO_VERDICT = {"high": "block", "medium": "review", "low": "hint"}

    def __init__(self, lexicon_path: str | Path | None = None):
        path = Path(lexicon_path) if lexicon_path else LEXICON_PATH
        with open(path, encoding="utf-8") as f:
            self._lexicon: dict = json.load(f)
        self._rules: list[dict] = self._lexicon.get("rules", [])
        self._whitelist_phrases: list[str] = sorted(
            self._lexicon.get("whitelist", {}).get("phrases", []),
            key=len, reverse=True,
        )
        self._whitelist_regexes: list[re.Pattern] = [
            re.compile(p)
            for p in self._lexicon.get("whitelist", {}).get("regex", [])
        ]
        self._variant_map: dict[str, str] = self._lexicon.get("variant_map", {})
        self._zw_chars: set[str] = set(self._lexicon.get("zero_width_chars", []))
        self._sep: str = self._lexicon.get(
            "separator_pattern",
            r"[\s\*\-~·—–_\.。、()\[\]（）【】\u200b\u200c\u200d\ufeff]{0,3}",
        )
        self._categories: dict[str, dict] = {
            c["id"]: c for c in self._lexicon.get("categories", [])
        }
        self._long_rules = sorted(self._rules, key=lambda r: len(r.get("surface", "")), reverse=True)

    # ------------------------------------------------------------------
    # Text normalization
    # ------------------------------------------------------------------

    def normalize(self, text: str) -> tuple[str, list[int]]:
        """Remove zero-width chars, normalize full-width spaces, and apply variant_map; return (normalized, pos_map).

        pos_map[i] = index in *text* of the character that became normalized[i].
        """
        result: list[str] = []
        pos_map: list[int] = []
        for i, ch in enumerate(text):
            if ch in self._zw_chars:
                continue
            if ch == "\u3000":
                result.append(" ")
                pos_map.append(i)
                continue
            mapped = self._variant_map.get(ch, ch)
            result.append(mapped)
            pos_map.append(i)
        return "".join(result), pos_map

    # ------------------------------------------------------------------
    # Whitelist
    # ------------------------------------------------------------------

    def _whitelist_spans(self, norm: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for phrase in self._whitelist_phrases:
            start = 0
            while True:
                idx = norm.find(phrase, start)
                if idx == -1:
                    break
                spans.append((idx, idx + len(phrase)))
                start = idx + 1
        for pat in self._whitelist_regexes:
            for m in pat.finditer(norm):
                spans.append((m.start(), m.end()))
        return spans

    @staticmethod
    def _overlaps(span: tuple[int, int], wl: list[tuple[int, int]]) -> bool:
        return any(not (span[1] <= ws or span[0] >= we) for ws, we in wl)

    @staticmethod
    def _in_negation_context(norm: str, ns: int, ne: int, window: int = 20) -> bool:
        """Check if the match is within a negation/warning context (e.g., '请勿相信...夸大')."""
        left_start = max(0, ns - window)
        left_ctx = norm[left_start:ns]
        negation_patterns = [
            "请勿相信", "不要相信", "不能相信", "请勿", "不要", "不能", "不含", "没有",
            "警告", "警惕", "避免", "防范", "并非", "不是",
        ]
        return any(pat in left_ctx for pat in negation_patterns)

    # ------------------------------------------------------------------
    # Rule matching
    # ------------------------------------------------------------------

    def _check_rule(self, text: str, norm: str, pos_map: list[int], rule: dict, wl: list[tuple[int, int]]) -> ComplianceHit | None:
        surface = rule.get("surface", "")
        match_type = rule.get("match_type", "keyword")
        risk = rule.get("risk", "medium")
        category = rule.get("category", "")
        rule_id = rule.get("id", "")
        suggestions = rule.get("suggestions", [])
        legal_basis = rule.get("legal_basis", "") or self._categories.get(category, {}).get("legal_basis", "")

        candidates: list[tuple[int, int, str]] = []

        if match_type == "regex":
            pattern = rule.get("pattern", "")
            if not pattern:
                return None
            for m in re.finditer(pattern, norm):
                candidates.append((m.start(), m.end(), m.group()))
        else:
            start = 0
            while True:
                idx = norm.find(surface, start)
                if idx == -1:
                    break
                candidates.append((idx, idx + len(surface), surface))
                start = idx + 1

            if not candidates:
                esc = re.escape(surface)
                fuzzy = re.compile(self._sep.join(list(esc)))
                for m in fuzzy.finditer(norm):
                    if m.group() == surface:
                        continue
                    candidates.append((m.start(), m.end(), surface))
                    risk = self._escalate(risk)

        if not candidates:
            return None

        boundary = rule.get("boundary", {})
        block_suffixes: list[str] = boundary.get("block_suffixes", [])
        exceptions: list[str] = rule.get("exceptions", [])
        context = rule.get("context", {})
        window: int = context.get("window", 8)
        escalate_to: str = context.get("escalate_risk", "")
        boost_left: list[str] = context.get("boost_left", [])
        boost_right: list[str] = context.get("boost_right", [])

        for ns, ne, matched_surface in candidates:
            if exceptions:
                matched = False
                for exc in exceptions:
                    if norm[ns:].startswith(exc):
                        matched = True
                        break
                if matched:
                    continue

            if block_suffixes:
                right_after = norm[ne:ne + 2]
                if any(right_after.startswith(suf) for suf in block_suffixes):
                    continue

            if self._overlaps((ns, ne), wl):
                continue

            if self._in_negation_context(norm, ns, ne):
                continue

            final_risk = risk
            if boost_left or boost_right:
                left_start = max(0, ns - window)
                left_ctx = norm[left_start:ns]
                right_end = min(len(norm), ne + window)
                right_ctx = norm[ne:right_end]
                if any(w in left_ctx for w in boost_left) or any(w in right_ctx for w in boost_right):
                    if escalate_to and self._RISK_RANK.get(escalate_to, 0) > self._RISK_RANK.get(final_risk, 0):
                        final_risk = escalate_to

            orig_start = pos_map[ns] if ns < len(pos_map) else len(pos_map)
            orig_end_idx = ne - 1 if ne > 0 else 0
            if orig_end_idx < len(pos_map):
                orig_end = pos_map[orig_end_idx] + 1
            else:
                orig_end = len(pos_map)
            if orig_end <= orig_start:
                orig_end = orig_start + 1

            # matched_text 必须取【原文切片】而非归一化文本：
            # 归一化会把零宽字符移除、全角空格转空格、形近字替换，
            # 若直接返回 norm[ns:ne]，前端拿它去原文里匹配会失配，高亮也会标错。
            # span 已是原文坐标（经 pos_map 回标），这里取原文切片即与 span 严格自洽。
            matched_text = text[orig_start:orig_end]

            return ComplianceHit(
                rule_id=rule_id,
                surface=matched_surface,
                matched_text=matched_text,
                span=(orig_start, orig_end),
                category=category,
                risk=final_risk,
                suggestions=suggestions,
                legal_basis=legal_basis,
            )

        return None

    @staticmethod
    def _escalate(risk: str) -> str:
        return {"low": "medium", "medium": "high"}.get(risk, risk)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_text(self, text: str, field_name: str = "") -> list[ComplianceHit]:
        if not text or not text.strip():
            return []
        norm, pos_map = self.normalize(text)
        if not norm.strip():
            return []
        wl = self._whitelist_spans(norm)
        hits: list[ComplianceHit] = []
        for rule in self._long_rules:
            hit = self._check_rule(text, norm, pos_map, rule, wl)
            if hit:
                hit.field_name = field_name
                hits.append(hit)
        return hits

    def check_text(self, text: str) -> ComplianceResult:
        hits = self.scan_text(text)
        return self._compile(hits)

    def check_content(self, content: dict, content_type: str = "main_image") -> ComplianceResult:
        hits: list[ComplianceHit] = []
        if content_type == "main_image":
            for f in ("title", "headline", "sub_headline"):
                hits.extend(self.scan_text(content.get(f, ""), field_name=f))
            for i, pp in enumerate(content.get("proof_points", [])):
                hits.extend(self.scan_text(pp, field_name=f"proof_points[{i}]"))
        elif content_type == "video_script":
            for f in ("title", "hook", "cta"):
                hits.extend(self.scan_text(content.get(f, ""), field_name=f))
            for i, scene in enumerate(content.get("scenes", [])):
                hits.extend(self.scan_text(scene.get("voiceover", ""), field_name=f"scenes[{i}].voiceover"))
        else:
            for key, value in content.items():
                if isinstance(value, str) and value.strip():
                    hits.extend(self.scan_text(value, field_name=key))
                elif isinstance(value, list):
                    for j, item in enumerate(value):
                        if isinstance(item, str) and item.strip():
                            hits.extend(self.scan_text(item, field_name=f"{key}[{j}]"))
        return self._compile(hits)

    @staticmethod
    def _compile(hits: list[ComplianceHit]) -> ComplianceResult:
        if not hits:
            return ComplianceResult(verdict="pass", hits=hits)
        max_risk = max((h.risk for h in hits), key=lambda r: {"low": 0, "medium": 1, "high": 2}.get(r, 0))
        verdict = {"high": "block", "medium": "review", "low": "pass"}.get(max_risk, "review")
        return ComplianceResult(verdict=verdict, hits=hits)


_default_checker: ComplianceChecker | None = None


def get_checker() -> ComplianceChecker:
    global _default_checker
    if _default_checker is None:
        _default_checker = ComplianceChecker()
    return _default_checker


def check_text(text: str) -> ComplianceResult:
    return get_checker().check_text(text)


def check_content(content: dict, content_type: str = "main_image") -> ComplianceResult:
    return get_checker().check_content(content, content_type)
