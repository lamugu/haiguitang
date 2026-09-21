"""LLM 客户端：经 Vercel AI Gateway（导入抽取 / 答案判定）。"""
from __future__ import annotations

import asyncio
import json
import re

import httpx

import config

EXTRACT_SYS = (
    "从用户给出的文本中提取所有海龟汤谜题，整理成 JSON 数组。"
    "每个元素字段：\n"
    "- surface：汤面，题目的故事表面描述\n"
    "- truth：汤底，故事的真相/答案\n"
    "- tags：字符串数组，从「经典/悬疑/惊悚/温情/烧脑/奇幻/日常」中选 1~3 个最合适的分类；"
    "若原文无分类信息，按内容自行判断，不要留空\n"
    "要求：只从文本中提取汤面与汤底，不要编造故事；保留原文语言和措辞；"
    "文本里的引号一律用中文全角引号「」，避免破坏 JSON；"
    "只输出 JSON 数组本身，不要任何解释。"
)

FIELD = re.compile(r'"(surface|truth)"\s*:\s*"((?:[^"]|"(?!\s*[,}]))*)"')
TAGS_FIELD = re.compile(r'"tags"\s*:\s*\[([^\]]*)\]')

CHECK_SYS = "判断玩家答案是否还原了汤底的关键真相。只回复【答案正确】或【答案错误】。"


async def _chat(messages: list, timeout: float = 90.0) -> str:
    if not config.gateway_ready():
        raise RuntimeError("AI 服务未配置：请设置 AI_GATEWAY_API_KEY")
    payload = {
        "model": config.AI_GATEWAY_MODEL,
        "messages": messages,
    }
    last = None
    for attempt in range(1, config.AI_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=10.0),
                trust_env=False,
            ) as client:
                resp = await client.post(
                    f"{config.AI_GATEWAY_URL}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {config.AI_GATEWAY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code in (401, 403):
                raise RuntimeError("AI 服务鉴权失败，请检查 AI_GATEWAY_API_KEY")
            resp.raise_for_status()
            body = resp.json()
            choices = body.get("choices") or []
            if not choices:
                raise RuntimeError("AI 返回缺少 choices")
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise RuntimeError("AI 返回缺少 content")
            return content
        except RuntimeError:
            raise
        except Exception as e:
            last = e
            print(f"AI 调用失败（第 {attempt} 次）：{e}")
            if attempt < config.AI_MAX_RETRIES:
                await asyncio.sleep(2.0 * attempt)
    raise RuntimeError(f"AI 调用多次失败：{last}")


async def check_answer(truth: str, player_answer: str) -> bool:
    result = await _chat([
        {"role": "system", "content": CHECK_SYS},
        {"role": "user", "content": f"汤底：{truth}\n玩家答案：{player_answer}"},
    ])
    return "【答案正确】" in result


async def extract_puzzles(chunk: str) -> list:
    raw = await _chat([
        {"role": "system", "content": EXTRACT_SYS},
        {"role": "user", "content": chunk},
    ])
    return parse_puzzle_json(raw)


def _normalize_item(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    surface = item.get("surface")
    truth = item.get("truth")
    if not isinstance(surface, str) or not isinstance(truth, str):
        return None
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace("，", ",").split(",") if t.strip()]
    elif isinstance(tags, list):
        tags = [str(t).strip() for t in tags if str(t).strip()]
    else:
        tags = []
    return {"surface": surface, "truth": truth, "tags": tags}


def parse_puzzle_json(raw: str) -> list:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text, count=1)
        text = re.sub(r"```$", "", text, count=1).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        body = text[start : end + 1]
        try:
            arr = json.loads(body)
            result = [p for p in (_normalize_item(item) for item in arr) if p]
            if result:
                return result
        except Exception as e:
            print(f"严格 JSON 解析失败，改用容错解析：{e}")

    values = [m.group(2) for m in FIELD.finditer(text)]
    tag_blocks = TAGS_FIELD.findall(text)
    result = []
    for i in range(0, len(values) - 1, 2):
        pair_idx = i // 2
        tags = []
        if pair_idx < len(tag_blocks):
            tags = re.findall(r'"([^"]+)"', tag_blocks[pair_idx])
        result.append({"surface": values[i], "truth": values[i + 1], "tags": tags})
    if not result:
        print("LLM 未返回可识别的题目 JSON：", text[:120])
    return result
