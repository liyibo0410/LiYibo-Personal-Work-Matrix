"""P07 配置：从仓库根 `.env` 读取模型凭证，跨模块端点从 SERVICE_REGISTRY 解析。

主用 Key 为空时自动落到备用端点（百炼 sk- / sk-sp- 凭证互认自己的端点），
保证「有任一端点可用就真调模型」，全不可用才降级并标注。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config.py → parents[0]=app，parents[1]=模块根
BASE_DIR = Path(__file__).resolve().parents[1]

# 仓库根的标记键：只有根 .env 同时定义了主/备两套百炼凭证，用它当定位锚点。
# 不要用硬编码 parents[N] —— P03 曾因把仓库根算成 projects/ 而读不到 .env（见 _evidence/INDEX.md D12）。
_ROOT_ENV_MARKER = "LLM_API_KEY_FALLBACK"
_PLACEHOLDER_HINTS = ("mock", "your-", "your_", "xxx", "changeme", "change-me", "todo", "placeholder")


def _find_repo_root() -> Path:
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
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
WEB_DIR = BASE_DIR / "web"
PROMPT_DIR = BASE_DIR / "prompts"
DB_PATH = DATA_DIR / "assets.db"

# ingest 允许的来源（P02 推送素材时声明）
INGEST_SOURCES = {"p02-ecommerce-ops", "manual", "demo"}


def is_usable(value: str) -> bool:
    """凭证是否真的可用：空值、短值与占位符字样都不算配置。"""
    v = (value or "").strip().lower()
    if len(v) < 8:
        return False
    return not any(h in v for h in _PLACEHOLDER_HINTS)


@dataclass(frozen=True)
class LLMEndpoint:
    base_url: str
    api_key: str
    model: str
    label: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    LLM_MODEL_FAST: str = ""
    LLM_BASE_URL_FALLBACK: str = ""
    LLM_API_KEY_FALLBACK: str = ""
    LLM_MODEL_ALT: str = ""
    P07_INGEST_TOKEN: str = ""

    def llm_endpoint(self, *, prefer_fast: bool = False) -> LLMEndpoint | None:
        """第一个凭证齐全的端点；都不齐返回 None（调用方据此走降级并标注）。

        百炼 sk- / sk-sp- 凭证互认自己的端点，主用 Key 为空时自动落到备用端点。
        `prefer_fast` 用 LLM_MODEL_FAST：打标这类短结构化输出没必要走推理模型（实测 8.2s vs 1s 级）。
        """
        primary = LLMEndpoint(self.LLM_BASE_URL, self.LLM_API_KEY, self._model_for(prefer_fast), "primary")
        fallback = LLMEndpoint(
            self.LLM_BASE_URL_FALLBACK,
            self.LLM_API_KEY_FALLBACK,
            self._model_for(prefer_fast) or self.LLM_MODEL_ALT,
            "fallback",
        )
        for ep in (primary, fallback):
            if ep.base_url.startswith("http") and is_usable(ep.api_key) and ep.model:
                return ep
        return None

    def _model_for(self, prefer_fast: bool) -> str:
        return (self.LLM_MODEL_FAST or self.LLM_MODEL) if prefer_fast else self.LLM_MODEL

    @property
    def llm_ready(self) -> bool:
        return self.llm_endpoint() is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_prompt(name: str) -> str:
    """读取 prompts/ 下版本化的 prompt（禁止硬编码在函数里）。"""
    path = PROMPT_DIR / name
    return path.read_text(encoding="utf-8").strip()
