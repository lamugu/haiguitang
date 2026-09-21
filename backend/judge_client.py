"""主持人判决客户端：经 Vercel AI Gateway 的 Chat Completions。

用结构化 JSON 输出替代旧的独立决策协议，统一走网关密钥。
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
    "你是海龟汤主持人。根据汤底真相判断玩家提问。"
    "只输出一行 JSON，不要解释、不要 markdown："
    '{"verdict":"yes|no|irrelevant","closeness":0到1的小数}'
    "规则：yes=陈述与汤底相符；no=与汤底不符；irrelevant=与关键真相无关；"
    "closeness=玩家已还原关键真相的程度（0~1）。"
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
        raise RuntimeError(
            "提问服务未配置：请设置 AI_GATEWAY_API_KEY（Vercel AI Gateway）后重启"
        )


def _chat(messages: list[dict], timeout: float = 90.0) -> str:
    _ensure_ready()
    payload = {
        "model": config.AI_GATEWAY_MODEL,
        "messages": messages,
        "temperature": 0,
    }
    last_err: Exception | None = None
    for attempt in range(1, config.AI_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0), trust_env=False) as client:
                resp = client.post(
                    f"{config.AI_GATEWAY_URL}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {config.AI_GATEWAY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code in (401, 403):
                raise RuntimeError("提问服务鉴权失败，请检查 AI_GATEWAY_API_KEY")
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
