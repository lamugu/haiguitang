"""配置：全部从环境变量读取，密钥不进代码、不回传前端。

两套独立服务：
- 判决提问（jev）：默认 Vercel AI Gateway，通常只需 JEV_API_KEY
- 导入 / 提交答案：任意 OpenAI 兼容 chat/completions（AI_API_URL + AI_MODEL + AI_API_KEY）
"""
from __future__ import annotations

import os
import re
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


def _normalize_openai_base(url: str) -> str:
    """接受根地址或误贴的 .../chat/completions，统一成 .../v1 基址。"""
    u = (url or "").strip().rstrip("/")
    if not u:
        return u
    u = re.sub(r"/chat/completions/?$", "", u, flags=re.I)
    return u.rstrip("/")


# ---------- jev 判决 → 默认 Vercel AI Gateway（只需 key）----------
JEV_API_KEY = (
    _env("JEV_API_KEY")
    or _env("AI_GATEWAY_API_KEY")
    or _env("VERCEL_AI_GATEWAY_API_KEY")
)
# 一般不用改；需要时再覆盖
JEV_API_URL = _normalize_openai_base(
    _env("JEV_API_URL") or _env("AI_GATEWAY_URL") or "https://ai-gateway.vercel.sh/v1"
)
JEV_MODEL = _env("JEV_MODEL") or _env("AI_GATEWAY_MODEL") or "openai/gpt-4o-mini"
CLOSENESS_THRESHOLD = float(_env("CLOSENESS_THRESHOLD", "0.95"))
# 至少提问这么多次后，才允许因 closeness 自动揭底（防误判提前结束）
CLOSENESS_MIN_QUESTIONS = int(_env("CLOSENESS_MIN_QUESTIONS", "8"))
# 是否启用「逼近真相自动揭底」；默认关闭，只靠提交答案/退出结束
CLOSENESS_AUTO_END = _env("CLOSENESS_AUTO_END", "0").lower() in ("1", "true", "yes", "on")

# 兼容旧变量名
AI_GATEWAY_API_KEY = JEV_API_KEY
AI_GATEWAY_URL = JEV_API_URL
AI_GATEWAY_MODEL = JEV_MODEL

# ---------- LLM：OpenAI 兼容 chat/completions（URL / model / key 均可配）----------
AI_API_KEY = _env("AI_API_KEY")
AI_API_URL = _normalize_openai_base(_env("AI_API_URL", "https://api.atria-asi.ai/v1"))
AI_MODEL = _env("AI_MODEL", "Atria-Dawn-Preview")
AI_MAX_RETRIES = int(_env("AI_MAX_RETRIES", "4"))

PLACEHOLDER_KEY = "填写你自己的 API Key"

SQLITE_PATH = _env("SQLITE_PATH", "data/puzzles.db")
STATIC_DIR = _env("STATIC_DIR", "")
ADMIN_KEY = _env("ADMIN_KEY")

DEFAULT_TAGS = (
    "经典",
    "悬疑",
    "惊悚",
    "温情",
    "烧脑",
    "奇幻",
    "日常",
    "本格",
    "变格",
    "红汤",
    "清汤",
    "黑汤",
    "荒诞",
    "搞笑",
)


def gateway_ready() -> bool:
    """jev / Gateway 判决是否可用。"""
    return bool(JEV_API_KEY)


def llm_ready() -> bool:
    """LLM（导入 + 提交答案）是否可用。"""
    return bool(AI_API_KEY) and AI_API_KEY != PLACEHOLDER_KEY


def admin_ready() -> bool:
    return bool(ADMIN_KEY)
