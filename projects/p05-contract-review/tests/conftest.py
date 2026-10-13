# -*- coding: utf-8 -*-
"""P05 合同审批 —— pytest 公共夹具。

被测对象是「零第三方依赖」的确定性风险审查引擎（app/review.py）、
文档解析器（app/parsers.py）、配置加载（app/config.py）与 SQLite 持久层
（app/store.py）。全部只用标准库，因此测试无需任何外部服务。

隔离原则：
  * Config 指向真实项目根（读 config/rules、config/clause_types.json）——
    这些是只读配置，测试不写回；
  * 需要落库的用例一律用 tmp_path 下的临时 db，绝不碰 data/review.db；
  * review._CACHE 是模块级配置缓存，autouse 夹具在每个用例后清理，避免串味。
"""
from __future__ import annotations

import os
import sys

import pytest

# 让 `from app import ...` 可用（pytest pythonpath=["."] 已覆盖，这里再兜底一次）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import config as config_mod          # noqa: E402
from app import review as review_mod          # noqa: E402


@pytest.fixture(scope="session")
def project_root() -> str:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def samples_dir(project_root) -> str:
    return os.path.join(project_root, "samples")


@pytest.fixture(scope="session")
def cfg(project_root):
    """真实项目配置（只读用途：加载规则库/条款类型/阈值）。"""
    return config_mod.Config(project_root)


@pytest.fixture
def clause_types(project_root):
    return review_mod.load_clause_types(project_root)


@pytest.fixture(autouse=True)
def _clear_review_cache():
    """review._CACHE 缓存配置对象；每个用例前后清空，保证互不干扰。"""
    review_mod._CACHE.clear()
    yield
    review_mod._CACHE.clear()


def make_paras(texts, start_page=1):
    """把若干段文本组装成解析层的「段落树」结构。

    段落字段与 parsers 输出一致：text/page/index/char_start/char_end/is_heading。
    字符偏移按「\\n 连接」累加，与 parse_document 的 text 拼接方式对齐，
    使 run_rules 命中坐标可映射回全文。
    """
    paras = []
    offset = 0
    for i, t in enumerate(texts):
        paras.append({
            "text": t,
            "page": start_page,
            "index": i,
            "char_start": offset,
            "char_end": offset + len(t),
            "is_heading": False,
        })
        offset += len(t) + 1  # +1 对应连接用的 "\n"
    full = "\n".join(texts)
    return paras, full
