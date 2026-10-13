"""P03 的模型入口。

凭据解析顺序（先命中先用，成对取值避免「A 家的 Key 打 B 家的端点」）：
  1) 本模块 .env 的 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL
  2) 仓库根 .env 的 LLM_API_KEY / LLM_BASE_URL
  3) 仓库根 .env 的 LLM_API_KEY_FALLBACK / LLM_BASE_URL_FALLBACK —— Token Plan（Essential 套餐，
     配额稳定，2026-10-22 00:00 到期）
  4) 仓库根 .env 的 CODING_API_KEY / CODING_BASE_URL_ALT —— 百炼免费额度端点

占位值（含 mock / your / xxx / change 或为空）视为不可用：以前拿着占位 Key 去打真实
端点，401 被上层吞掉，前端就永远停在「思考中…」。现在导入阶段就记下明确原因，由
agent/main_agent.py 在跑任务前以 error 事件回传，用户看得见该改哪里。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()  # 本模块 .env（已在 cwd 或其上层）

_PLACEHOLDER_HINTS = ("mock", "your-", "your_", "xxx", "changeme", "change-me", "todo", "placeholder")

# 仓库根的标记键：只有根 .env 同时定义了主/备两套百炼凭证，用它当定位锚点。
_ROOT_ENV_MARKER = "LLM_API_KEY_FALLBACK"


def _find_repo_root() -> Path:
    """向上找到含百炼凭证的仓库根 .env 所在目录。

    别再用硬编码层数：上一版写 parents[2] 并注释「即面试项目根」，实际指到 projects/，
    根 .env 读不到 → 明明配了两套 Key 却报「未找到可用的模型凭据」。
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        env_file = parent / ".env"
        try:
            if env_file.is_file() and _ROOT_ENV_MARKER in env_file.read_text(encoding="utf-8"):
                return parent
        except OSError:
            continue
    return here.parents[3]


REPO_ROOT = _find_repo_root()


def _usable(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip().lower()
    if len(v) < 8:
        return False
    return not any(h in v for h in _PLACEHOLDER_HINTS)


def _read_root_env() -> dict:
    """只读根 .env，不注入 os.environ —— 避免覆盖各模块自己的配置。"""
    out: dict[str, str] = {}
    path = REPO_ROOT / ".env"
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


_CANDIDATES = (
    ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "LLM_QWEN_PLUS"),
)


def resolve_model_config():
    """返回 (api_key, base_url, model_name, error)。error 为空表示可用。"""
    root = _read_root_env()
    fast_model = root.get("LLM_MODEL_FAST") or root.get("LLM_MODEL")
    pairs = [(os.getenv(a), os.getenv(b), os.getenv(m)) for a, b, m in _CANDIDATES]
    pairs.append((root.get("LLM_API_KEY"), root.get("LLM_BASE_URL"), fast_model))
    pairs.append((root.get("LLM_API_KEY_FALLBACK"), root.get("LLM_BASE_URL_FALLBACK"), fast_model))
    # 免费额度端点：按 model 维度发放免费额度，且官方口径限定编程工具使用 —— 只作兜底，
    # 一旦 Token Plan 到期（2026-10-22）无需改代码即可接管。
    pairs.append((root.get("CODING_API_KEY"), root.get("CODING_BASE_URL_ALT"), fast_model))
    for key, base, name in pairs:
        if _usable(key) and _usable(base) and name:
            return key.strip(), base.strip(), name.strip(), ""
    return None, None, None, (
        "未找到可用的模型凭据。请在仓库根目录 .env 里填写 LLM_API_KEY + LLM_BASE_URL"
        "（或 LLM_API_KEY_FALLBACK + LLM_BASE_URL_FALLBACK）；"
        "当前各处的 Key 仍是占位值或已失效。"
    )


api_key, base_url, model_name, MODEL_CONFIG_ERROR = resolve_model_config()

if MODEL_CONFIG_ERROR:
    # 仍然构造一个模型对象：create_deep_agent 在 import 期就要它。
    # 占位 Key 不会被真正用到 —— main_agent 在跑任务前会先检查 MODEL_CONFIG_ERROR。
    model = init_chat_model(
        model=model_name or "qwen-plus",
        model_provider="openai",
        api_key="***",
        base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
else:
    model = init_chat_model(
        model=model_name,
        model_provider="openai",
        api_key=api_key,
        base_url=base_url,
    )


if __name__ == "__main__":
    if MODEL_CONFIG_ERROR:
        print(MODEL_CONFIG_ERROR)
    else:
        print(model.invoke("你是谁").content)
