# -*- coding: utf-8 -*-
"""大模型接入层（可选增强，零依赖实现）

边界很明确（对齐架构图）：**大模型不参与风险判定**。
  * 风险识别：确定性规则引擎（app/review.py）
  * 大模型职责：把已确定的命中结果组织成更自然的中文审查摘要与评论表达
  * 未配置 API Key 时自动降级为确定性模板，功能不缺失，只是文风更「工程化」

调用方式：OpenAI 兼容的 /chat/completions 接口，仅用标准库 urllib。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .utils import build_opener


def available(cfg) -> bool:
    llm = (cfg or {}).get("llm") or {}
    if not llm.get("enabled"):
        return False
    if not llm.get("base_url"):
        return False
    return bool(os.environ.get(llm.get("api_key_env", "OPENAI_API_KEY")))


def chat(cfg, system_prompt: str, user_prompt: str):
    llm = cfg["llm"]
    key = os.environ.get(llm.get("api_key_env", "OPENAI_API_KEY"), "")
    url = llm["base_url"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    payload = {
        "model": llm.get("model", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer %s" % key},
        method="POST",
    )
    try:
        with build_opener().open(req, timeout=llm.get("timeout", 30)) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data["choices"][0]["message"]["content"] or "").strip(), ""
    except urllib.error.HTTPError as exc:
        return "", "HTTP %s: %s" % (exc.code, exc.read()[:200])
    except Exception as exc:                                 # noqa: BLE001
        return "", str(exc)


def polish_summary(cfg, rule_summary: str, case: dict, hits: list):
    """让大模型润色摘要；失败则原样返回规则摘要（保证永不阻断主流程）。"""
    if not available(cfg):
        return rule_summary, "rule-template"
    sys_p = ("你是企业法务合同审查助手。只做中文表达润色，不得新增、删减或改变任何风险结论、"
             "风险等级、金额、条款编号与法律依据。输出 120-220 字，分点陈述，不用 Markdown 标题。")
    user_p = json.dumps({
        "合同标题": case.get("title"),
        "业务类型": case.get("business_type"),
        "综合风险等级": case.get("risk_level"),
        "结论": case.get("conclusion"),
        "命中风险": [{"名称": h.get("rule_name"), "等级": h.get("risk_level"),
                      "条款类型": h.get("clause_type")} for h in hits],
        "规则摘要原文": rule_summary,
    }, ensure_ascii=False, indent=2)
    text, err = chat(cfg, sys_p, user_p)
    if text:
        return text, "llm"
    return rule_summary, "rule-template(llm-failed:%s)" % (err or "unknown")


# ------------------------------------------------------------------ 二阶段复核
def _extract_json(raw: str) -> list | dict | None:
    """从 LLM 输出中提取 JSON —— 剥围栏、容前后废话、解析失败返回 None。

    为什么不用 jsonschema：零依赖铁律。这里只需要「拿到一个 JSON 数组或对象」，
    解析失败就整体降级为 rule-only，不需要精确校验 schema。
    """
    text = raw.strip()
    # 剥掉 ```json ... ``` 围栏（LLM 最常见的输出格式）
    if "```" in text:
        import re
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # 容忍前后废话：找第一个 [ 或 { 到最后一个 ] 或 }
    for start_ch, end_ch in (("[", "]"), ("{", "}")):
        s = text.find(start_ch)
        e = text.rfind(end_ch)
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def review_hits(cfg, case: dict, hits: list, text: str, paras: list) -> dict:
    """二阶段复核：对规则引擎的每条命中做语义判定。

    一阶段（规则引擎）全量召回 → 二阶段（LLM）逐条判定：
      - confirm       —— 真风险，规则判定正确
      - false_positive —— 误报，语义上不构成风险
      - need_human    —— 无法确定，建议人工复核

    设计约束：
      - 一次批量调用（所有命中打包成一个请求），不逐条请求
      - 只依据给定的合同原文片段判断，不引入外部法律常识
      - 未配置 Key / 调用失败 / JSON 解析失败 → 整体降级 rule-only，绝不阻断主流程
      - 判定依据（规则命中原文 + 上下文）全程留痕，保证可解释、可审计

    返回：
        {"source": "llm"|"rule-only", "reason": "",
         "items": {rule_id: {"verdict": ..., "confidence": ..., "reason": ..., "source": ...}}}
    """
    llm_cfg = (cfg or {}).get("llm") or {}
    verify_enabled = llm_cfg.get("verify_enabled", True)
    min_confidence = float(llm_cfg.get("verify_min_confidence", 0.6))

    def _rule_only(reason=""):
        """降级为纯规则模式：所有命中保留原判定，不做语义复核。"""
        items = {}
        for h in hits:
            rid = h.get("rule_id", "")
            items[rid] = {"verdict": "", "confidence": 0.0,
                          "reason": "", "source": "rule-only"}
        return {"source": "rule-only", "reason": reason, "items": items}

    if not hits:
        return _rule_only("无命中项，无需复核")

    if not verify_enabled:
        return _rule_only("verify_enabled=false")

    if not available(cfg):
        reason_parts = []
        if not llm_cfg.get("enabled"):
            reason_parts.append("llm.enabled=false")
        if not llm_cfg.get("base_url"):
            reason_parts.append("未配置 llm.base_url")
        key_env = llm_cfg.get("api_key_env", "OPENAI_API_KEY")
        if not os.environ.get(key_env):
            reason_parts.append("环境变量 %s 未设置" % key_env)
        return _rule_only("；".join(reason_parts) if reason_parts else "LLM 不可用")

    # 构建批量 prompt —— 把所有命中打包成一个请求
    hit_items = []
    for i, h in enumerate(hits):
        # 取命中位置前后的上下文（各 200 字），给 LLM 足够的判断依据
        cs = max(0, h.get("char_start", 0) - 200)
        ce = min(len(text), h.get("char_end", 0) + 200)
        context = text[cs:ce]
        hit_items.append({
            "序号": i + 1,
            "规则ID": h.get("rule_id"),
            "规则名称": h.get("rule_name"),
            "风险等级": h.get("risk_level"),
            "条款类型": h.get("clause_type"),
            "命中原文": h.get("evidence", ""),
            "规则判定理由": h.get("reason", ""),
            "上下文片段": context,
        })

    sys_p = ("你是企业法务合同审查的语义复核员。你的任务是对规则引擎已命中的风险条款做二次判定。\n"
             "判断规则：\n"
             "1. 只依据给定的合同原文片段和上下文判断，不要引入外部法律常识\n"
             "2. 如果命中原文在上下文中确实构成该规则描述的风险 → verdict=confirm\n"
             "3. 如果命中原文在上下文中已被删除/修改/不适用（如'该条款已删除'、'经协商取消'）→ verdict=false_positive\n"
             "4. 如果你无法确定 → verdict=need_human\n"
             "5. 对每条给出 0.0-1.0 的置信度和一句话理由\n\n"
             "你必须严格输出 JSON 数组，格式如下（不要输出其他内容）：\n"
             '[{"序号":1,"verdict":"confirm","confidence":0.85,"reason":"一句话理由"},...]')

    user_p = json.dumps({
        "合同标题": case.get("title"),
        "业务类型": case.get("business_type"),
        "命中项": hit_items,
    }, ensure_ascii=False, indent=2)

    raw, err = chat(cfg, sys_p, user_p)
    if not raw:
        return _rule_only("LLM 调用失败：%s" % (err or "unknown"))

    parsed = _extract_json(raw)
    if parsed is None:
        return _rule_only("LLM 输出非法 JSON，整体降级")

    # 兼容：模型可能返回 {"items": [...]} 或直接 [...]
    if isinstance(parsed, dict):
        parsed = parsed.get("items") or parsed.get("results") or []
    if not isinstance(parsed, list):
        return _rule_only("LLM 输出格式异常（期望数组），整体降级")

    # 按序号映射回每条命中
    verdict_map = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        idx = item.get("序号")
        if idx is not None:
            verdict_map[int(idx)] = item

    items = {}
    confirm_count = 0
    fp_count = 0
    human_count = 0
    for i, h in enumerate(hits):
        rid = h.get("rule_id", "")
        v = verdict_map.get(i + 1, {})
        verdict = v.get("verdict", "")
        confidence = float(v.get("confidence", 0.0))
        reason_text = v.get("reason", "")

        # 校验 verdict 合法性
        if verdict not in ("confirm", "false_positive", "need_human"):
            verdict = "need_human"
            reason_text = (reason_text + "；" if reason_text else "") + "LLM 返回非法 verdict，转人工"

        # 低置信度的 false_positive 不降权，转为 need_human
        if verdict == "false_positive" and confidence < min_confidence:
            verdict = "need_human"
            reason_text = (reason_text + "；" if reason_text else "") + \
                "置信度 %.2f 低于阈值 %.2f，转人工确认" % (confidence, min_confidence)

        items[rid] = {
            "verdict": verdict,
            "confidence": confidence,
            "reason": reason_text,
            "source": "llm",
        }
        if verdict == "confirm":
            confirm_count += 1
        elif verdict == "false_positive":
            fp_count += 1
        else:
            human_count += 1

    return {
        "source": "llm",
        "reason": "",
        "items": items,
        "stats": {"confirm": confirm_count, "false_positive": fp_count,
                  "need_human": human_count, "total": len(hits)},
    }


# ------------------------------------------------------------------ 模式对照（P1-05）
MODE_RULE = "rule"
MODE_RULE_LLM = "rule+llm"
MODE_LABEL = {
    MODE_RULE: "规则引擎模式",
    MODE_RULE_LLM: "规则引擎 + 模型润色模式",
}


def mode_info(cfg) -> dict:
    """当前可用模式与不可用原因 —— 演示时必须能「明示当前模式」（D-40）。"""
    llm = (cfg or {}).get("llm") or {}
    enabled = bool(llm.get("enabled"))
    has_url = bool(llm.get("base_url"))
    key_env = llm.get("api_key_env", "OPENAI_API_KEY")
    has_key = bool(os.environ.get(key_env))
    if enabled and has_url and has_key:
        mode, reason = MODE_RULE_LLM, ""
    else:
        mode = MODE_RULE
        missing = []
        if not enabled:
            missing.append("llm.enabled=false")
        if not has_url:
            missing.append("未配置 llm.base_url")
        if not has_key:
            missing.append("环境变量 %s 未设置" % key_env)
        reason = "；".join(missing)
    return {
        "mode": mode,
        "mode_label": MODE_LABEL[mode],
        "available": mode == MODE_RULE_LLM,
        "reason": reason,
        "model": llm.get("model", ""),
        "base_url_set": has_url,
        "key_env": key_env,
        "key_present": has_key,
        "fallback": "内置示范条款模板库（确定性生成，零依赖）",
        "note": ("风险判定 100% 由确定性规则引擎产出，大模型只改写措辞、不参与判定；"
                 "未配置 Key 时自动回退内置模板并明示当前模式。"),
    }
