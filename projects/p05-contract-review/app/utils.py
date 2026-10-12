"""
公共工具函数模块
"""
import urllib.request


def build_opener():
    """
    构建一个禁用代理的 URL opener。
    避免宿主环境的 http_proxy 把内网/本机请求劫持到代理端口。
    """
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))
