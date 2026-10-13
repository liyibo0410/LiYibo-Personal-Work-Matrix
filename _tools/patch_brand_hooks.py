# -*- coding: utf-8 -*-
"""把 P06/P08/P09/P10 侧栏里写死的公司名改成绑定 brand.json。

不改这些页面就不会跟着「品牌定制」变 —— 用户换公司名后只有外壳变，模块仍写死。
幂等：已经打过的跳过。
"""
import re
import sys
from pathlib import Path

ROOT = Path(r"D:/software/PycharmProjects/面试项目/projects")

# (文件, [(旧片段, 新片段), ...])
RULES = [
    ("p06-data-platform/web/index.html", [
        ('<title>P06 数据中台 - CloudPivot</title>',
         '<title data-cp-brand-title="P06 数据中台 · {name_en}">P06 数据中台 - CloudPivot</title>'),
        ("<h1>CloudPivot</h1>",
         '<h1 data-cp-brand="company">云枢智能</h1>'),
    ]),
    ("p08-live-clip/web/index.html", [
        ('<title>P08 直播切片系统 - 云枢智能</title>',
         '<title data-cp-brand-title="P08 直播切片 · {company}">P08 直播切片系统 - 云枢智能</title>'),
        ('<div class="subtitle">云枢智能 CloudPivot</div>',
         '<div class="subtitle"><span data-cp-brand="company">云枢智能</span> '
         '<span data-cp-brand="name_en">CloudPivot</span></div>'),
    ]),
    ("p09-ai-sales-assessment/web/index.html", [
        ('<title>P09 AI 销售考核 - 云枢智能</title>',
         '<title data-cp-brand-title="P09 AI 销售考核 · {company}">P09 AI 销售考核 - 云枢智能</title>'),
        ("<h1>云枢智能</h1>",
         '<h1 data-cp-brand="company">云枢智能</h1>'),
    ]),
    ("p10-model-finetune/web/index.html", [
        ('<title>P10 模型微调平台 - 云枢智能</title>',
         '<title data-cp-brand-title="P10 模型微调平台 · {company}">P10 模型微调平台 - 云枢智能</title>'),
        ("<span>云枢智能 AI 平台</span>",
         '<span><span data-cp-brand="company">云枢智能</span> AI 平台</span>'),
    ]),
]

report = []
bad = []
for rel, pairs in RULES:
    path = ROOT / rel
    if not path.is_file():
        bad.append("%s 不存在" % rel)
        continue
    s = path.read_text(encoding="utf-8")
    before = s

    for old, new in pairs:
        if old in s:
            s = s.replace(old, new, 1)
        elif new not in s:
            bad.append("%s 未找到片段：%s" % (rel, old[:48]))

    # 让 ui-kit.js 启动时同源拉取 brand.json（属性缺省则只吃默认值）
    s = re.sub(r'(<body[^>]*data-cp-module="p\d+"(?![^>]*data-cp-brand-src)[^>]*)>',
               r'\1 data-cp-brand-src="/shared/config/brand.json">', s, count=1)

    if s != before:
        path.write_text(s, encoding="utf-8")
        report.append("%s 已更新" % rel)
    else:
        report.append("%s 无需改动" % rel)

print("\n".join(report))
for p, _ in RULES:
    s = (ROOT / p).read_text(encoding="utf-8")
    if "data-cp-brand-src" not in s:
        bad.append("%s 缺 data-cp-brand-src" % p)
print("\n".join(bad) if bad else "校验通过：4 个模块已绑定品牌真源")
sys.exit(1 if bad else 0)
