"""
P09 AI Sales Assessment - FastAPI Backend
Port: 8090
Mock boundary: LLM scoring is rule-based, not real LLM calls.
"""

from __future__ import annotations

import csv
import io
import math
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# P01 客服跨模块客户端（真实 HTTP 调用，地址从 SERVICE_REGISTRY 解析）。
# 兼容两种启动方式：`python app/main.py`（app/ 在 sys.path）与 `import app.main`（项目根在 sys.path）。
try:
    from app import p01_client
except ImportError:  # pragma: no cover - 取决于启动方式
    import p01_client  # type: ignore

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="P09 AI 销售考核 · 云枢智能", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# 统一设计系统：把仓库根的 shared/ 挂到 /shared，使前端能引用
# shared/ui-kit/tokens.css（配色/间距唯一真源）与 shared/ui-kit/ui-kit.js（主题桥接）。
# 独立访问（:8090）与 shell iframe 挂载两种方式下路径一致。
_SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"
if _SHARED_DIR.exists():
    app.mount("/shared", StaticFiles(directory=str(_SHARED_DIR)), name="shared")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str  # "customer" | "agent" | "system"
    content: str
    timestamp: str = ""


class DimensionScore(BaseModel):
    dimension: str
    score: float  # 0-100
    deduction_reasons: list[str] = []
    highlights: list[str] = []


class ConversationScore(BaseModel):
    overall: float
    dimensions: list[DimensionScore]
    rule_violations: list[dict[str, Any]] = []
    suggestions: list[str] = []


