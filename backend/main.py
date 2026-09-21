"""海龟汤后端。

对外接口不暴露模型名、密钥或内部实现细节。
汤底仅在游戏结束或管理端返回。
生产环境可托管前端 dist（同域 /api）。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
import game_service
import puzzle_bank
import puzzle_import

app = FastAPI(title="海龟汤", docs_url=None, redoc_url=None, openapi_url=None)
api = FastAPI(root_path="/api", docs_url=None, redoc_url=None, openapi_url=None)

for target in (app, api):
    target.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


class PuzzleIn(BaseModel):
    surface: str
    truth: str
    tags: List[str] = Field(default_factory=list)


class PuzzleBatchIn(BaseModel):
    items: List[PuzzleIn]


class PuzzleUpdateIn(BaseModel):
    surface: Optional[str] = None
    truth: Optional[str] = None
    tags: Optional[List[str]] = None


def _resolve_static() -> Path | None:
    candidates = []
    if config.STATIC_DIR:
        candidates.append(Path(config.STATIC_DIR))
    here = Path(__file__).resolve().parent
    candidates.append(here / "static")
    candidates.append(here.parent / "frontend" / "dist")
    for path in candidates:
        if (path / "index.html").exists():
            return path
    return None


@app.on_event("startup")
def _startup() -> None:
    puzzle_bank.load()
    if not config.gateway_ready():
        print("警告：未设置 AI_GATEWAY_API_KEY（判决），提问将不可用")
    if not config.llm_ready():
        print("警告：未设置 AI_API_KEY（原 LLM），导入/答案语义判定将降级")
    static = _resolve_static()
    if static:
        print(f"静态前端目录：{static}")
    else:
        print("未找到前端 dist，仅提供 API")


def _friendly_error(exc: Exception) -> JSONResponse:
    msg = str(exc) or "请求失败"
    lowered = msg.lower()
    if any(x in lowered for x in ("api", "key", "model", "bearer", "gateway", "vercel", "atria")):
        if "未配置" in msg or "ai_gateway" in lowered or "ai_api" in lowered:
            msg = "服务未配置，请检查 AI_GATEWAY_API_KEY / AI_API_KEY"
        else:
            msg = "服务暂时不可用，请稍后重试"
    return JSONResponse(status_code=400, content={"message": msg})


@app.exception_handler(Exception)
async def _on_error_app(request: Request, exc: Exception):
    return _friendly_error(exc)


@api.exception_handler(Exception)
async def _on_error_api(request: Request, exc: Exception):
    return _friendly_error(exc)


@api.get("/health")
def health():
    return {
        "ok": True,
        "puzzles": puzzle_bank.size(),
        "gatewayConfigured": config.gateway_ready(),
        "llmConfigured": config.llm_ready(),
    }


@api.post("/chat/{room_id}/send", response_class=PlainTextResponse)
def send(room_id: int, message: str = Query(...)):
    return game_service.do_chat(room_id, message)


@api.post("/chat/{room_id}/start", response_class=PlainTextResponse)
def start(
    room_id: int,
    puzzle_index: Optional[int] = Query(None, alias="puzzleIndex"),
    tag: Optional[str] = None,
):
    return game_service.start_game(room_id, puzzle_index=puzzle_index, tag=tag)


@api.post("/chat/{room_id}/submit", response_class=PlainTextResponse)
async def submit(room_id: int, answer: str = Query(...)):
    return await game_service.submit_answer(room_id, answer)


@api.post("/chat/{room_id}/next", response_class=PlainTextResponse)
def next_puzzle(room_id: int, tag: Optional[str] = None):
    return game_service.next_puzzle(room_id, tag=tag)


@api.get("/chat/rooms")
def rooms():
    return game_service.list_rooms()


@api.post("/puzzles/import")
def import_puzzles(text: str = Query(...)):
    return puzzle_import.submit(text)


@api.get("/puzzles/import/status")
def import_status(job_id: str = Query(..., alias="jobId")):
    job = puzzle_import.get_job(job_id)
    if job is None:
        raise ValueError("任务不存在或已过期")
    return job


@api.get("/puzzles/stats")
def stats():
    return {
        "total": puzzle_bank.size(),
        "tags": puzzle_bank.list_tags(),
        "suggestedTags": list(config.DEFAULT_TAGS),
    }


@api.get("/puzzles/tags")
def tags():
    return {
        "tags": puzzle_bank.list_tags(),
        "suggestedTags": list(config.DEFAULT_TAGS),
    }


@api.get("/puzzles/catalog")
def catalog(tag: Optional[str] = None):
    items = puzzle_bank.list_catalog(tag=tag)
    return {"total": len(items), "items": items, "tags": puzzle_bank.list_tags()}


@api.get("/puzzles/list")
def puzzle_list():
    return {"total": puzzle_bank.size(), "items": puzzle_bank.list_all()}


@api.post("/puzzles/add", response_class=PlainTextResponse)
def puzzle_add(
    surface: str = Query(...),
    truth: str = Query(...),
    tags: Optional[str] = Query(None),
):
    tag_list = [t.strip() for t in (tags or "").replace("，", ",").split(",") if t.strip()]
    if puzzle_bank.add_one(surface, truth, tag_list):
        return f"已加入题库，现有 {puzzle_bank.size()} 道题"
    return "添加失败：汤面或汤底为空，或汤面已存在"


@api.post("/puzzles/add/json")
def puzzle_add_json(body: PuzzleIn):
    ok = puzzle_bank.add_one(body.surface, body.truth, body.tags)
    if not ok:
        return {"ok": False, "message": "添加失败：汤面或汤底为空，或汤面已存在"}
    return {"ok": True, "total": puzzle_bank.size()}


@api.post("/puzzles/batch")
def puzzle_batch(body: PuzzleBatchIn):
    added = puzzle_bank.add_all([item.model_dump() for item in body.items])
    return {"ok": True, "imported": added, "total": puzzle_bank.size()}


@api.put("/puzzles/{index}")
def puzzle_update(index: int, body: PuzzleUpdateIn):
    ok = puzzle_bank.update_at(index, body.surface, body.truth, body.tags)
    if not ok:
        return {"ok": False, "message": "更新失败"}
    return {"ok": True}


@api.delete("/puzzles/{index}")
def puzzle_delete(index: int):
    if not puzzle_bank.delete_at(index):
        return {"ok": False, "message": "索引不存在"}
    return {"ok": True, "total": puzzle_bank.size()}


app.mount("/api", api)

_static_dir = _resolve_static()
if _static_dir is not None:
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="spa")


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT") or os.environ.get("PY_PORT", "8081")))
