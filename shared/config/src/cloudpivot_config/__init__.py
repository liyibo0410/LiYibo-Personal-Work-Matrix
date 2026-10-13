# -*- coding: utf-8 -*-
"""cloudpivot_config —— 云枢智能统一平台共享配置。

对外只暴露服务注册表（SERVICE_REGISTRY）相关 API。
"""
from .registry import (
    ServiceNotFound,
    api_url,
    by_layer,
    get,
    host,
    ids,
    port,
    registry,
    route_path,
    service_url,
    services,
)

__all__ = [
    "ServiceNotFound",
    "api_url",
    "by_layer",
    "get",
    "host",
    "ids",
    "port",
    "registry",
    "route_path",
    "service_url",
    "services",
]

__version__ = "1.0.0"
