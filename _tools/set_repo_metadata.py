#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""云枢智能作品集 · GitHub 仓库「门面」元数据落地脚本（About / topics / homepage）。

设计约束（与 AGENTS.md 的证据纪律一致）：
  * 纯标准库（urllib.request），不引入任何新依赖，不需要 uv / requests。
  * Token **只从环境变量读**，不接受 `--token` 明文参数，不写盘、不回显（打印一律打码）。
  * **默认 dry-run**：先 GET 现状，只列出真的会变的字段，打印将要发送的 body；
    只有显式 `--yes` 才真发 PATCH / PUT。
  * `--self-test` 不联网、不需要 Token，校验参数解析 / topics 合法性与 20 上限 / dry-run 输出格式。

用法：
    python -X utf8 _tools\\set_repo_metadata.py --repo liyibo0410/yunshu-ai-portfolio
    python -X utf8 _tools\\set_repo_metadata.py --repo liyibo0410/yunshu-ai-portfolio --yes
    python -X utf8 _tools\\set_repo_metadata.py --description "..." --topics a,b,c
    python -X utf8 _tools\\set_repo_metadata.py --homepage ""          # 清空 Website
    python -X utf8 _tools\\set_repo_metadata.py --token-env GH_META_TOKEN
    python -X utf8 _tools\\set_repo_metadata.py --self-test

PowerShell 里给 Token（只在当前窗口生效，不进任何文件）：
    $env:GITHUB_TOKEN = 'github_pat_...'   # 不要写进脚本、不要写进被 git 跟踪的文件
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------- 常量

API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
ACCEPT_JSON = "application/vnd.github+json"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
USER_AGENT = "yunshu-ai-portfolio-metadata/1.0 (stdlib urllib)"

DEFAULT_REPO = "liyibo0410/yunshu-ai-portfolio"
DEFAULT_HOMEPAGE = "http://39.96.200.45:8070"
DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"

MAX_TOPICS = 20            # GitHub 硬上限
MAX_TOPIC_LEN = 50         # GitHub 硬上限（单个 topic 字符数）
MAX_DESCRIPTION_LEN = 350  # GitHub About 简介上限

# 默认 About 简介（≤350 字符，中文按 1 字符算）。
# 与 docs/github-repo-metadata.md「候选 A」一致；要改就文档 + 这里两处一起改。
DEFAULT_DESCRIPTION = (
    "云枢智能 CloudPivot · AI 电商运营中台：10 个 AI 能力模块（AI 客服 / 电商运营助手 / "
    "NL2SQL 问数 / RAG 知识库 / 合同审批 / 数据中台 / 素材中心 / 直播切片 / 销售考核 / 微调平台）"
    "合并成一套统一系统——微前端外壳 + 统一认证 + 端口注册表 + 跨模块真实调用，731 passed。"
    "Python 3.12 · FastAPI · LangGraph · Next.js。"
)

# 默认 topics（正好 20 个 = GitHub 上限，全部小写 + 连字符）。
# 与 docs/github-repo-metadata.md 的表格逐条对应；括号内是该 topic 在
# https://github.com/topics/<name> 上实测的仓库数（2026-10-15）。
DEFAULT_TOPICS = [
    "python",          # 963,941
    "fastapi",         # 109,159
    "llm",             # 156,943
    "rag",             # 56,186
    "ai-agent",        # 39,785
    "multi-agent",     # 19,653
    "langchain",       # 27,773
    "langgraph",       # 15,582
    "nl2sql",          # 407   —— 极精准但冷门：只用于精确命中，不指望 topic 页曝光
    "llmops",          # 3,573
    "lora",            # 6,587 —— 曾考虑 model-finetuning，实测全站只有 8 个仓库，故换掉
    "knowledge-base",  # 7,776
    "micro-frontend",  # 382
    "nextjs",          # 202,920
    "vue3",            # 20,053
    "duckdb",          # 6,131
    "milvus",          # 668
    "e-commerce",      # 8,684
    "docker",          # 233,690
    "portfolio",       # 90,105
]