class Conversation(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    store: str
    customer_name: str
    topic: str
    messages: list[Message]
    score: ConversationScore | None = None
    human_score: float | None = None
    created_at: str = ""
    duration_seconds: int = 0


class Agent(BaseModel):
    id: str
    name: str
    avatar_color: str
    store: str
    hire_date: str


class QualityRule(BaseModel):
    id: str
    name: str
    category: str  # "forbidden_word" | "required_script" | "response_time" | "tone" | "compliance"
    description: str
    penalty: float  # points deducted per violation
    enabled: bool = True
    keywords: list[str] = []
    pattern: str = ""


# ---------------------------------------------------------------------------
# Seed Data
# ---------------------------------------------------------------------------

AGENTS: list[Agent] = [
    Agent(id="agent-001", name="张伟", avatar_color="#3370FF", store="旗舰店 A", hire_date="2024-03-15"),
    Agent(id="agent-002", name="李娜", avatar_color="#00B96B", store="旗舰店 A", hire_date="2024-01-10"),
    Agent(id="agent-003", name="王芳", avatar_color="#F53F3F", store="旗舰店 B", hire_date="2023-11-20"),
    Agent(id="agent-004", name="陈杰", avatar_color="#FF7D00", store="旗舰店 B", hire_date="2024-06-01"),
    Agent(id="agent-005", name="刘洋", avatar_color="#866BFF", store="海外店", hire_date="2024-02-28"),
]

QUALITY_RULES: list[QualityRule] = [
    QualityRule(id="rule-001", name="禁止：粗鲁推诿用语", category="forbidden_word",
                description="坐席不得使用侮辱、敷衍、推诿式言辞", penalty=15,
                keywords=["笨蛋", "白痴", "不关我的事", "自己处理", "随便"]),
    QualityRule(id="rule-002", name="禁止：不实承诺", category="forbidden_word",
                description="坐席不得做出无法兑现的承诺", penalty=20,
                keywords=["保证", "百分百", "一定能", "向您承诺"]),
    QualityRule(id="rule-003", name="必须：开场问候话术", category="required_script",
                description="坐席首条消息需向客户问好", penalty=10,
                pattern="greeting"),
    QualityRule(id="rule-004", name="必须：结束送别话术", category="required_script",
                description="会话结束需有致谢与道别", penalty=5,
                pattern="closing"),
    QualityRule(id="rule-005", name="响应时长要求", category="response_time",
                description="平均响应时长须低于 30 秒", penalty=8,
                pattern="response_time_30s"),
    QualityRule(id="rule-006", name="必须：共情安抚", category="tone",
                description="客户投诉时坐席需表达理解与歉意", penalty=10,
                keywords=["理解", "抱歉", "对不起", "帮您"]),
    QualityRule(id="rule-007", name="禁止：正向提及竞品", category="compliance",
                description="坐席不得正面推荐或引导客户选择竞品", penalty=15,
                keywords=["别家更好", "去买别家", "选竞品更好"]),
    QualityRule(id="rule-008", name="必须：连带/升单推荐", category="required_script",
                description="合适场景下坐席应做升单或连带推荐", penalty=5,
                pattern="upsell"),
]

# --- Helper to generate realistic conversations ---

_TOPICS = [
    "商品咨询 - 护肤套装",
    "订单物流查询",
    "退货申请 - 尺码不合适",
    "投诉 - 包装破损",
    "活动咨询 - 双十一大促",
    "商品推荐 - 母亲节礼物",
    "发货延迟投诉",
    "退款申请 - 商品质量问题",
    "会员等级升级咨询",
    "商品使用方法指导",
    "企业批量采购咨询",
    "优惠券无法使用",
    "换货申请 - 更换颜色",
    "商品正品保障疑虑",
    "积分余额与有效期查询",
    "春季新品上架咨询",
    "在线支付失败问题",
    "尺码表选购咨询",
    "礼品包装服务申请",
    "月度订阅取消",
    "连带搭配购买意向",
    "VIP 专属优惠咨询",
]

_STORES = ["旗舰店 A", "旗舰店 B", "海外店"]

_CUSTOMER_NAMES = [
    "赵女士", "孙先生", "黄女士", "周先生", "吴女士",
    "徐先生", "马女士", "朱先生", "胡女士", "郭先生",
    "林女士", "何先生", "高女士", "罗先生", "郑女士",
    "梁先生", "宋女士", "谢先生", "唐女士", "韩先生",
    "冯女士", "邓先生",
]


def _make_messages(topic: str, agent_quality: str) -> list[Message]:
    """Generate a realistic conversation based on topic and agent quality level."""
    base_time = datetime(2025, 3, 15, 10, 0, 0)
    msgs: list[dict] = []

    # Greeting
    if agent_quality in ("good", "excellent"):
        msgs.append({"role": "agent", "content": "您好，欢迎光临云枢智能旗舰店！很高兴为您服务，请问有什么可以帮您的吗？", "offset": 0})
    else:
        msgs.append({"role": "agent", "content": "在的，您有什么事？", "offset": 0})

    msgs.append({"role": "customer", "content": _customer_query(topic), "offset": 15})

    # Agent response
    if agent_quality == "excellent":
        msgs.append({"role": "agent", "content": _excellent_response(topic), "offset": 28})
        msgs.append({"role": "customer", "content": _customer_followup(topic, "positive"), "offset": 45})
        msgs.append({"role": "agent", "content": _excellent_closing(topic), "offset": 60})
    elif agent_quality == "good":
        msgs.append({"role": "agent", "content": _good_response(topic), "offset": 25})
        msgs.append({"role": "customer", "content": _customer_followup(topic, "neutral"), "offset": 42})
        msgs.append({"role": "agent", "content": _good_closing(), "offset": 58})
    elif agent_quality == "average":
        msgs.append({"role": "agent", "content": _average_response(topic), "offset": 35})
        msgs.append({"role": "customer", "content": _customer_followup(topic, "neutral"), "offset": 55})
        msgs.append({"role": "agent", "content": "还有其他需要帮忙的吗？", "offset": 80})
        msgs.append({"role": "customer", "content": "没有了，就这些，谢谢。", "offset": 95})
        msgs.append({"role": "agent", "content": "再见。", "offset": 100})
    else:  # poor
        msgs.append({"role": "agent", "content": _poor_response(topic), "offset": 45})
        msgs.append({"role": "customer", "content": _customer_followup(topic, "negative"), "offset": 65})
        msgs.append({"role": "agent", "content": "不关我的事，您自己处理。", "offset": 90})
        msgs.append({"role": "customer", "content": "这服务态度也太差了，我要找你们主管来处理。", "offset": 110})
        msgs.append({"role": "agent", "content": "随便，再见。", "offset": 120})

    result = []
    for m in msgs:
        t = base_time + timedelta(seconds=m["offset"])
        result.append(Message(role=m["role"], content=m["content"], timestamp=t.isoformat()))
    return result


def _customer_query(topic: str) -> str:
    mapping = {
        "商品咨询 - 护肤套装": "你好，我想了解一下你们的护肤套装，成分都有哪些？敏感肌能用吗？",
        "订单物流查询": "您好，我三天前下的订单一直没发货，麻烦帮我查下物流，订单号 20250312-4521。",
        "退货申请 - 尺码不合适": "我收到的尺码不对，下单买的是 M 码，发来是 XL 码，想申请退货。",
        "投诉 - 包装破损": "快递到的时候外盒已经压扁了，里面的商品看着还行，但这套包装是我要送人的。",
        "活动咨询 - 双十一大促": "请问双十一活动什么时候开始？现在有提前预约的优惠吗？",
        "商品推荐 - 母亲节礼物": "想给我妈妈挑一份礼物，她五十多岁，有合适的套装推荐吗？",
        "发货延迟投诉": "订单显示五天前就该送到了，物流到现在还没更新，这到底是怎么了？",
        "退款申请 - 商品质量问题": "收到的商品有质量问题，拉链是坏的，我要申请全额退款。",
        "会员等级升级咨询": "怎么升级成金牌会员？升级之后都有哪些权益？",
        "商品使用方法指导": "刚买的精华液应该怎么用？是早上用还是晚上用比较好？",
        "企业批量采购咨询": "公司年会想采购两百件，能走批量采购价吗？多久能到货？",
        "优惠券无法使用": "我有一张二十元的优惠券，结算的时候一直勾选不上，能帮我看看吗？",
        "换货申请 - 更换颜色": "蓝色这款我想换成黑色，可以吗？需要自己承担运费吗？",
        "商品正品保障疑虑": "怎么确认买到的是正品？我在别的平台看到过仿货，有点不放心。",
        "积分余额与有效期查询": "帮我查一下我账户里还有多少积分？什么时候过期？",
        "春季新品上架咨询": "春季有上新吗？想给衣柜添两件新款式。",
        "在线支付失败问题": "付款一直失败，换了两张卡都提示交易异常，是什么原因？",
        "尺码表选购咨询": "我的身材在 M 和 L 之间，想要宽松一点的版型，选哪个码更合适？",
        "礼品包装服务申请": "可以加一份礼品包装吗？这是送给朋友的生日礼物。",
        "月度订阅取消": "我想取消每月的订阅推送，具体怎么操作？",
        "连带搭配购买意向": "我正在看面霜，有没有同系列可以搭配的爽肤水？",
        "VIP 专属优惠咨询": "我是 VIP 会员，最近有什么专属优惠可以了解一下吗？",
    }
    return mapping.get(topic, "我想咨询一下你们的产品。")


def _excellent_response(topic: str) -> str:
    return f"我完全理解您的顾虑，这件事我现在就帮您核实处理。关于{topic.split(' - ')[1] if ' - ' in topic else '这个问题'}，我会全程跟进，尽快给您一个明确的答复，也请您放心。"


def _good_response(topic: str) -> str:
    return "感谢您的反馈，这个问题我很乐意帮您处理。我这边先帮您核实一下订单详情，请您稍等片刻。"


def _average_response(topic: str) -> str:
    return "好的，我这边查一下，您稍等片刻。"


def _poor_response(topic: str) -> str:
    return "这个我不知道，详情您自己看网站吧。"


def _excellent_closing(topic: str) -> str:
    return "很高兴能帮到您！请问还有其他可以为您做的吗？另外同步一个信息，我们刚上了一批新品，还有一套和您这次选购很搭配的组合装，或许您会感兴趣，需要我把详细资料发给您看看吗？感谢您选择云枢智能，祝您生活愉快，期待下次再为您服务，再见！"


def _good_closing() -> str:
    return "不客气！如果您还有其他问题，随时联系我们就好。感谢您选择我们，祝您购物愉快，天天开心！"


def _customer_followup(topic: str, mood: str) -> str:
    if mood == "positive":
        return "太好了，非常感谢您的耐心解答，服务真的很周到！"
    elif mood == "negative":
        return "这样一点都不解决问题，我都等好几天了，好像没人管一样。"
    else:
        return "好的，我明白了，谢谢您帮忙查。"


# Agent quality profiles: agent_id -> quality level
_AGENT_QUALITY = {
    "agent-001": "excellent",
    "agent-002": "good",
    "agent-003": "average",
    "agent-004": "poor",
    "agent-005": "good",
}


def _generate_conversations() -> list[Conversation]:
    """Generate 22 demo conversations across 5 agents."""
    convos: list[Conversation] = []
    random.seed(42)  # deterministic

    agent_conv_counts = {
        "agent-001": 6,
        "agent-002": 5,
        "agent-003": 4,
        "agent-004": 3,
        "agent-005": 4,
    }

    topic_idx = 0
    for agent in AGENTS:
        quality = _AGENT_QUALITY[agent.id]
        count = agent_conv_counts[agent.id]
        for i in range(count):
            topic = _TOPICS[topic_idx % len(_TOPICS)]
            topic_idx += 1
            cid = f"conv-{agent.id[-3:]}-{i+1:03d}"
            customer = _CUSTOMER_NAMES[(topic_idx + i) % len(_CUSTOMER_NAMES)]
            msgs = _make_messages(topic, quality)
            duration = msgs[-1].timestamp and int(
                (datetime.fromisoformat(msgs[-1].timestamp) - datetime.fromisoformat(msgs[0].timestamp)).total_seconds()
            ) or 0
            base_date = datetime(2025, 3, 1) + timedelta(days=random.randint(0, 28))

            conv = Conversation(
                id=cid,
                agent_id=agent.id,
                agent_name=agent.name,
                store=agent.store,
                customer_name=customer,
                topic=topic,
                messages=msgs,
                created_at=base_date.isoformat(),
                duration_seconds=max(duration, 30),
            )
            conv.score = _rule_based_score(conv)
            # Human scores: correlated with AI but with some variance
            if conv.score:
                noise = random.uniform(-12, 12)
                conv.human_score = max(0, min(100, conv.score.overall + noise))
            convos.append(conv)

    return convos


# ---------------------------------------------------------------------------
# Rule-based Mock Scoring Engine
# ---------------------------------------------------------------------------

FORBIDDEN_WORDS = [
    "笨蛋", "白痴", "不关我的事", "自己处理", "随便",
    "保证", "百分百", "一定能", "向您承诺",
    "不知道", "看网站", "别家更好",
]

GREETING_KEYWORDS = ["您好", "欢迎", "很高兴", "请问", "帮您"]
CLOSING_KEYWORDS = ["感谢", "祝您", "愉快", "再见", "不客气", "期待"]
EMPATHY_KEYWORDS = ["理解", "抱歉", "对不起", "顾虑", "帮您"]
UPSELL_KEYWORDS = ["另外", "推荐", "新品", "搭配", "感兴趣", "顺便"]


def _rule_based_score(conv: Conversation) -> ConversationScore:
    """Score a conversation using rule-based heuristics (mock LLM)."""
    agent_texts = " ".join(m.content.lower() for m in conv.messages if m.role == "agent")
    all_text = " ".join(m.content.lower() for m in conv.messages)
    violations: list[dict] = []
    deduction_reasons_by_dim: dict[str, list[str]] = {
        "服务态度": [], "专业度": [], "需求挖掘": [],
        "促成转化": [], "合规性": [],
    }
    highlights_by_dim: dict[str, list[str]] = {
        "服务态度": [], "专业度": [], "需求挖掘": [],
        "促成转化": [], "合规性": [],
    }

    # --- 服务态度 (0-100) ---
    attitude = 80.0
    for word in FORBIDDEN_WORDS:
        if word in agent_texts:
            attitude -= 10
            violations.append({"rule": "forbidden_word", "word": word, "penalty": 10})
            deduction_reasons_by_dim["服务态度"].append(f"使用违规用语：'{word}'")
    if any(kw in agent_texts for kw in GREETING_KEYWORDS):
        attitude += 5
        highlights_by_dim["服务态度"].append("开场问候规范")
    if any(kw in agent_texts for kw in EMPATHY_KEYWORDS):
        attitude += 5
        highlights_by_dim["服务态度"].append("体现了共情安抚")
    else:
        attitude -= 5
        deduction_reasons_by_dim["服务态度"].append("缺少共情安抚表达")
    if any(kw in agent_texts for kw in CLOSING_KEYWORDS):
        attitude += 5
        highlights_by_dim["服务态度"].append("结束送别规范")
    else:
        attitude -= 10
        deduction_reasons_by_dim["服务态度"].append("缺少规范结束语")
    attitude = max(0, min(100, attitude))

    # --- 专业度 (0-100) ---
    expertise = 70.0
    if len(agent_texts) > 100:
        expertise += 10
        highlights_by_dim["专业度"].append("回复详实充分")
    else:
        deduction_reasons_by_dim["专业度"].append("回复过于简略")
        expertise -= 10
    if conv.duration_seconds < 60:
        expertise -= 5
        deduction_reasons_by_dim["专业度"].append("会话时长偏短，可能存在服务不充分")
    if any(kw in agent_texts for kw in ["查一下", "核实", "详情"]):
        expertise += 5
        highlights_by_dim["专业度"].append("主动核查客户问题")
    expertise = max(0, min(100, expertise))

    # --- 需求挖掘 (0-100) ---
    demand = 60.0
    customer_msgs = [m for m in conv.messages if m.role == "customer"]
    if len(customer_msgs) >= 3:
        demand += 15
        highlights_by_dim["需求挖掘"].append("与客户形成多轮互动")
    else:
        deduction_reasons_by_dim["需求挖掘"].append("客户互动轮次不足")
    if any(kw in agent_texts for kw in ["还有其他", "其他", "更多"]):
        demand += 10
        highlights_by_dim["需求挖掘"].append("主动挖掘延伸需求")
    else:
        deduction_reasons_by_dim["需求挖掘"].append("未挖掘延伸需求")
    demand = max(0, min(100, demand))

    # --- 促成转化 (0-100) ---
    conversion = 65.0
    if any(kw in agent_texts for kw in UPSELL_KEYWORDS):
        conversion += 15
        highlights_by_dim["促成转化"].append("做了升单/连带推荐")
    else:
        deduction_reasons_by_dim["促成转化"].append("未做升单或连带推荐")
    if "感谢您" in agent_texts or "选择我们" in agent_texts:
        conversion += 10
        highlights_by_dim["促成转化"].append("强化了购买决策")
    conversion = max(0, min(100, conversion))

    # --- 合规性 (0-100) ---
    compliance = 90.0
    compliance_violations = [v for v in violations if v["rule"] == "forbidden_word" and v["word"] in
                             ["别家更好", "去买别家", "选竞品更好"]]
    if compliance_violations:
        compliance -= 20 * len(compliance_violations)
        deduction_reasons_by_dim["合规性"].append("正面提及竞品")
    false_promise = [v for v in violations if v["word"] in ["保证", "百分百", "一定能", "向您承诺"]]
    if false_promise:
        compliance -= 15 * len(false_promise)
        deduction_reasons_by_dim["合规性"].append("做出不实承诺")
    compliance = max(0, min(100, compliance))

    # Build dimension scores
    dimensions = [
        DimensionScore(dimension="服务态度", score=round(attitude, 1),
                       deduction_reasons=deduction_reasons_by_dim["服务态度"],
                       highlights=highlights_by_dim["服务态度"]),
        DimensionScore(dimension="专业度", score=round(expertise, 1),
                       deduction_reasons=deduction_reasons_by_dim["专业度"],
                       highlights=highlights_by_dim["专业度"]),
        DimensionScore(dimension="需求挖掘", score=round(demand, 1),
                       deduction_reasons=deduction_reasons_by_dim["需求挖掘"],
                       highlights=highlights_by_dim["需求挖掘"]),
        DimensionScore(dimension="促成转化", score=round(conversion, 1),
                       deduction_reasons=deduction_reasons_by_dim["促成转化"],
                       highlights=highlights_by_dim["促成转化"]),
        DimensionScore(dimension="合规性", score=round(compliance, 1),
                       deduction_reasons=deduction_reasons_by_dim["合规性"],
                       highlights=highlights_by_dim["合规性"]),
    ]

    # Weighted overall
    weights = {"服务态度": 0.25, "专业度": 0.25, "需求挖掘": 0.15, "促成转化": 0.20, "合规性": 0.15}
    overall = sum(d.score * weights[d.dimension] for d in dimensions)

    # Suggestions
    suggestions = []
    for d in dimensions:
        if d.score < 60:
            suggestions.append(f"需重点改进{d.dimension}：{'；'.join(d.deduction_reasons[:2]) if d.deduction_reasons else '复核质检规范'}")
        elif d.score < 75:
            suggestions.append(f"{d.dimension}仍有提升空间，建议聚焦：{d.deduction_reasons[0] if d.deduction_reasons else '服务规范最佳实践'}")
    if not suggestions:
        suggestions.append("整体表现优秀，请继续保持高水准。")

    return ConversationScore(
        overall=round(overall, 1),
        dimensions=dimensions,
        rule_violations=violations,
        suggestions=suggestions,
    )


CONVERSATIONS: list[Conversation] = _generate_conversations()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "p09-ai-sales-assessment", "version": "1.0.0"}


