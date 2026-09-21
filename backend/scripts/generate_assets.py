"""并发生成前端氛围素材（Nova images API）。密钥只走环境变量，不进仓库。"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
from pathlib import Path

import httpx

API_URL = os.environ.get("NOVA_API_URL", "https://nova.7399888.xyz").rstrip("/")
API_KEY = os.environ.get("NOVA_API_KEY", "")
MODEL = os.environ.get("NOVA_MODEL", "nova")

OUT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "assets"

ASSETS = [
    {
        "name": "hero-bg.png",
        "size": "1792x1024",
        "prompt": (
            "Cinematic wide illustration of a steam-wreathed soup bowl on a dark lacquered table, "
            "moonlit ink-wash atmosphere, deep teal and amber light, mysterious narrative game mood, "
            "no text, no watermark, no logos, elegant East-Asian mystery aesthetic"
        ),
    },
    {
        "name": "brand-bowl.png",
        "size": "1024x1024",
        "prompt": (
            "Centered emblem of a steaming ceramic soup bowl, minimal premium game brand icon, "
            "deep teal glaze with warm amber rim highlights, soft volumetric steam, "
            "clean solid dark background, no text, no watermark"
        ),
    },
    {
        "name": "avatar-host.png",
        "size": "1024x1024",
        "prompt": (
            "Close-up portrait of a mysterious game host wearing a dark hooded coat, "
            "calm half-smile, teal-amber rim lighting, painterly character art for chat avatar, "
            "square composition, no text, no watermark"
        ),
    },
    {
        "name": "avatar-player.png",
        "size": "1024x1024",
        "prompt": (
            "Close-up portrait of a curious young investigator, soft amber key light, "
            "thoughtful expression, painterly character art for chat avatar, "
            "square composition, no text, no watermark"
        ),
    },
    {
        "name": "pattern-mist.png",
        "size": "1024x1024",
        "prompt": (
            "Seamless soft mist and ink-wash texture background for UI, deep teal and charcoal, "
            "subtle paper grain, low contrast, abstract atmospheric pattern, no objects, no text"
        ),
    },
    {
        "name": "empty-bowl.png",
        "size": "1024x1024",
        "prompt": (
            "Elegant empty ceramic bowl with faint residual steam, quiet melancholy mood, "
            "deep teal table, soft amber edge light, illustration for empty-state UI, no text"
        ),
    },
]


async def generate_one(client: httpx.AsyncClient, asset: dict) -> Path:
    payload = {
        "model": MODEL,
        "prompt": asset["prompt"],
        "n": 1,
        "size": asset["size"],
        "response_format": "b64_json",
    }
    resp = await client.post(f"{API_URL}/v1/images/generations", json=payload)
    resp.raise_for_status()
    body = resp.json()
    item = (body.get("data") or [None])[0]
    if not item:
        raise RuntimeError(f"{asset['name']}: empty data")

    out = OUT_DIR / asset["name"]
    if item.get("b64_json"):
        out.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        img = await client.get(item["url"])
        img.raise_for_status()
        out.write_bytes(img.content)
    else:
        raise RuntimeError(f"{asset['name']}: no b64_json/url")
    print(f"OK {asset['name']} -> {out}")
    return out


async def main() -> int:
    if not API_KEY:
        print("缺少 NOVA_API_KEY", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timeout = httpx.Timeout(180.0, connect=20.0)
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, trust_env=False) as client:
        results = await asyncio.gather(
            *[generate_one(client, a) for a in ASSETS],
            return_exceptions=True,
        )
    failed = [r for r in results if isinstance(r, Exception)]
    for err in failed:
        print(f"FAIL {err}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