# 明确禁止的 topics：无意义、引流式、或与本仓库定位不符。
# 这些不是「合法性问题」而是「策略问题」——脚本宁可报错也不让它们混进去。
BANNED_TOPICS = {
    "awesome": "空泛的「收藏夹」词，搜到的人不是来找可运行项目的，无曝光价值",
    "awesome-list": "同上，且会被理解为「资源清单」而非「一套可运行的系统」",
    "hacktoberfest": "季节性引流标签，面试官视角是噪声，且本仓库并不收外部 PR",
    "good-first-issue": "表示「欢迎新人练手」，与「工程作品集」定位相反",
    "help-wanted": "同上，暗示项目未完成 / 缺人手",
    "first-timers-only": "同上",
    "hackathon": "与项目定位不符",
    "opensource": "几乎无区分度，等于没打标签",
    "ai": "过宽，被海量仓库稀释（用 llm / ai-agent / rag 这类可检索词替代）",
}

TOPIC_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# HTTP 状态码 → 人话解释
HTTP_HINTS = {
    401: "Token 无效或已过期（也可能是拼写错误或权限范围不足）。请重新生成 Token，并确认环境变量名与 --token-env 一致。",
    403: "权限不足，或被 GitHub 限流（未认证 60 次/小时，认证 5000 次/小时）。若是权限问题：fine-grained Token 需要 Administration:write，经典 Token 需要 public_repo / repo 范围。",
    404: "仓库名拼错了，或者该 Token 看不到这个仓库（私有仓库 / 未被授权）。注意 owner/name 格式与大小写。",
    422: "请求体不合法：最常见是 topics 超过 20 个、含非法字符（只允许小写字母 / 数字 / 连字符）、单个 topic 超过 50 字符，或 description 超长。",
}


class MetadataError(Exception):
    """可预期的业务错误（参数 / 校验 / 网络）——由 main 统一转成人话并给退出码。"""


def eprint(*args):
    """写 stderr，并先把 stdout 刷出去——避免管道里 stdout / stderr 顺序错乱。"""
    sys.stdout.flush()
    print(*args, file=sys.stderr)


# ---------------------------------------------------------------- 工具函数


def mask_token(token: str) -> str:
    """把 Token 打码成 github_pat_11B4...izG4 形式。任何日志都只能打印这个结果。"""
    if not token:
        return "(未设置)"
    if len(token) <= 12:
        return token[:4] + "..." + token[-2:]
    return token[:14] + "..." + token[-4:]


def validate_description(desc: str) -> list:
    """返回问题列表（空列表 = 通过）。"""
    problems = []
    if desc is None:
        return ['description 不能为 None；要清空请传空字符串 ""']
    if len(desc) > MAX_DESCRIPTION_LEN:
        problems.append(
            "description 长度 %d 超过 GitHub 上限 %d（中文按 1 字符算）"
            % (len(desc), MAX_DESCRIPTION_LEN)
        )
    if desc and desc != desc.strip():
        problems.append("description 首尾有多余空白（GitHub 会原样保存，建议先 strip）")
    if "\n" in desc or "\r" in desc:
        problems.append("description 含换行；About 是单行字段，请改成空格分隔")
    return problems


def validate_topic(topic: str) -> list:
    problems = []
    if not topic:
        return ["存在空 topic"]
    if len(topic) > MAX_TOPIC_LEN:
        problems.append("topic %r 长度 %d 超过 %d" % (topic, len(topic), MAX_TOPIC_LEN))
    if topic != topic.lower():
        problems.append("topic %r 含大写字母，GitHub 只接受小写" % topic)
    if not TOPIC_RE.match(topic):
        problems.append(
            "topic %r 含非法字符或格式不对（只允许小写字母 / 数字 / 连字符，"
            "不能以连字符开头结尾，不能连续两个连字符）" % topic
        )
    return problems


