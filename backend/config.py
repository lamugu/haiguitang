"""配置：全部从环境变量读取，密钥不进代码、不回传前端。"""
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    path = Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# Vercel AI Gateway（OpenAI 兼容）
# https://ai-gateway.vercel.sh/v1
AI_GATEWAY_URL = _env("AI_GATEWAY_URL", "https://ai-gateway.vercel.sh/v1").rstrip("/")
AI_GATEWAY_API_KEY = (
    _env("AI_GATEWAY_API_KEY")
    or _env("VERCEL_AI_GATEWAY_API_KEY")
    or _env("AI_API_KEY")
)
AI_GATEWAY_MODEL = _env("AI_GATEWAY_MODEL", "openai/gpt-4o-mini")
AI_MAX_RETRIES = int(_env("AI_MAX_RETRIES", "4"))

# 逼近真相自动揭底阈值
CLOSENESS_THRESHOLD = float(_env("CLOSENESS_THRESHOLD", "0.7"))

SQLITE_PATH = _env("SQLITE_PATH", "data/puzzles.db")
STATIC_DIR = _env("STATIC_DIR", "")

DEFAULT_TAGS = ("经典", "悬疑", "惊悚", "温情", "烧脑", "奇幻", "日常")


def gateway_ready() -> bool:
    return bool(AI_GATEWAY_API_KEY)
