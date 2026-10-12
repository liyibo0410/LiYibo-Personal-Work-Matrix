# -*- coding: utf-8 -*-
"""零依赖 .env 文件加载器

为什么不用 python-dotenv：本项目铁律「零第三方依赖」，客户是内网企业，
不希望为了跑一个工具先装一堆东西。

职责：
  1. 从指定目录向上最多找 3 级父目录，碰到 .env 就加载
  2. 只解析 KEY=VALUE，忽略 # 注释与空行，容忍值两端的引号
  3. 【不覆盖】已存在的真实环境变量（os.environ 优先，避免污染部署环境）
  4. 在 LLM 相关判断之前调用一次即可（server.boot() 里调用）

设计取舍：
  - 不支持多行值、变量展开（$VAR）、export 前缀 —— 本项目的 .env 用不到这些
  - 找到的第一个 .env 即停止（不会合并多个 .env 文件）
"""
from __future__ import annotations

import os
import re


_KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def _strip_quotes(val: str) -> str:
    """去掉值两端的引号（单引号/双引号成对才算）。"""
    if len(val) >= 2:
        if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
            return val[1:-1]
    return val


def _parse_line(line: str):
    """解析单行，返回 (key, value) 或 None。"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = _KV_RE.match(line)
    if not m:
        return None
    return m.group(1), _strip_quotes(m.group(2))


def find_dotenv(start_dir: str, max_levels: int = 3) -> str | None:
    """从 start_dir 向上找 .env，最多 max_levels 级，返回第一个找到的路径。"""
    d = os.path.abspath(start_dir)
    for _ in range(max_levels + 1):
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def load_dotenv(start_dir: str | None = None, path: str | None = None) -> dict[str, str]:
    """加载 .env 文件到 os.environ。

    参数：
      start_dir —— 从哪个目录开始向上找（默认 os.getcwd()）
      path      —— 直接指定 .env 路径（优先级高于 start_dir 搜索）

    返回实际加载的 {key: value} 字典（只含本次新设的，不含已存在的）。

    关键约束：已存在的环境变量不被覆盖 —— 这是为了避免污染部署环境里
    由运维 / Docker 注入的真实值。
    """
    env_path = path or find_dotenv(start_dir or os.getcwd())
    if not env_path or not os.path.isfile(env_path):
        return {}

    loaded: dict[str, str] = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_line(line)
            if parsed is None:
                continue
            key, value = parsed
            if key in os.environ:
                continue
            os.environ[key] = value
            loaded[key] = value
    return loaded


# ------------------------------------------------------------------ LLM 配置映射
def llm_credentials() -> tuple[str, str, str]:
    """按「主通道优先、备用通道兜底」挑出一组可用凭证。

    .env 里有两套阿里云百炼凭证（两套体系互相隔离，Key 与 Base URL 必须配对）：
      LLM_BASE_URL / LLM_API_KEY             —— 按量付费主通道（全模型、无有效期）
      LLM_BASE_URL_FALLBACK / LLM_API_KEY_FALLBACK —— Token Plan 备用通道（按月清零）

    主通道没填 Key 时自动退到备用通道，避免「配了 Key 却因为主通道空着而用不上」。

    返回 (base_url, api_key, source)，source ∈ {"primary", "fallback", ""}。
    """
    url, key = os.environ.get("LLM_BASE_URL", ""), os.environ.get("LLM_API_KEY", "")
    if url and key:
        return url, key, "primary"
    url2 = os.environ.get("LLM_BASE_URL_FALLBACK", "")
    key2 = os.environ.get("LLM_API_KEY_FALLBACK", "")
    if url2 and key2:
        return url2, key2, "fallback"
    return "", "", ""


def apply_llm_config(cfg) -> dict:
    """把 .env 的凭证映射进本项目的 llm 配置段（缺什么补什么，不覆盖显式配置）。

    为什么必须有这一步：load_dotenv() 只把变量塞进 os.environ，但本项目读的是
    config/app.json 的 llm.base_url 与 llm.api_key_env。两者不通的话，
    「用户在 .env 里配好了 Key，应用却永远走规则模式」—— 配置通路断在中间。

    规则（保守，绝不覆盖用户显式配置）：
      - base_url 为空才填，填了就不动
      - api_key_env 指向的环境变量为空才填
      - 不动 llm.enabled（是否启用由用户显式决定，保持任务卡要求的默认关闭语义）
    """
    url, key, source = llm_credentials()
    if not url or not key:
        return {"applied": False, "reason": ".env 中无可用凭证（主/备通道均未配置）"}

    llm = (cfg.data or {}).setdefault("llm", {})
    changed = []
    if not llm.get("base_url"):
        llm["base_url"] = url
        changed.append("base_url")
    key_env = llm.get("api_key_env") or "OPENAI_API_KEY"
    llm.setdefault("api_key_env", key_env)
    if not os.environ.get(key_env):
        os.environ[key_env] = key
        changed.append(key_env)
    return {"applied": True, "source": source, "changed": changed,
            "base_url": url, "model": llm.get("model", "")}
