# -*- coding: utf-8 -*-
"""云枢智能统一平台 · 共享鉴权（shared/auth）

纯标准库实现的 HS256 令牌签发与校验（不引第三方 JWT 库），供各模块 import 复用，
落实「四统一」里的**认证统一**：shell 登录一次签发令牌，各模块只校验不自己实现登录。

设计：
  * 令牌 = base64url(header).base64url(payload).base64url(HMAC-SHA256 签名)
    —— 与标准 JWT 结构兼容，可被任意 JWT 工具解析；
  * 密钥从环境变量 ``CP_AUTH_SECRET`` 读取，缺省用一个仅本地演示的弱密钥并告警；
  * payload 带 ``sub``(用户) / ``roles``(角色列表) / ``exp``(过期) / ``iat``(签发)；
  * 校验失败一律抛 ``AuthError``，不返回半可信结构。

红线：真实部署必须设置 ``CP_AUTH_SECRET`` 强密钥，禁止把弱默认值带上生产。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

ALG = "HS256"
_DEFAULT_TTL = 8 * 3600           # 8 小时
_WEAK_SECRET = "cloudpivot-local-demo-secret-do-not-use-in-prod"


class AuthError(Exception):
    """令牌签发/校验相关的统一异常。"""


def _secret() -> bytes:
    sec = os.environ.get("CP_AUTH_SECRET", "").strip()
    if not sec:
        # 不静默：缺密钥时用弱默认值并在 stderr 告警（生产必须显式配置）
        import sys
        sys.stderr.write("[shared.auth] 警告：未设置 CP_AUTH_SECRET，正在使用本地演示弱密钥，"
                         "禁止用于生产环境。\n")
        sec = _WEAK_SECRET
    return sec.encode("utf-8")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(signing_input: str, secret: bytes) -> str:
    sig = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return _b64e(sig)


def issue_token(subject: str, roles: list[str] | None = None, *,
                ttl: int = _DEFAULT_TTL, extra: dict | None = None) -> str:
    """签发令牌。

    :param subject: 用户标识（用户名 / 用户 id）
    :param roles: 角色列表，如 ["owner"] / ["legal"] / ["sales"]
    :param ttl: 有效期秒数
    :param extra: 追加到 payload 的非敏感声明
    """
    now = int(time.time())
    payload = {
        "sub": str(subject),
        "roles": list(roles or []),
        "iat": now,
        "exp": now + int(ttl),
    }
    if extra:
        payload.update(extra)
    header = {"alg": ALG, "typ": "JWT"}
    h = _b64e(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    p = _b64e(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = "%s.%s" % (h, p)
    return "%s.%s" % (signing_input, _sign(signing_input, _secret()))


def verify_token(token: str) -> dict:
    """校验令牌并返回 payload。签名不符 / 过期 / 结构非法一律抛 AuthError。"""
    if not token or not isinstance(token, str):
        raise AuthError("令牌为空")
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("令牌结构非法")
    signing_input = "%s.%s" % (parts[0], parts[1])
    expected = _sign(signing_input, _secret())
    if not hmac.compare_digest(expected, parts[2]):
        raise AuthError("签名校验失败")
    try:
        header = json.loads(_b64d(parts[0]))
        payload = json.loads(_b64d(parts[1]))
    except (ValueError, TypeError) as exc:
        raise AuthError("令牌解析失败：%s" % exc)
    if header.get("alg") != ALG:
        raise AuthError("不支持的签名算法：%s" % header.get("alg"))
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise AuthError("令牌已过期")
    return payload


def require_role(token: str, role: str) -> dict:
    """校验令牌且要求具备某角色，返回 payload；否则抛 AuthError。"""
    payload = verify_token(token)
    roles = payload.get("roles") or []
    if role not in roles and "owner" not in roles and "admin" not in roles:
        raise AuthError("角色不足：需要 %s，实际 %s" % (role, roles))
    return payload


def parse_bearer(authorization_header: str | None) -> str:
    """从 ``Authorization: Bearer <token>`` 头里取出令牌。"""
    if not authorization_header:
        return ""
    h = authorization_header.strip()
    if h.lower().startswith("bearer "):
        return h[7:].strip()
    return h


if __name__ == "__main__":
    # 自检：签发 → 校验 → 篡改检测 → 角色校验
    os.environ.setdefault("CP_AUTH_SECRET", "self-test-secret")
    tok = issue_token("李奕波", ["legal", "sales"], ttl=60)
    print("token:", tok[:48], "...")
    pl = verify_token(tok)
    print("payload:", pl)
    assert pl["sub"] == "李奕波" and "legal" in pl["roles"]
    # 篡改一个字符应校验失败
    bad = tok[:-2] + ("AA" if not tok.endswith("AA") else "BB")
    try:
        verify_token(bad)
        print("FAIL: 篡改未被发现")
    except AuthError as e:
        print("篡改检测 OK:", e)
    require_role(tok, "legal")
    print("角色校验 OK")