@app.get("/api/v1/stats")
async def get_stats():
    """Dashboard overview statistics."""
    total = len(CONVERSATIONS)
    scored = [c for c in CONVERSATIONS if c.score]
    avg_score = sum(c.score.overall for c in scored) / len(scored) if scored else 0

    # Score distribution
    brackets = {"0-40": 0, "40-60": 0, "60-75": 0, "75-90": 0, "90-100": 0}
    for c in scored:
        s = c.score.overall
        if s < 40:
            brackets["0-40"] += 1
        elif s < 60:
            brackets["40-60"] += 1
        elif s < 75:
            brackets["60-75"] += 1
        elif s < 90:
            brackets["75-90"] += 1
        else:
            brackets["90-100"] += 1

    # Dimension averages
    dim_avgs: dict[str, list[float]] = {}
    for c in scored:
        for d in c.score.dimensions:
            dim_avgs.setdefault(d.dimension, []).append(d.score)
    dim_averages = {k: round(sum(v) / len(v), 1) for k, v in dim_avgs.items()}

    # Violations count
    total_violations = sum(len(c.score.rule_violations) for c in scored if c.score)

    # Store breakdown
    stores: dict[str, list[float]] = {}
    for c in scored:
        stores.setdefault(c.store, []).append(c.score.overall)
    store_avgs = {k: round(sum(v) / len(v), 1) for k, v in stores.items()}

    return {
        "total_conversations": total,
        "total_agents": len(AGENTS),
        "average_score": round(avg_score, 1),
        "score_distribution": brackets,
        "dimension_averages": dim_averages,
        "total_violations": total_violations,
        "store_averages": store_avgs,
        "evaluation_period": "2025-03-01 至 2025-03-31",
    }


