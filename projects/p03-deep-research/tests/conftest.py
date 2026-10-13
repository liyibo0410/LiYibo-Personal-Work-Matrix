import sys
from pathlib import Path

# 让测试可以 import tools.sql_guard（项目根加入 sys.path）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
