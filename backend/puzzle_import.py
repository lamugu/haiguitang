"""题库导入：把人工粘贴的原始文本规范化成结构化题目。

流程：清洗 markdown 噪音 → 按段落分块 → 每块 LLM 抽取 JSON（含 tags）→
校验去重 → 写入题库。

对外状态字段使用 camelCase，与前端对齐；不回传模型信息。
"""
import asyncio
import re
import threading
import uuid
from dataclasses import dataclass, field

import ai_client
import puzzle_bank

CHUNK_MAX = 3000

IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
LIST_BULLET = re.compile(r"^\s*[-*+]\s*", re.MULTILINE)
BLANK_RUN = re.compile(r"\n{3,}")
ANSWER_PREFIXES = ("汤底", "答案", "真相")


@dataclass
class ImportJob:
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chunks: int = 0
    chunk_done: int = 0
    extracted: int = 0
    imported: int = 0
    total: int = 0
    done: bool = False
    error: str = ""

    def to_public(self) -> dict:
        return {
            "jobId": self.job_id,
            "chunks": self.chunks,
            "chunkDone": self.chunk_done,
            "extracted": self.extracted,
            "imported": self.imported,
            "total": self.total,
            "done": self.done,
            "error": self.error,
        }


_jobs: dict[str, ImportJob] = {}


def clean(raw: str) -> str:
    md = IMAGE.sub("", raw)
    md = LINK.sub(r"\1", md)
    md = HEADING.sub("", md)
    md = LIST_BULLET.sub("", md)
    md = BLANK_RUN.sub("\n\n", md)
    return md.strip()


def _is_answer(paragraph: str) -> bool:
    head = paragraph[:4]
    return any(head.startswith(p) or paragraph.startswith("**" + p) for p in ANSWER_PREFIXES)


def chunk(cleaned: str) -> list:
    chunks = []
    current = []
    current_len = 0
    for para in (p.strip() for p in re.split(r"\n\s*\n", cleaned)):
        if not para:
            continue
        would_split = current_len + len(para) + 2 > CHUNK_MAX
        if would_split and not _is_answer(para):
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def submit(raw: str) -> dict:
    if not raw or not raw.strip():
        raise ValueError("内容为空")

    chunks = chunk(clean(raw))
    job = ImportJob(chunks=len(chunks), total=puzzle_bank.size())
    _jobs[job.job_id] = job
    print(f"导入：原文 {len(raw)} 字符，分 {len(chunks)} 块")
    threading.Thread(target=_run_in_loop, args=(job, chunks), daemon=True).start()
    return job.to_public()


def _run_in_loop(job: ImportJob, chunks: list) -> None:
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run(job, chunks))
    finally:
        loop.close()


def get_job(job_id: str) -> dict | None:
    job = _jobs.get(job_id)
    return None if job is None else job.to_public()


async def _run(job: ImportJob, chunks: list) -> None:
    try:
        extracted = []
        for chunk_text in chunks:
            try:
                extracted.extend(await ai_client.extract_puzzles(chunk_text))
            except Exception as e:
                print(f"第 {job.chunk_done + 1}/{len(chunks)} 块抽取失败，跳过该块：{e}")
            job.chunk_done += 1
            job.extracted = len(extracted)
            print(f"第 {job.chunk_done}/{len(chunks)} 块抽取完成，累计 {len(extracted)} 条")

        imported = puzzle_bank.add_all(extracted)
        job.imported = imported
        job.total = puzzle_bank.size()
        print(f"导入完成：抽取 {len(extracted)} 条，新增 {imported} 条，题库共 {puzzle_bank.size()} 条")
    except Exception as e:
        job.error = str(e)
        print("导入失败：", e)
    finally:
        job.done = True