def validate_topics(topics: list) -> list:
    """返回问题列表（空列表 = 通过）。"""
    problems = []
    if not topics:
        problems.append("topics 为空：GitHub 要求至少 1 个")
    if len(topics) > MAX_TOPICS:
        problems.append("topics 数量 %d 超过 GitHub 上限 %d" % (len(topics), MAX_TOPICS))
    for t in topics:
        problems.extend(validate_topic(t))
    dupes = sorted({t for t in topics if topics.count(t) > 1})
    if dupes:
        problems.append("topics 有重复项：%s" % ", ".join(dupes))
    for t in sorted({t for t in topics if t in BANNED_TOPICS}):
        problems.append("topic %r 在禁用清单里（%s）" % (t, BANNED_TOPICS[t]))
    return problems


def parse_topics(raw: str) -> list:
    """把 `a,b,c` 解析成列表：切分、去空白、去首尾连字符、小写化，然后校验。"""
    if raw is None:
        raise MetadataError("--topics 传了 None")
    items = [p.strip().lower() for p in raw.replace("，", ",").split(",")]
    items = [t.strip("-") for t in items if t]
    problems = validate_topics(items)
    if problems:
        raise MetadataError("--topics 校验未通过：\n  - " + "\n  - ".join(problems))
    return items


# ---------------------------------------------------------------- HTTP


def http_json(method: str, url: str, token: str = "", body=None,
              accept: str = ACCEPT_JSON, timeout: int = 30):
    """发一个 JSON 请求，返回 (status_code, payload)。

    HTTP 4xx / 5xx 不抛裸异常，而是把状态码与 GitHub 的 message 一起返回，
    由调用方映射成 HTTP_HINTS 里的人话；网络层错误抛 MetadataError。
    """
    data = None
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": API_VERSION,
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = JSON_CONTENT_TYPE

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except ValueError:
            payload = {"message": raw[:300]}
        return exc.code, payload
    except urllib.error.URLError as exc:
        raise MetadataError(
            "网络层失败，连不上 %s：%s\n"
            "  排查：代理 / TUN 是否对 api.github.com 做了 TLS 中间人；"
            "试 `curl.exe -sS -o NUL -w \"%%{http_code}\" https://api.github.com/rate_limit`。"
            % (API_ROOT, exc.reason)
        )
    except TimeoutError:
        raise MetadataError("请求超时（%d 秒）：%s" % (timeout, url))


def explain_status(status: int, payload) -> str:
    """把状态码 + GitHub 返回的 message 拼成人话（不回显任何请求头 / Token）。"""
    hint = HTTP_HINTS.get(status)
    message = ""
    if isinstance(payload, dict):
        message = str(payload.get("message") or "")
        errors = payload.get("errors")
        if errors:
            try:
                message += " | errors: " + json.dumps(errors, ensure_ascii=False)
            except (TypeError, ValueError):
                message += " | errors: " + repr(errors)
    line = "HTTP %s" % status
    if message:
        line += " · GitHub 说：%s" % message
    if hint:
        line += "\n  → " + hint
    elif status >= 500:
        line += "\n  → GitHub 侧 5xx，稍后重试；这不是参数问题。"
    return line


def api_url(repo: str, suffix: str = "") -> str:
    return "%s/repos/%s%s" % (API_ROOT, repo, suffix)


