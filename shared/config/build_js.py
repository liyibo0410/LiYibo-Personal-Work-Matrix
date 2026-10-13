# -*- coding: utf-8 -*-
"""从 services.json（唯一真源）生成前端镜像 services.js。

前端（shell / 各模块页面）需要读端口时，引入生成的 services.js，
而不是各自硬编码。改端口只改 services.json，然后重跑本脚本。

    python shared/config/build_js.py
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "services.json")
_OUT = os.path.join(_HERE, "services.js")


def main() -> None:
    with open(_SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 只导出前端需要的字段，避免把注释等冗余带进产物
    gateway = data.get("gateway", {})
    payload = {
        "version": data.get("version"),
        "host": data.get("host"),
        # 网关端口：前端取品牌配置时的兜底来源（同源 brand.json 拿不到才用它）
        "gateway": {"web_port": gateway.get("web_port")},
        "layers": data.get("layers", {}),
        "services": data.get("services", {}),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)

    js = (
        "/* 自动生成，请勿手改 —— 真源是 shared/config/services.json，"
        "改端口后重跑 build_js.py。 */\n"
        "window.CP_REGISTRY = %s;\n" % body
    )
    with open(_OUT, "w", encoding="utf-8") as f:
        f.write(js)
    print("已生成 %s（%d 个服务）" % (_OUT, len(payload["services"])))


if __name__ == "__main__":
    main()
