# -*- coding: utf-8 -*-
"""给 P05 挂上平台设计系统：tokens.css + ui-kit.js + data-cp-module，
并把防闪内联脚本的主题来源从「只认 cr-theme」改为「URL 参数 > cp_theme > cr-theme」。
幂等：已经打过的文件跳过。"""
import re
import sys
from pathlib import Path

UI = Path(r"D:/software/PycharmProjects/面试项目/projects/p05-contract-review/ui")
PAGES = ["index.html", "workbench.html", "rules.html", "twin.html",
         "login.html", "mock.html", "denied.html"]

OLD_THEME = """    var t = localStorage.getItem('cr-theme');
    if (t !== 'light' && t !== 'dark') t = 'dark';"""
NEW_THEME = """    var t = /[?&]cp-theme=(light|dark)/.exec(location.search);
    t = t ? t[1] : (localStorage.getItem('cp_theme') || localStorage.getItem('cr-theme'));
    if (t !== 'light' && t !== 'dark') t = 'dark';"""

report = []
for name in PAGES:
    p = UI / name
    s = p.read_text(encoding="utf-8")
    before = s

    # 1) 设计令牌：放在 app.css 之前，让 app.css 里的 var(--cp-*) 有定义
    if "/shared/ui-kit/tokens.css" not in s:
        s = s.replace('<link rel="stylesheet" href="/assets/app.css">',
                      '<link rel="stylesheet" href="/shared/ui-kit/tokens.css">\n'
                      '<link rel="stylesheet" href="/assets/app.css">', 1)

    # 2) 运行时桥（主题 + 品牌 + 与外壳的 postMessage 契约）
    if "/shared/ui-kit/ui-kit.js" not in s:
        s = s.replace('<script src="/assets/app.js"></script>',
                      '<script src="/shared/ui-kit/ui-kit.js"></script>\n'
                      '<script src="/assets/app.js"></script>', 1)

    # 3) 主题初值：优先吃外壳传来的 ?cp-theme=
    if OLD_THEME in s:
        s = s.replace(OLD_THEME, NEW_THEME, 1)

    # 4) 声明为平台模块，ui-kit.js 据此自动建桥
    s = re.sub(r'<body(?![^>]*data-cp-module)([^>]*)>',
               r'<body data-cp-module="p05"\1>', s, count=1)

    if s != before:
        p.write_text(s, encoding="utf-8")
        report.append("%s: 已更新" % name)
    else:
        report.append("%s: 无需改动" % name)

print("\n".join(report))

# 校验：每页都要有 4 个挂载点
bad = []
for name in PAGES:
    s = (UI / name).read_text(encoding="utf-8")
    for needle in ("tokens.css", "ui-kit.js", 'data-cp-module="p05"', "cp-theme="):
        if needle not in s:
            bad.append("%s 缺 %s" % (name, needle))
print("\n".join(bad) if bad else "校验通过：7 个页面全部挂载完成")
sys.exit(1 if bad else 0)