def normalize_repo(repo: str) -> str:
    """接受 owner/name、URL、带 .git 后缀等写法，统一成 owner/name。"""
    r = (repo or "").strip()
    r = re.sub(r"^https?://(www\.)?github\.com/", "", r, flags=re.I)
    r = r.strip().strip("/")
    if r.endswith(".git"):
        r = r[:-4]
    if not re.match(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$", r):
        raise MetadataError(
            "仓库名 %r 不是 owner/name 形式（例：liyibo0410/yunshu-ai-portfolio）" % repo
        )
    return r


# ---------------------------------------------------------------- 差异计算与展示


def desired_state(args) -> dict:
    """把命令行参数解析成「想要的状态」。"""
    desc = args.description if args.description is not None else DEFAULT_DESCRIPTION
    problems = validate_description(desc)
    if problems:
        raise MetadataError("description 校验未通过：\n  - " + "\n  - ".join(problems))

    if args.topics is not None:
        topics = parse_topics(args.topics)
    else:
        topics = list(DEFAULT_TOPICS)
        problems = validate_topics(topics)
        if problems:
            raise MetadataError(
                "脚本内置 DEFAULT_TOPICS 自己就不合法：\n  - " + "\n  - ".join(problems))

    homepage = args.homepage if args.homepage is not None else DEFAULT_HOMEPAGE
    return {"description": desc, "homepage": homepage, "topics": topics}


def diff_fields(current: dict, want: dict) -> list:
    """只列出真的会变的字段。current 为 None 表示读不到现状（网络 / 权限问题）。"""
    changes = []
    if current is None:
        for key in ("description", "homepage", "topics"):
            changes.append((key, "<无法读取>", want[key]))
        return changes

    cur_desc = current.get("description") or ""
    if cur_desc != want["description"]:
        changes.append(("description", cur_desc or "(空)", want["description"]))

    cur_home = current.get("homepage") or ""
    if cur_home != want["homepage"]:
        changes.append(("homepage", cur_home or "(空)", want["homepage"] or "(清空)"))

    cur_topics = list(current.get("topics") or [])
    if sorted(cur_topics) != sorted(want["topics"]):
        changes.append((
            "topics",
            "%d 个 %s" % (len(cur_topics), cur_topics) if cur_topics else "(空)",
            "%d 个 %s" % (len(want["topics"]), want["topics"]),
        ))
    elif cur_topics != want["topics"]:
        # 集合相同、顺序不同：GitHub 不算「变了」，但提示一下便于对齐文档
        changes.append(("topics(仅顺序)", str(cur_topics), str(want["topics"])))
    return changes


def render_dry_run(repo: str, current: dict, want: dict, changes: list,
                   token_present: bool) -> str:
    """dry-run 输出：现状 → 目标差异 → 将要发送的请求体。"""
    lines = []
    lines.append("=" * 72)
    lines.append("DRY-RUN（默认模式，不会发送任何写请求；要真发请加 --yes）")
    lines.append("=" * 72)
    lines.append("仓库        : %s" % repo)
    lines.append("Token       : %s"
                 % ("已提供（打码显示在上方）" if token_present else "(未提供，仅能未认证读取)"))
    lines.append("")
    lines.append("-- 现状（GET /repos/%s）--" % repo)
    if current is None:
        lines.append("  <读取失败，见上方错误>")
    else:
        lines.append("  description : %s" % (current.get("description") or "(空)"))
        lines.append("  homepage    : %s" % (current.get("homepage") or "(空)"))
        lines.append("  topics      : %s" % ((current.get("topics") or []) or "(空)"))
        lines.append("  stars / size / branch : %s / %s KB / %s"
                     % (current.get("stargazers_count"), current.get("size"),
                        current.get("default_branch")))
    lines.append("")
    lines.append("-- 差异（只会列出真的会变的字段）--")
    if not changes:
        lines.append("  （无差异：远端已经就是目标状态，不需要发送任何写请求）")
    else:
        for key, old, new in changes:
            lines.append("  * %s" % key)
            lines.append("      - 旧: %s" % old)
            lines.append("      + 新: %s" % new)
    lines.append("")
    lines.append("-- 将要发送的请求体 --")
    lines.append("  PATCH %s" % api_url(repo))
    lines.append("    Accept: %s" % ACCEPT_JSON)
    if any(c[0] in ("description", "homepage") for c in changes):
        lines.append("    body:")
        lines.append(json.dumps(
            {"description": want["description"], "homepage": want["homepage"]},
            ensure_ascii=False, indent=2).replace("\n", "\n    "))
    else:
        lines.append("    body: （description / homepage 无差异，跳过此请求）")
    lines.append("")
    lines.append("  PUT %s" % api_url(repo, "/topics"))
    lines.append("    Accept: %s   (必须带，否则 404 / 415)" % ACCEPT_JSON)
    lines.append("    body:")
    lines.append(json.dumps({"names": want["topics"]},
                            ensure_ascii=False, indent=2).replace("\n", "\n    "))
    lines.append("")
    lines.append("description 长度: %d / %d 字符" % (len(want["description"]), MAX_DESCRIPTION_LEN))
    lines.append("topics 数量    : %d / %d" % (len(want["topics"]), MAX_TOPICS))
    lines.append("")
    lines.append("注意：Social preview（社交预览图）**REST API 不支持**，只能在 "
                 "Settings → General → Social preview → Edit → Upload an image 手动上传。")
    lines.append("=" * 72)
    return "\n".join(lines)


# ---------------------------------------------------------------- 主流程


def fetch_repo(repo: str, token: str, timeout: int):
    """返回 (current_dict_or_None, error_text_or_None)。"""
    status, payload = http_json("GET", api_url(repo), token=token, timeout=timeout)
    if status == 200 and isinstance(payload, dict):
        return payload, None
    return None, explain_status(status, payload)


def apply_metadata(repo: str, want: dict, changes: list, token: str, timeout: int) -> int:
    changed_keys = {c[0] for c in changes}
    if "description" in changed_keys or "homepage" in changed_keys:
        body = {"description": want["description"], "homepage": want["homepage"]}
        print("--> PATCH %s" % api_url(repo))
        status, payload = http_json("PATCH", api_url(repo), token=token,
                                    body=body, timeout=timeout)
        if status != 200:
            eprint(explain_status(status, payload))
            return 2
        print("    ok，description / homepage 已写入")
    else:
        print("--> 跳过 PATCH（description / homepage 无差异）")

    if any(c[0].startswith("topics") for c in changes):
        print("--> PUT %s" % api_url(repo, "/topics"))
        status, payload = http_json("PUT", api_url(repo, "/topics"), token=token,
                                    body={"names": want["topics"]}, timeout=timeout)
        if status != 200:
            eprint(explain_status(status, payload))
            return 2
        print("    ok，topics 已写入")
    else:
        print("--> 跳过 PUT /topics（无差异）")
    return 0


def print_final_state(repo: str, token: str, timeout: int) -> int:
    """真跑完用一次 GET 回读并打印实际生效的最终状态。"""
    print("")
    print("-- 回读实际生效状态（GET /repos/%s）--" % repo)
    current, error = fetch_repo(repo, token, timeout)
    if error:
        eprint("  回读失败：" + error)
        return 2
    print("  description : %s" % (current.get("description") or "(空)"))
    print("  homepage    : %s" % (current.get("homepage") or "(空)"))
    print("  topics      : %d 个 %s" % (len(current.get("topics") or []),
                                       current.get("topics") or []))
    return 0


def cmd_self_test() -> int:
    """离线自检：不联网、不需要 Token。返回 0 = 全通过。"""
    failures = []

    def check(name, cond, extra=""):
        mark = "ok  " if cond else "FAIL"
        print("[%s] %s%s" % (mark, name, ("  -> " + extra) if (extra and not cond) else ""))
        if not cond:
            failures.append(name)

    print("== set_repo_metadata.py --self-test（离线，不联网，不需要 Token）==")
    print("")
    print("-- 1. 参数解析 --")
    parser = build_parser()
    a = parser.parse_args(["--repo", DEFAULT_REPO, "--yes",
                           "--token-env", "GH_META_TOKEN",
                           "--description", "x", "--topics", "a,b,c"])
    check("--repo/--yes/--token-env/--description/--topics 都能解析", a.repo == DEFAULT_REPO and a.yes)
    check("--token-env 可改名", a.token_env == "GH_META_TOKEN")
    a2 = parser.parse_args([])
    check("不带 --yes 时 yes=False（默认 dry-run）", a2.yes is False)
    check("不带 --repo 时有默认仓库", a2.repo == DEFAULT_REPO)
    a3 = parser.parse_args(["--homepage", ""])
    check('--homepage "" 解析为空串（= 清空）', a3.homepage == "")
    check("不带 --homepage 时为 None（= 用默认值）", parser.parse_args([]).homepage is None)
    check("不存在 --token 明文参数",
          all("--token" != act.option_strings[0] for act in parser._actions if act.option_strings))
    check("--self-test 可解析", parser.parse_args(["--self-test"]).self_test is True)

    print("")
    print("-- 2. topics 合法性与 20 上限 --")
    check("合法 topics 通过", validate_topics(["ai-agent", "nl2sql", "vue3", "nextjs"]) == [])
    check("内置 DEFAULT_TOPICS 合法且不超过 20 个",
          validate_topics(DEFAULT_TOPICS) == [] and len(DEFAULT_TOPICS) <= MAX_TOPICS,
          str(validate_topics(DEFAULT_TOPICS)))
    check("内置 DEFAULT_TOPICS 数量正好 = %d" % MAX_TOPICS, len(DEFAULT_TOPICS) == MAX_TOPICS,
          "实际 %d" % len(DEFAULT_TOPICS))
    p21 = validate_topics(DEFAULT_TOPICS + ["extra-one"])
    check("21 个 topics 被拒并提到上限 20",
          bool(p21) and any("上限 20" in x for x in p21), str(p21))
    check("大写被拒", bool(validate_topic("Awesome")))
    check("下划线被拒", bool(validate_topic("good_first_issue")))
    check("连续连字符被拒", bool(validate_topic("a--b")))
    check("首尾连字符被拒", bool(validate_topic("-rag-")) and bool(validate_topic("-x")))
    check("超 50 字符被拒", bool(validate_topic("a" * 51)))
    check("重复项被拒", any("重复" in x for x in validate_topics(["rag", "rag"])))
    check("禁用标签 hacktoberfest 被拒",
          any("禁用清单" in x for x in validate_topics(["rag", "hacktoberfest"])))
    check("禁用标签 awesome 被拒",
          any("禁用清单" in x for x in validate_topics(["awesome"])))
    check("HTTP_HINTS 覆盖 401/403/404/422",
          all(k in HTTP_HINTS for k in (401, 403, 404, 422)))

    print("")
    print("-- 3. --topics 命令行解析 --")
    check("a,b,c -> 3 项", parse_topics("a,b,c") == ["a", "b", "c"])
    check("中文逗号与空白也能切",
          parse_topics("RAG, ai-agent ，nl2sql") == ["rag", "ai-agent", "nl2sql"])
    check("大写自动小写化", parse_topics("RAG") == ["rag"])
    raised = False
    try:
        parse_topics(",".join("t%d" % i for i in range(21)))
    except MetadataError:
        raised = True
    check("21 项走 parse_topics 抛 MetadataError（不是裸异常）", raised)

    print("")
    print("-- 4. description 校验 --")
    check("内置 DEFAULT_DESCRIPTION 通过且 ≤350",
          validate_description(DEFAULT_DESCRIPTION) == []
          and len(DEFAULT_DESCRIPTION) <= MAX_DESCRIPTION_LEN,
          "len=%d %s" % (len(DEFAULT_DESCRIPTION), validate_description(DEFAULT_DESCRIPTION)))
    check("351 字符被拒", bool(validate_description("中" * (MAX_DESCRIPTION_LEN + 1))))
    check("含换行被拒", bool(validate_description("a\nb")))

    print("")
    print("-- 5. Token 打码（不会出现完整 Token）--")
    # 注意：这个假 Token 故意用字符串拼接写，避免文件里出现 `github_pat_` 开头的字面量
    # （否则任何「扫描仓库里是否混入真 Key」的正则都会误报这一行）。
    fake = "github_pat_" + "TESTONLY" * 3 + "NOTAREALTOKEN" + "izG4"
    masked = mask_token(fake)
    check("打码形如 <前 14 字符>...<后 4 字符>",
          masked.startswith("github_pat_TES") and masked.endswith("izG4") and "..." in masked,
          masked)
    check("打码结果不含完整 Token", fake not in masked and len(masked) < len(fake))
    check("空 Token 显示 (未设置)", mask_token("") == "(未设置)")

    print("")
    print("-- 6. dry-run 输出格式 --")
    want = {"description": DEFAULT_DESCRIPTION, "homepage": DEFAULT_HOMEPAGE,
            "topics": list(DEFAULT_TOPICS)}
    current = {"description": None, "homepage": None, "topics": [],
               "stargazers_count": 1, "size": 58589, "default_branch": "main"}
    changes = diff_fields(current, want)
    out = render_dry_run(DEFAULT_REPO, current, want, changes, token_present=False)
    for needle in ("DRY-RUN",
                   "PATCH https://api.github.com/repos/%s" % DEFAULT_REPO,
                   "PUT https://api.github.com/repos/%s/topics" % DEFAULT_REPO,
                   "application/vnd.github+json", '"names"', "description", "homepage",
                   "Social preview", "REST API 不支持"):
        check("dry-run 输出含 %r" % needle, needle in out)
    check("差异覆盖 3 个字段", {c[0] for c in changes} == {"description", "homepage", "topics"},
          str([c[0] for c in changes]))
    same = diff_fields({"description": DEFAULT_DESCRIPTION, "homepage": DEFAULT_HOMEPAGE,
                        "topics": list(DEFAULT_TOPICS)}, want)
    check("远端已一致时差异为空", same == [], str(same))
    check("未提供 Token 时 dry-run 明确标注", "未提供" in out)

    print("")
    print("-- 7. 仓库名规整 --")
    check("URL 形式能规整",
          normalize_repo("https://github.com/liyibo0410/yunshu-ai-portfolio.git") == DEFAULT_REPO)
    bad = False
    try:
        normalize_repo("just-a-name")
    except MetadataError:
        bad = True
    check("非法仓库名抛 MetadataError", bad)

    print("")
    print("-- 8. 错误码映射是人话（不是裸异常）--")
    for code in (401, 403, 404, 422):
        text = explain_status(code, {"message": "demo"})
        check("%d 有解释且带 GitHub 的 message" % code,
              ("HTTP %d" % code) in text and "demo" in text)

    print("")
    print("-- 9. 网络层错误不崩（离线模拟，不联网）--")
    real_urlopen = urllib.request.urlopen

    def _boom_urlopen(*a, **k):
        raise urllib.error.URLError("simulated network failure")

    urllib.request.urlopen = _boom_urlopen
    converted = False
    try:
        http_json("GET", API_ROOT + "/repos/x/y")
    except MetadataError as exc:
        converted = "网络层失败" in str(exc)
    except BaseException as exc:  # 裸 URLError / OSError 都算失败
        converted = "意外异常 %s" % type(exc).__name__
    finally:
        urllib.request.urlopen = real_urlopen
    check("http_json 把网络错误转成 MetadataError（不是裸 URLError）", converted is True,
          str(converted))

    global fetch_repo
    real_fetch = fetch_repo

    def _boom_fetch(repo, token, timeout):
        raise MetadataError("网络层失败，连不上 %s：simulated" % API_ROOT)

    fetch_repo = _boom_fetch
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = main(["--repo", DEFAULT_REPO, "--token-env", "__NO_SUCH_ENV__"])
    finally:
        fetch_repo = real_fetch
    check("main 捕获网络错误并返回 2（不是 traceback 崩掉）", rc == 2, "rc=%r" % (rc,))
    check("中止时明确说了「未发送任何写请求」", "未发送任何写请求" in buf.getvalue())

    print("")
    if failures:
        print("自检失败 %d 项：%s" % (len(failures), ", ".join(failures)))
        return 1
    print("自检全部通过（不联网，未使用任何 Token）。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="set_repo_metadata.py",
        description="写入 GitHub 仓库门面元数据（About description / homepage / topics）。默认 dry-run。",
        epilog="Token 只从环境变量读；本脚本不接收 --token 明文参数，也不会把 Token 写入任何文件。",
    )
    p.add_argument("--repo", default=DEFAULT_REPO,
                   help="owner/name 或仓库 URL（默认 %s）" % DEFAULT_REPO)
    p.add_argument("--yes", action="store_true",
                   help="真的发送写请求（PATCH / PUT）。不传就是 dry-run。")
    p.add_argument("--token-env", default=DEFAULT_TOKEN_ENV,
                   help="从哪个环境变量读 Token（默认 %s）" % DEFAULT_TOKEN_ENV)
    p.add_argument("--description", default=None,
                   help="覆盖 About 简介（默认用脚本内置的 DEFAULT_DESCRIPTION）")
    p.add_argument("--topics", default=None,
                   help="逗号分隔覆盖 topics，例如 ai-agent,rag,langgraph（默认用内置 20 个）")
    p.add_argument("--homepage", default=None,
                   help='Website 链接；传空串 "" 表示清空（默认 %s）' % DEFAULT_HOMEPAGE)
    p.add_argument("--timeout", type=int, default=30, help="单请求超时秒数（默认 30）")
    p.add_argument("--self-test", action="store_true",
                   help="离线自检：参数解析 / topics 合法性 / dry-run 输出格式；不联网、不需要 Token")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.self_test:
        return cmd_self_test()

    try:
        repo = normalize_repo(args.repo)
    except MetadataError as exc:
        eprint("参数错误：" + str(exc))
        return 1

    token = os.environ.get(args.token_env, "") or ""
    print("仓库    : %s" % repo)
    print("Token   : %s  (环境变量 %s)" % (mask_token(token) if token else "(未设置)", args.token_env))
    print("模式    : %s" % ("APPLY（真的写）" if args.yes else "DRY-RUN（默认，只打印差异）"))

    try:
        want = desired_state(args)
    except MetadataError as exc:
        eprint("参数错误：" + str(exc))
        return 1

    # 1) 先读现状（未认证也能读公开仓库）
    #    网络层错误在 run() 里统一转成人话，绝不把 traceback 甩给用户
    try:
        return run(args, repo, token, want)
    except MetadataError as exc:
        eprint("网络层错误：" + str(exc))
        eprint("未发送任何写请求（读不到现状就不写）。")
        return 2


def run(args, repo: str, token: str, want: dict) -> int:
    """读现状 → dry-run 或真写 → 回读。任何网络层失败都抛 MetadataError 由 main 兜住。"""
    if not token:
        print("提示：未提供 Token，本次为未认证读取（公开仓库可读，速率上限 60 次/小时）。")
    current, error = fetch_repo(repo, token, args.timeout)
    if error:
        eprint("读现状失败：" + error)
        if args.yes:
            eprint("已中止：读不到现状就不写，避免盲写。")
            return 2
        # dry-run 下读不到也要把意图打出来，方便排查
        eprint("以下为「读不到现状」时推演的将发请求体：")
        print(json.dumps({"PATCH": {"description": want["description"],
                                    "homepage": want["homepage"]},
                          "PUT /topics": {"names": want["topics"]}},
                         ensure_ascii=False, indent=2))
        return 2

    changes = diff_fields(current, want)
    print(render_dry_run(repo, current, want, changes, bool(token)))

    if not args.yes:
        print("")
        print("以上为 dry-run。确认无误后加 --yes 真发请求（请在主控授权后再跑）。")
        return 0

    # 2) 真写
    if not token:
        eprint("写请求缺少 Token：GitHub 会以 401 拒绝（未认证）。")
        eprint("  → " + HTTP_HINTS[401])
        eprint("  → PowerShell: $env:%s = 'github_pat_...' 然后重跑（不要写进任何文件）"
               % args.token_env)
        return 3

    code = apply_metadata(repo, want, changes, token, args.timeout)
    if code != 0:
        eprint("写操作失败，已停止。")
        return code
    return print_final_state(repo, token, args.timeout)


if __name__ == "__main__":
    sys.exit(main())