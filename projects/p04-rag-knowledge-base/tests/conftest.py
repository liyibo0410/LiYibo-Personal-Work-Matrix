# tests/conftest.py

"""
pytest 全局配置。
确保 .env 在任何模块 import 前被加载，避免 config 模块读到空值。
"""

import os
import sys
from pathlib import Path

# 步骤1：确保项目根目录在 sys.path 最前面
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 步骤2：在 config 模块被 import 前，先加载 .env
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=True)
