"""配置：全部从环境变量读取，密钥不进代码、不回传前端。

两套独立服务：
- 主持人判决（原 jev 职责）→ Vercel AI Gateway
- 导入抽取 / 提交答案语义判定 → 原 LLM（OpenAI 兼容，如 Atria）
"""
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


# ---------- 判决（jev 职责）→ Vercel AI Gateway ----------
AI_GATEWAY_URL = _env("AI_GATEWAY_URL", "https://ai-gateway.vercel.sh/v1").rstrip("/")
# 兼容旧名 JEV_API_KEY：有人仍把判决密钥叫 jev key
AI_GATEWAY_API_KEY = (
    _env("AI_GATEWAY_API_KEY")
    or _env("VERCEL_AI_GATEWAY_API_KEY")
    or _env("JEV_API_KEY")
)
AI_GATEWAY_MODEL = _env("AI_GATEWAY_MODEL", "openai/gpt-4o-mini")
CLOSENESS_THRESHOLD = float(_env("CLOSENESS_THRESHOLD", "0.7"))

# ---------- 原 LLM（导入 / 判答案）----------
AI_API_KEY = _env("AI_API_KEY")
AI_API_URL = _env("AI_API_URL", "https://api.atria-asi.ai/v1").rstrip("/")
AI_MODEL = _env("AI_MODEL", "Atria-Dawn-Preview")
AI_MAX_RETRIES = int(_env("AI_MAX_RETRIES", "4"))

PLACEHOLDER_KEY = "填写你自己的 API Key"

SQLITE_PATH = _env("SQLITE_PATH", "data/puzzles.db")
STATIC_DIR = _env("STATIC_DIR", "")

# 管理端口令（汤库增删改 / 含汤底列表 / 导入）
ADMIN_KEY = _env("ADMIN_KEY")

DEFAULT_TAGS = ("经典", "悬疑", "惊悚", "温情", "烧脑", "奇幻", "日常")


def gateway_ready() -> bool:
    """判决通道是否可用。"""
    return bool(AI_GATEWAY_API_KEY)


def llm_ready() -> bool:
    """原 LLM 是否可用（导入 + 提交答案）。"""
    return bool(AI_API_KEY) and AI_API_KEY != PLACEHOLDER_KEY


def admin_ready() -> bool:
    return bool(ADMIN_KEY)