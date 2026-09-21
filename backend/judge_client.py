"""主持人判决客户端：经 Vercel AI Gateway 的 Chat Completions。

承担原 jev 的职责（是/否/无关 + 接近度），但走 Gateway，不走 OpenRouter Decisions。
导入与最终答案判定见 ai_client（原 LLM）。
"""
from __future__ import annotations

import json
import re

import httpx

import config

VERDICT_TEXT = {
    "yes": "是",
    "no": "否",
    "irrelevant": "与此无关",
}

JUDGE_SYS = (
    "你是海龟汤主持人。根据汤底真相，只判断玩家本轮提问该如何回答。"
    "只输出一行 JSON，不要解释、不要 markdown："
    '{"verdict":"yes|no|irrelevant","closeness":0到1的小数}'
    "\nverdict 规则："
    "yes=玩家陈述与汤底事实相符；no=与汤底事实不符；"
    "irrelevant=该问题对还原汤底无关紧要（闲聊、元规则、无法从汤底判定的）。"
    "\ncloseness 规则（必须极严格，宁低勿高）："
    "closeness 表示玩家是否已经基本拼出汤底的核心机制/因果，而不是问题是否相关。"
    "0.0~0.3：刚开始或只在外围线索打转（例如只确认是否自杀、是否与地点有关）；"
    "0.3~0.6：摸到部分要素，但关键因果仍未串起；"
    "0.6~0.85：接近但还缺关键一环；"
    "只有当问答历史表明玩家已能说出接近完整的关键真相时，才给 0.9+。"
    "单个相关问题、哪怕答案是「是」，closeness 也通常应低于 0.4。"
    "不要因为提问「沾边」就抬高 closeness。"
)

ANSWER_SYS = (
    "你是海龟汤主持人。判断玩家最终答案是否还原汤底关键真相。"
    "只输出一行 JSON，不要解释："
    '{"correct":true或false,"confidence":0到1的小数}'
)


def verdict_text(verdict: str) -> str:
    return VERDICT_TEXT.get(verdict, "与此无关")


def _ensure_ready() -> None:
    if not config.gateway_ready():
        raise RuntimeError("判决服务未配置：请设置 JEV_API_KEY 后重启")


def _chat(messages: list[dict], timeout: float = 90.0) -> str:
    _ensure_ready()
    payload = {
        "model": config.JEV_MODEL,
        "messages": messages,
        "temperature": 0,
    }
    last_err: Exception | None = None
    for attempt in range(1, config.AI_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0), trust_env=False) as client:
                resp = client.post(
                    f"{config.JEV_API_URL}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {config.JEV_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code in (401, 403):
                raise RuntimeError("提问服务鉴权失败，请检查 JEV_API_KEY")
            if resp.status_code >= 400:
                raise RuntimeError(f"提问服务暂时不可用（HTTP {resp.status_code}）")
            body = resp.json()
            choices = body.get("choices") or []
            if not choices:
                raise RuntimeError("提问服务返回异常")
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise RuntimeError("提问服务返回异常")
            return content
        except RuntimeError:
            raise
        except Exception as e:
            last_err = e
            print(f"Gateway 调用失败（第 {attempt} 次）：{e}")
    raise RuntimeError(f"提问服务多次失败：{last_err}")


def _parse_json_obj(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, count=1).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("提问服务返回无法解析")
    return json.loads(text[start : end + 1])


def judge(state_text: str, question: str) -> dict:
    """判定玩家提问，返回 verdict / confidence / closeness。"""
    raw = _chat([
        {"role": "system", "content": JUDGE_SYS},
        {
            "role": "user",
            "content": f"{state_text}\n\n玩家本轮提问：{question}",
        },
    ])
    data = _parse_json_obj(raw)
    verdict = str(data.get("verdict") or "irrelevant").lower().strip()
    if verdict not in VERDICT_TEXT:
        # 兼容中文
        mapping = {"是": "yes", "否": "no", "与此无关": "irrelevant", "无关": "irrelevant"}
        verdict = mapping.get(verdict, "irrelevant")
    try:
        closeness = float(data.get("closeness", 0))
    except (TypeError, ValueError):
        closeness = 0.0
    closeness = max(0.0, min(1.0, closeness))
    return {
        "verdict": verdict,
        "confidence": -1.0,
        "closeness": closeness,
    }


def judge_answer(state_text: str, answer: str) -> float:
    """判定最终答案，返回 0~1 把握度。"""
    raw = _chat([
        {"role": "system", "content": ANSWER_SYS},
        {
            "role": "user",
            "content": f"{state_text}\n\n玩家提交的最终答案：{answer}",
        },
    ])
    data = _parse_json_obj(raw)
    if "correct" in data:
        correct = bool(data["correct"])
        try:
            conf = float(data.get("confidence", 1.0 if correct else 0.0))
        except (TypeError, ValueError):
            conf = 1.0 if correct else 0.0
        return conf if correct else min(conf, 0.49)
    try:
        return float(data.get("confidence", 0))
    except (TypeError, ValueError):
        return 0.0