@app.get("/api/v1/leaderboard")
async def get_leaderboard():
    """Agent ranking by overall score."""
    agent_scores: dict[str, list[float]] = {}
    agent_convos: dict[str, int] = {}
    for c in CONVERSATIONS:
        if c.score:
            agent_scores.setdefault(c.agent_id, []).append(c.score.overall)
            agent_convos[c.agent_id] = agent_convos.get(c.agent_id, 0) + 1

    ranking = []
    for agent in AGENTS:
        scores = agent_scores.get(agent.id, [])
        if scores:
            avg = round(sum(scores) / len(scores), 1)
            ranking.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "avatar_color": agent.avatar_color,
                "store": agent.store,
                "conversation_count": len(scores),
                "average_score": avg,
                "max_score": round(max(scores), 1),
                "min_score": round(min(scores), 1),
            })

    ranking.sort(key=lambda x: x["average_score"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {"leaderboard": ranking}


@app.get("/api/v1/agents/{agent_id}")
async def get_agent_report(agent_id: str):
    """Individual agent report with radar chart data."""
    agent = next((a for a in AGENTS if a.id == agent_id), None)
    if not agent:
        raise HTTPException(404, "未找到该坐席")

    agent_convs = [c for c in CONVERSATIONS if c.agent_id == agent_id and c.score]
    if not agent_convs:
        raise HTTPException(404, "该坐席暂无已评分的会话")

    # Radar data (dimension averages)
    dim_data: dict[str, list[float]] = {}
    for c in agent_convs:
        for d in c.score.dimensions:
            dim_data.setdefault(d.dimension, []).append(d.score)
    radar = [{"dimension": k, "score": round(sum(v) / len(v), 1)} for k, v in dim_data.items()]

    # Score trend
    trend = sorted(
        [{"date": c.created_at[:10], "score": c.score.overall, "conversation_id": c.id} for c in agent_convs],
        key=lambda x: x["date"],
    )

    # Strengths and weaknesses
    avg_overall = round(sum(c.score.overall for c in agent_convs) / len(agent_convs), 1)
    strengths = []
    weaknesses = []
    for r in radar:
        if r["score"] >= 80:
            strengths.append(f"{r['dimension']} ({r['score']})")
        elif r["score"] < 65:
            weaknesses.append(f"{r['dimension']} ({r['score']})")

    # Improvement suggestions
    suggestions = []
    for c in agent_convs:
        suggestions.extend(c.score.suggestions)
    unique_suggestions = list(dict.fromkeys(suggestions))[:5]

    # Common violations
    violation_counts: dict[str, int] = {}
    for c in agent_convs:
        for v in c.score.rule_violations:
            key = v.get("word", v.get("rule", "unknown"))
            violation_counts[key] = violation_counts.get(key, 0) + 1
    top_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "avatar_color": agent.avatar_color,
            "store": agent.store,
            "hire_date": agent.hire_date,
        },
        "summary": {
            "total_conversations": len(agent_convs),
            "average_score": avg_overall,
            "max_score": round(max(c.score.overall for c in agent_convs), 1),
            "min_score": round(min(c.score.overall for c in agent_convs), 1),
        },
        "radar": radar,
        "score_trend": trend,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvement_suggestions": unique_suggestions,
        "top_violations": [{"keyword": k, "count": v} for k, v in top_violations],
        "conversations": [
            {
                "id": c.id,
                "topic": c.topic,
                "customer": c.customer_name,
                "score": c.score.overall,
                "date": c.created_at[:10],
                "duration_seconds": c.duration_seconds,
            }
            for c in sorted(agent_convs, key=lambda x: x.created_at, reverse=True)
        ],
    }


