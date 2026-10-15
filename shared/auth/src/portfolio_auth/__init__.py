# -*- coding: utf-8 -*-
"""portfolio_auth —— 李奕波个人作品矩阵统一平台共享鉴权（HS256 令牌签发/校验）。"""
from .token import (
    ALG,
    AuthError,
    issue_token,
    parse_bearer,
    require_role,
    verify_token,
)

__all__ = ["ALG", "AuthError", "issue_token", "verify_token", "require_role", "parse_bearer"]
__version__ = "1.0.0"
