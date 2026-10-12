"""
供应商 API 客户端公共工具：封装 Jimeng/DashScope 等供应商的通用请求/轮询/错误处理逻辑。
避免 image_generation.py 和 video_generation.py 之间的代码重复。
"""
from typing import Any

import httpx

from app.core.config import Settings


def post_jimeng_json(
    *,
    api_key: str,
    base_url: str | None,
    action: str,
    payload: dict[str, Any],
    timeout: int,
    error_class: type[Exception],
    not_configured_class: type[Exception],
) -> dict[str, Any]:
    """
    发送 Jimeng API JSON 请求的通用实现。

    :param api_key: API 密钥（access_key:secret_key 格式）
    :param base_url: API 基础地址
    :param action: API Action 名称
    :param payload: 请求体
    :param timeout: 超时秒数
    :param error_class: 通用错误异常类
    :param not_configured_class: 未配置错误异常类
    :return: API 响应数据
    """
    from app.services.auth import parse_access_key_pair, VolcengineCredentialsError
    from app.services.llm import signed_json_headers
    import json

    try:
        access_key, secret_key = parse_access_key_pair(api_key)
    except VolcengineCredentialsError as exc:
        raise not_configured_class(str(exc)) from exc

    url = base_url or "https://visual.volcengineapi.com"
    query = {"Action": action, "Version": "2022-08-31"}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = signed_json_headers(
        access_key=access_key,
        secret_key=secret_key,
        method="POST",
        url=url,
        query=query,
        body=body,
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, params=query, content=body, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise error_class(_dashscope_error_detail(exc.response)) from exc
    except httpx.HTTPError as exc:
        raise error_class(f"Jimeng request failed: {exc}") from exc

    code = data.get("code") or data.get("Code")
    if code not in {None, 0, 10000, "0", "10000"}:
        raise error_class(str(data)[:500])
    return data


def extract_jimeng_task_id(data: dict[str, Any]) -> str:
    """从 Jimeng 响应中提取任务 ID。"""
    for container in (data.get("data"), data.get("Result"), data.get("output"), data):
        if isinstance(container, dict) and isinstance(container.get("task_id"), str):
            return container["task_id"]
    return ""


def jimeng_status(data: dict[str, Any]) -> str:
    """从 Jimeng 响应中提取任务状态。"""
    container = data.get("data")
    if isinstance(container, dict) and isinstance(container.get("status"), str):
        return container["status"].lower()
    if isinstance(data.get("status"), str):
        return data["status"].lower()
    return ""


def extract_jimeng_url(data: dict[str, Any], url_keys: tuple[str, ...], list_keys: tuple[str, ...]) -> str:
    """
    从 Jimeng 响应中提取 URL。

    :param data: API 响应数据
    :param url_keys: 单个 URL 的键名列表，如 ("image_url", "url") 或 ("video_url", "url")
    :param list_keys: URL 列表的键名列表，如 ("image_urls", "urls") 或 ("video_urls", "urls")
    :return: 提取到的 URL 或空字符串
    """
    containers = [data.get("data"), data.get("Result"), data.get("output"), data]
    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in url_keys:
            value = container.get(key)
            if isinstance(value, str) and value:
                return value
        for key in list_keys:
            value = container.get(key)
            if isinstance(value, list) and value and isinstance(value[0], str):
                return value[0]
    return ""


def _dashscope_error_detail(response: httpx.Response) -> str:
    """从 HTTP 响应中提取错误详情。"""
    try:
        data = response.json()
        for key in ("Message", "message", "msg"):
            if data.get(key):
                return str(data[key])[:500]
    except Exception:
        pass
    return f"HTTP {response.status_code}: {response.text[:200]}"