@app.get("/api/v1/conversations")
async def list_conversations(
    agent_id: str | None = None,
    store: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List conversations with optional filters."""
    filtered = CONVERSATIONS[:]
    if agent_id:
        filtered = [c for c in filtered if c.agent_id == agent_id]
    if store:
        filtered = [c for c in filtered if c.store == store]
    if min_score is not None:
        filtered = [c for c in filtered if c.score and c.score.overall >= min_score]
    if max_score is not None:
        filtered = [c for c in filtered if c.score and c.score.overall <= max_score]

    filtered.sort(key=lambda x: x.created_at, reverse=True)
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = filtered[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": c.id,
                "agent_id": c.agent_id,
                "agent_name": c.agent_name,
                "store": c.store,
                "customer_name": c.customer_name,
                "topic": c.topic,
                "score": c.score.overall if c.score else None,
                "human_score": c.human_score,
                "created_at": c.created_at[:10],
                "duration_seconds": c.duration_seconds,
                "message_count": len(c.messages),
            }
            for c in page_items
        ],
    }


@app.get("/api/v1/conversations/{conv_id}")
async def get_conversation_detail(conv_id: str):
    """Conversation detail with full messages and score breakdown."""
    conv = next((c for c in CONVERSATIONS if c.id == conv_id), None)
    if not conv:
        raise HTTPException(404, "未找到该会话")

    return {
        "id": conv.id,
        "agent_id": conv.agent_id,
        "agent_name": conv.agent_name,
        "store": conv.store,
        "customer_name": conv.customer_name,
        "topic": conv.topic,
        "created_at": conv.created_at,
        "duration_seconds": conv.duration_seconds,
        "messages": [m.model_dump() for m in conv.messages],
        "score": conv.score.model_dump() if conv.score else None,
        "human_score": conv.human_score,
    }


@app.post("/api/v1/evaluate")
async def evaluate_conversation(
    messages: list[dict[str, str]],
    agent_id: str = "agent-001",
    store: str = "旗舰店 A",
):
    """Evaluate a new conversation (mock LLM scoring)."""
    agent = next((a for a in AGENTS if a.id == agent_id), AGENTS[0])
    parsed_msgs = []
    for m in messages:
        parsed_msgs.append(Message(
            role=m.get("role", "customer"),
            content=m.get("content", ""),
            timestamp=m.get("timestamp", datetime.now().isoformat()),
        ))

    if not parsed_msgs:
        raise HTTPException(400, "未提供任何会话消息")

    cid = f"conv-new-{uuid.uuid4().hex[:8]}"
    conv = Conversation(
        id=cid,
        agent_id=agent.id,
        agent_name=agent.name,
        store=store,
        customer_name="新客户",
        topic="实时评估会话",
        messages=parsed_msgs,
        created_at=datetime.now().isoformat(),
        duration_seconds=0,
    )
    score = _rule_based_score(conv)
    conv.score = score
    CONVERSATIONS.append(conv)

    return {
        "conversation_id": cid,
        "score": score.model_dump(),
        "mock_notice": "本次评分使用基于规则的启发式算法（mock），并非真实 LLM 调用。",
    }


@app.get("/api/v1/rules")
async def get_rules():
    """List all quality rules."""
    return {
        "rules": [r.model_dump() for r in QUALITY_RULES],
        "total": len(QUALITY_RULES),
    }


@app.put("/api/v1/rules/{rule_id}")
async def update_rule(rule_id: str, body: dict):
    """Update a quality rule (toggle enable, change penalty)."""
    rule = next((r for r in QUALITY_RULES if r.id == rule_id), None)
    if not rule:
        raise HTTPException(404, "未找到该质检规则")
    if "enabled" in body:
        rule.enabled = bool(body["enabled"])
    if "penalty" in body:
        rule.penalty = float(body["penalty"])
    if "description" in body:
        rule.description = str(body["description"])
    return {"rule": rule.model_dump(), "message": "质检规则已更新"}


@app.get("/api/v1/agreement")
async def get_agreement():
    """Human-AI agreement statistics with Kappa coefficient."""
    pairs = [(c.human_score, c.score.overall) for c in CONVERSATIONS if c.human_score is not None and c.score]
    if not pairs:
        return {"error": "暂无可用于比对的人工评分与 AI 评分"}

    # Discretize into categories for Kappa
    # 注意：以下 excellent/good/average/poor 是机器可读的分类键（前端用它们索引 confusion_matrix），
    # 不作为展示文案；界面上的中文标签由前端映射表负责。
    def categorize(score: float) -> str:
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 55:
            return "average"
        else:
            return "poor"

    categories = ["excellent", "good", "average", "poor"]
    human_cats = [categorize(h) for h, _ in pairs]
    ai_cats = [categorize(a) for _, a in pairs]
    n = len(pairs)

    # Observed agreement
    observed = sum(1 for h, a in zip(human_cats, ai_cats) if h == a) / n

    # Expected agreement
    expected = 0
    for cat in categories:
        p_h = human_cats.count(cat) / n
        p_a = ai_cats.count(cat) / n
        expected += p_h * p_a

    # Cohen's Kappa
    kappa = (observed - expected) / (1 - expected) if (1 - expected) > 0 else 0

    # Confusion matrix
    matrix: dict[str, dict[str, int]] = {cat: {c2: 0 for c2 in categories} for cat in categories}
    for h, a in zip(human_cats, ai_cats):
        matrix[h][a] += 1

    # Correlation stats
    human_scores = [h for h, _ in pairs]
    ai_scores = [a for _, a in pairs]
    mean_h = sum(human_scores) / n
    mean_a = sum(ai_scores) / n
    cov = sum((h - mean_h) * (a - mean_a) for h, a in pairs) / n
    std_h = math.sqrt(sum((h - mean_h) ** 2 for h in human_scores) / n)
    std_a = math.sqrt(sum((a - mean_a) ** 2 for a in ai_scores) / n)
    pearson_r = cov / (std_h * std_a) if std_h * std_a > 0 else 0
    mae = sum(abs(h - a) for h, a in pairs) / n

    # Per-category breakdown
    cat_breakdown = {}
    for cat in categories:
        cat_pairs = [(h, a) for h, a, hc in zip(human_scores, ai_scores, human_cats) if hc == cat]
        if cat_pairs:
            cat_breakdown[cat] = {
                "count": len(cat_pairs),
                "avg_human": round(sum(h for h, _ in cat_pairs) / len(cat_pairs), 1),
                "avg_ai": round(sum(a for _, a in cat_pairs) / len(cat_pairs), 1),
                "avg_diff": round(sum(abs(h - a) for h, a in cat_pairs) / len(cat_pairs), 1),
            }

    return {
        "kappa": round(kappa, 4),
        "kappa_interpretation": (
            "近乎完全一致" if kappa > 0.8 else
            "高度一致" if kappa > 0.6 else
            "中度一致" if kappa > 0.4 else
            "一般一致" if kappa > 0.2 else "微弱一致"
        ),
        "observed_agreement": round(observed, 4),
        "expected_agreement": round(expected, 4),
        "pearson_correlation": round(pearson_r, 4),
        "mean_absolute_error": round(mae, 1),
        "sample_size": n,
        "confusion_matrix": matrix,
        "category_breakdown": cat_breakdown,
        "mock_notice": "Kappa 系数由演示数据计算得出，人工评分为模拟值，并非真实质检会话。",
    }


@app.post("/api/v1/import")
async def import_conversations(file: UploadFile = File(...)):
    """Import conversations from CSV or JSON file."""
    content = await file.read()
    filename = file.filename or "upload"
    imported = 0

    if filename.endswith(".json"):
        import json
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                msgs = [Message(**m) for m in item.get("messages", [])]
                if msgs:
                    conv = Conversation(
                        id=f"conv-import-{uuid.uuid4().hex[:8]}",
                        agent_id=item.get("agent_id", "agent-001"),
                        agent_name=item.get("agent_name", "导入坐席"),
                        store=item.get("store", "导入店铺"),
                        customer_name=item.get("customer_name", "客户"),
                        topic=item.get("topic", "导入会话"),
                        messages=msgs,
                        created_at=item.get("created_at", datetime.now().isoformat()),
                        duration_seconds=item.get("duration_seconds", 0),
                    )
                    conv.score = _rule_based_score(conv)
                    CONVERSATIONS.append(conv)
                    imported += 1

    elif filename.endswith(".csv"):
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        # Expected columns: agent_id, agent_name, store, customer_name, topic, role, content, timestamp
        groups: dict[str, list[dict]] = {}
        for row in reader:
            key = row.get("topic", "import")
            groups.setdefault(key, []).append(row)
        for topic, rows in groups.items():
            msgs = [Message(role=r.get("role", "customer"), content=r.get("content", ""), timestamp=r.get("timestamp", "")) for r in rows]
            first = rows[0]
            conv = Conversation(
                id=f"conv-import-{uuid.uuid4().hex[:8]}",
                agent_id=first.get("agent_id", "agent-001"),
                agent_name=first.get("agent_name", "导入坐席"),
                store=first.get("store", "导入店铺"),
                customer_name=first.get("customer_name", "客户"),
                topic=topic,
                messages=msgs,
                created_at=first.get("timestamp", datetime.now().isoformat()),
                duration_seconds=0,
            )
            conv.score = _rule_based_score(conv)
            CONVERSATIONS.append(conv)
            imported += 1
    else:
        raise HTTPException(400, "不支持的文件格式，请使用 .json 或 .csv")

    return {"imported": imported, "message": f"已导入 {imported} 段会话"}


# ---------------------------------------------------------------------------
# 跨模块：消费 P01 客服真实会话（红线：真实 HTTP 调用 + 降级不伪造）
# ---------------------------------------------------------------------------

class P01ImportRequest(BaseModel):
    sender_ids: list[str]
    agent_id: str = "agent-001"
    store: str = "旗舰店 A"


@app.get("/api/v1/p01/status")
async def p01_status():
    """探测 P01 客服是否在线，供前端标注数据来源（实时 / 降级）。"""
    return p01_client.health()


@app.post("/api/v1/import/from-p01")
async def import_from_p01(body: P01ImportRequest):
    """跨模块拉取 P01 真实客服会话并自动评分。

    数据流闭环：P01 会话 → P09 质检评分。地址从 SERVICE_REGISTRY 解析，未硬编码端口。
    P01 不可达时返回 degraded=True 且 imported=0，**不伪造任何会话**。
    """
    if not body.sender_ids:
        raise HTTPException(400, "sender_ids 不能为空")

    result = p01_client.fetch_conversations(body.sender_ids)
    if not result.get("ok"):
        return JSONResponse(status_code=200, content={
            "ok": False,
            "degraded": True,
            "source": "unavailable",
            "imported": 0,
            "url": result.get("url"),
            "error": result.get("error"),
            "notice": "P01 客服不可达，未导入任何会话（降级不伪造数据）。",
        })

    agent = next((a for a in AGENTS if a.id == body.agent_id), AGENTS[0])
    imported = 0
    ids: list[str] = []
    for conv_data in result["conversations"]:
        msgs = [
            Message(role=m["role"], content=m["content"],
                    timestamp=m.get("timestamp") or datetime.now().isoformat())
            for m in conv_data["messages"]
        ]
        if not msgs:
            continue
        session_tag = str(conv_data["session_id"])[:8]
        cid = f"conv-p01-{conv_data['sender_id']}-{session_tag}"
        conv = Conversation(
            id=cid,
            agent_id=agent.id,
            agent_name=agent.name,
            store=body.store,
            customer_name=conv_data["sender_id"],
            topic=f"P01 真实会话 {session_tag}",
            messages=msgs,
            created_at=datetime.now().isoformat(),
            duration_seconds=0,
        )
        conv.score = _rule_based_score(conv)
        CONVERSATIONS.append(conv)
        imported += 1
        ids.append(cid)

    return {
        "ok": True,
        "degraded": False,
        "source": "p01-live",
        "url": result.get("url"),
        "imported": imported,
        "conversation_ids": ids,
        "fetched_senders": result.get("fetched_senders"),
        "empty_senders": result.get("empty_senders"),
        "message": f"从 P01 客服真实导入 {imported} 段会话并完成评分",
    }


# Serve frontend
@app.get("/")
async def serve_index():
    return FileResponse(WEB_DIR / "index.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  P09 AI 销售考核 - 云枢智能")
    print("  http://localhost:8090")
    print("  [MOCK] 质检评分: 基于规则的模拟算法，非真实 LLM 调用")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8090)
