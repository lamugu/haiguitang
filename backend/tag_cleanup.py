"""标签整理：规则预览 + LLM 建议。"""
from __future__ import annotations

import json
import re
from typing import Any

import ai_client
import config
import puzzle_bank

# 过细剧情/场景标签 → 并入粗分类；空字符串表示建议删除
RULE_MERGES: dict[str, str] = {
    "恐怖": "惊悚",
    "微恐": "惊悚",
    "死亡": "惊悚",
    "自杀": "惊悚",
    "谋杀": "惊悚",
    "全员死亡": "惊悚",
    "连环杀人": "惊悚",
    "杀人埋尸": "惊悚",
    "杀妻": "惊悚",
    "肢解": "惊悚",
    "解剖": "惊悚",
    "尸体": "惊悚",
    "无头": "惊悚",
    "断脚": "惊悚",
    "人皮": "惊悚",
    "重口": "红汤",
    "儿童杀人": "惊悚",
    "囚禁": "惊悚",
    "复仇": "惊悚",
    "绑架": "悬疑",
    "犯罪": "悬疑",
    "黑帮": "悬疑",
    "凶手": "悬疑",
    "偷窥": "悬疑",
    "寄居": "悬疑",
    "夹层": "悬疑",
    "鬼": "奇幻",
    "灵异": "奇幻",
    "科幻": "奇幻",
    "穿越": "奇幻",
    "清醒梦": "奇幻",
    "梦游": "奇幻",
    "人性": "温情",
    "悲剧": "温情",
    "童年": "温情",
    "办公室": "日常",
    "医院": "日常",
    "电影院": "日常",
    "电梯井": "日常",
    "独居": "日常",
    "理发": "日常",
    "动物": "日常",
    "钓鱼": "日常",
    "洗衣机": "日常",
    "拼多多": "日常",
    "海尔兄弟": "荒诞",
    "精神病": "悬疑",
    "慢性毒": "悬疑",
    "毒鼠": "悬疑",
    "拐卖": "惊悚",
    "民俗": "奇幻",
    "变性": "悬疑",
    "男情人": "悬疑",
    "装瞎": "悬疑",
    "反手": "烧脑",
    "呼吸机": "悬疑",
    "人体实验": "惊悚",
    "侏儒": "悬疑",
    "车窗雾气": "悬疑",
    "晕船": "日常",
    "打嗝": "日常",
    "意外": "日常",
    "绝望": "惊悚",
    "赌博": "悬疑",
}

RULE_DELETES = {
    "未揭晓",
    "未详",
    "原创",
    "留题",
}


def _canonical() -> list[str]:
    return list(config.DEFAULT_TAGS)


def rule_plan(existing: list[dict] | None = None) -> dict:
    """基于内置规则生成整理方案（不改库）。"""
    tags = existing if existing is not None else puzzle_bank.list_tags()
    names = {t["name"] for t in tags}
    merges: dict[str, str] = {}
    deletes: list[str] = []
    notes: list[str] = []

    for src, dst in RULE_MERGES.items():
        if src in names and src != dst:
            merges[src] = dst
            notes.append(f"规则：{src} → {dst}")

    for name in RULE_DELETES:
        if name in names:
            deletes.append(name)
            notes.append(f"规则：删除 {name}")

    # 计数为 1 且不在标准库、也未进入合并表的，建议删除（剧情碎片）
    canon = set(_canonical())
    for t in tags:
        n = t["name"]
        if n in canon or n in merges or n in deletes:
            continue
        if int(t.get("count") or 0) <= 1:
            deletes.append(n)
            notes.append(f"规则：低频碎片「{n}」建议删除")

    return {
        "merges": merges,
        "deletes": sorted(set(deletes)),
        "canonical": _canonical(),
        "notes": notes,
        "source": "rules",
    }


async def llm_plan(existing: list[dict] | None = None) -> dict:
    """调用 LLM 生成整理方案（不改库）。失败时回退规则方案。"""
    tags = existing if existing is not None else puzzle_bank.list_tags()
    if not tags:
        return {
            "merges": {},
            "deletes": [],
            "canonical": _canonical(),
            "notes": ["题库暂无标签"],
            "source": "empty",
        }

    if not config.llm_ready():
        plan = rule_plan(tags)
        plan["notes"] = ["LLM 未配置，已使用规则方案"] + plan["notes"]
        return plan

    try:
        raw = await ai_client.suggest_tag_cleanup(tags, _canonical())
        plan = _parse_llm_plan(raw, {t["name"] for t in tags})
        plan["source"] = "llm"
        return plan
    except Exception as e:
        plan = rule_plan(tags)
        plan["notes"] = [f"LLM 失败（{e}），已回退规则方案"] + plan["notes"]
        return plan


def _parse_llm_plan(raw: str, existing_names: set[str]) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, count=1).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("LLM 未返回 JSON 方案")
    data: Any = json.loads(text[start : end + 1])

    merges_raw = data.get("merges") or {}
    merges: dict[str, str] = {}
    if isinstance(merges_raw, dict):
        for k, v in merges_raw.items():
            src, dst = str(k).strip(), str(v).strip()
            if src and dst and src != dst and src in existing_names:
                merges[src] = dst
    elif isinstance(merges_raw, list):
        for item in merges_raw:
            if not isinstance(item, dict):
                continue
            src = str(item.get("from") or item.get("source") or "").strip()
            dst = str(item.get("to") or item.get("target") or "").strip()
            if src and dst and src != dst and src in existing_names:
                merges[src] = dst

    deletes: list[str] = []
    for t in data.get("deletes") or []:
        name = str(t).strip()
        if name and name in existing_names and name not in merges:
            deletes.append(name)

    notes = [str(n) for n in (data.get("notes") or []) if str(n).strip()]
    return {
        "merges": merges,
        "deletes": sorted(set(deletes)),
        "canonical": _canonical(),
        "notes": notes or ["LLM 已生成方案，请预览后应用"],
    }
