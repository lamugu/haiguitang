"""题库：SQLite 持久化，支持 tags 分类。

启动时若库为空：优先从旧版 puzzles.json 迁移，否则灌入种子题。
对外 catalog 永不返回汤底。
API 中的 index 对应表主键 id（删除后不必连续）。
"""
from __future__ import annotations

import json
import os
import random as _random
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional

import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _seed_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_puzzles.json")


def _legacy_json_path() -> str:
    # 兼容旧版 JSON 题库
    return os.path.join(os.path.dirname(config.SQLITE_PATH), "puzzles.json")


def _normalize_tags(tags) -> list:
    if tags is None:
        return []
    if isinstance(tags, str):
        text = tags.strip()
        if text.startswith("["):
            try:
                return _normalize_tags(json.loads(text))
            except Exception:
                pass
        parts = [t.strip() for t in text.replace("，", ",").split(",")]
        return [t for t in parts if t]
    if isinstance(tags, list):
        out = []
        seen = set()
        for t in tags:
            name = str(t).strip()
            if name and name not in seen:
                seen.add(name)
                out.append(name)
        return out
    return []


def _normalize_puzzle(raw: dict) -> dict | None:
    surface = (raw.get("surface") or "").strip()
    truth = (raw.get("truth") or "").strip()
    if not surface or not truth:
        return None
    return {
        "surface": surface,
        "truth": truth,
        "tags": _normalize_tags(raw.get("tags")),
    }


def _guess_tags(surface: str, truth: str) -> list:
    text = surface + truth
    tags = ["经典"]
    rules = [
        ("惊悚", ("自杀", "死", "尸", "血", "砍", "谋杀", "鬼")),
        ("悬疑", ("为什么", "究竟", "真相", "警察", "失踪")),
        ("温情", ("母亲", "父亲", "孩子", "女儿", "儿子", "爱人")),
        ("奇幻", ("魔法", "幽灵", "梦", "异世界", "穿越")),
        ("日常", ("餐厅", "火车", "房间", "邻居", "公司")),
        ("烧脑", ("逻辑", "推理", "不可能", "矛盾", "火柴", "冰块")),
    ]
    for tag, keys in rules:
        if any(k in text for k in keys) and tag not in tags:
            tags.append(tag)
        if len(tags) >= 3:
            break
    return tags[:3]


def _tags_to_db(tags: list) -> str:
    return json.dumps(tags, ensure_ascii=False)


def _tags_from_db(raw: str | None) -> list:
    return _normalize_tags(raw or "[]")


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    path = config.SQLITE_PATH
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL;")
    _conn.execute("PRAGMA foreign_keys=ON;")
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surface TEXT NOT NULL UNIQUE,
            truth TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    _conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_puzzles_surface ON puzzles(surface)"
    )
    _conn.commit()
    return _conn


def _row_to_puzzle(row: sqlite3.Row, include_truth: bool = True) -> dict:
    item = {
        "index": row["id"],
        "surface": row["surface"],
        "tags": _tags_from_db(row["tags"]),
    }
    if include_truth:
        item["truth"] = row["truth"]
    return item


def _insert_puzzle(conn: sqlite3.Connection, p: dict) -> bool:
    try:
        conn.execute(
            "INSERT INTO puzzles(surface, truth, tags) VALUES (?, ?, ?)",
            (p["surface"], p["truth"], _tags_to_db(p["tags"])),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def _bootstrap_from_list(items: list) -> int:
    conn = _connect()
    added = 0
    for item in items:
        p = _normalize_puzzle(item)
        if not p:
            continue
        if not p["tags"]:
            p["tags"] = _guess_tags(p["surface"], p["truth"])
        if _insert_puzzle(conn, p):
            added += 1
    conn.commit()
    return added


def load() -> None:
    with _lock:
        path = os.path.abspath(config.SQLITE_PATH)
        persistent_hint = path.startswith("/var/data") or os.environ.get("RENDER_DISK_MOUNT_PATH")
        if not persistent_hint:
            print(
                "⚠️ SQLite 路径不在持久盘上："
                f"{path}。Render 免费实例每次 redeploy 会清空容器磁盘，"
                "导入的题会丢失。请挂载 Disk 到 /var/data，或定期在管理页导出备份。"
            )
        conn = _connect()
        count = conn.execute("SELECT COUNT(*) AS c FROM puzzles").fetchone()["c"]
        if count > 0:
            print(f"从 SQLite {path} 加载 {count} 道题")
            return

        legacy = _legacy_json_path()
        if os.path.exists(legacy):
            with open(legacy, encoding="utf-8") as f:
                items = json.load(f)
            added = _bootstrap_from_list(items)
            print(f"已从旧 JSON 迁移 {added} 道题到 SQLite")
            return

        with open(_seed_path(), encoding="utf-8") as f:
            items = json.load(f)
        added = _bootstrap_from_list(items)
        print(f"用种子题库初始化 {added} 道题到 SQLite {path}")


def random(tag: Optional[str] = None) -> dict:
    with _lock:
        conn = _connect()
        if tag:
            rows = conn.execute("SELECT id, surface, truth, tags FROM puzzles").fetchall()
            pool = [r for r in rows if tag in _tags_from_db(r["tags"])]
            if not pool:
                raise RuntimeError(f"分类「{tag}」下暂无题目")
            row = _random.choice(pool)
        else:
            row = conn.execute(
                "SELECT id, surface, truth, tags FROM puzzles ORDER BY RANDOM() LIMIT 1"
            ).fetchone()
            if row is None:
                raise RuntimeError("题库为空")
        return {
            "index": row["id"],
            "surface": row["surface"],
            "truth": row["truth"],
            "tags": _tags_from_db(row["tags"]),
        }


def get_at(index: int) -> dict:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT id, surface, truth, tags FROM puzzles WHERE id = ?",
            (index,),
        ).fetchone()
        if row is None:
            raise RuntimeError("题目不存在")
        return {
            "index": row["id"],
            "surface": row["surface"],
            "truth": row["truth"],
            "tags": _tags_from_db(row["tags"]),
        }


def size() -> int:
    with _lock:
        conn = _connect()
        return conn.execute("SELECT COUNT(*) AS c FROM puzzles").fetchone()["c"]


def add_all(incoming: List[dict]) -> int:
    added = 0
    with _lock:
        conn = _connect()
        for raw in incoming:
            p = _normalize_puzzle(raw)
            if not p:
                continue
            if not p["tags"]:
                p["tags"] = _guess_tags(p["surface"], p["truth"])
            if _insert_puzzle(conn, p):
                added += 1
        if added:
            conn.commit()
    return added


def list_all() -> List[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT id, surface, truth, tags FROM puzzles ORDER BY id"
        ).fetchall()
        return [_row_to_puzzle(r, include_truth=True) for r in rows]


def export_backup() -> dict:
    """导出完整题库（含汤底），供管理员下载备份。"""
    items = list_all()
    return {
        "version": 1,
        "exportedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(items),
        "items": [
            {
                "surface": it["surface"],
                "truth": it["truth"],
                "tags": it.get("tags") or [],
            }
            for it in items
        ],
    }


def restore_backup(items: list, mode: str = "merge") -> dict:
    """从备份恢复。mode=merge 只追加不存在的汤面；replace 清空后全量写入。"""
    mode = (mode or "merge").strip().lower()
    if mode not in ("merge", "replace"):
        raise ValueError("mode 只能是 merge 或 replace")

    normalized = []
    for raw in items or []:
        p = _normalize_puzzle(raw if isinstance(raw, dict) else {})
        if not p:
            continue
        if not p["tags"]:
            p["tags"] = _guess_tags(p["surface"], p["truth"])
        normalized.append(p)

    with _lock:
        conn = _connect()
        if mode == "replace":
            conn.execute("DELETE FROM puzzles")
            conn.commit()
            added = 0
            for p in normalized:
                if _insert_puzzle(conn, p):
                    added += 1
            conn.commit()
            return {
                "ok": True,
                "mode": mode,
                "imported": added,
                "skipped": len(normalized) - added,
                "total": conn.execute("SELECT COUNT(*) AS c FROM puzzles").fetchone()["c"],
            }

        added = 0
        skipped = 0
        for p in normalized:
            if _insert_puzzle(conn, p):
                added += 1
            else:
                skipped += 1
        conn.commit()
        return {
            "ok": True,
            "mode": mode,
            "imported": added,
            "skipped": skipped,
            "total": conn.execute("SELECT COUNT(*) AS c FROM puzzles").fetchone()["c"],
        }


def list_catalog(tag: Optional[str] = None) -> List[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT id, surface, tags FROM puzzles ORDER BY id"
        ).fetchall()
        items = []
        for r in rows:
            tags = _tags_from_db(r["tags"])
            if tag and tag not in tags:
                continue
            items.append({
                "index": r["id"],
                "surface": r["surface"],
                "tags": tags,
            })
        return items


def list_tags() -> List[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT tags FROM puzzles").fetchall()
        counts: dict[str, int] = {}
        for r in rows:
            for t in _tags_from_db(r["tags"]):
                counts[t] = counts.get(t, 0) + 1
        preferred = list(config.DEFAULT_TAGS)
        names = preferred + sorted(n for n in counts if n not in preferred)
        return [{"name": n, "count": counts.get(n, 0)} for n in names if counts.get(n, 0) > 0]


def delete_at(index: int) -> bool:
    with _lock:
        conn = _connect()
        cur = conn.execute("DELETE FROM puzzles WHERE id = ?", (index,))
        conn.commit()
        return cur.rowcount > 0


def _remap_tags(tags: list, merges: dict[str, str], deletes: set[str]) -> list:
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        name = merges.get(t, t)
        if name in deletes or not name:
            continue
        # 链式合并：A→B、B→C
        guard = 0
        while name in merges and guard < 8:
            nxt = merges[name]
            if nxt == name:
                break
            name = nxt
            guard += 1
        if name in deletes or not name:
            continue
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def apply_tag_ops(merges: dict | None = None, deletes: list | None = None) -> dict:
    """批量合并/删除标签。merges: {旧名: 新名}；deletes: 要移除的标签名。"""
    merge_map = {str(k).strip(): str(v).strip() for k, v in (merges or {}).items() if str(k).strip() and str(v).strip()}
    delete_set = {str(t).strip() for t in (deletes or []) if str(t).strip()}
    # 合并目标若同时在删除列表，以合并为准（删的是源）
    delete_set -= set(merge_map.values())
    if not merge_map and not delete_set:
        return {"ok": True, "updated": 0, "tags": list_tags()}

    updated = 0
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT id, surface, truth, tags FROM puzzles").fetchall()
        for row in rows:
            old = _tags_from_db(row["tags"])
            new = _remap_tags(old, merge_map, delete_set)
            if not new:
                new = _guess_tags(row["surface"], row["truth"])
            if new == old:
                continue
            conn.execute(
                "UPDATE puzzles SET tags = ? WHERE id = ?",
                (_tags_to_db(new), row["id"]),
            )
            updated += 1
        conn.commit()
    return {"ok": True, "updated": updated, "tags": list_tags()}


def rename_tag(old: str, new: str) -> dict:
    old = (old or "").strip()
    new = (new or "").strip()
    if not old or not new:
        raise ValueError("旧标签与新标签均不能为空")
    if old == new:
        return {"ok": True, "updated": 0, "tags": list_tags()}
    return apply_tag_ops({old: new}, [])


def delete_tag(name: str) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("标签名不能为空")
    return apply_tag_ops({}, [name])


def add_one(surface: str, truth: str, tags=None) -> bool:
    p = _normalize_puzzle({"surface": surface, "truth": truth, "tags": tags})
    if not p:
        return False
    if not p["tags"]:
        p["tags"] = _guess_tags(p["surface"], p["truth"])
    with _lock:
        conn = _connect()
        ok = _insert_puzzle(conn, p)
        if ok:
            conn.commit()
        return ok


def update_at(index: int, surface: str = None, truth: str = None, tags=None) -> bool:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT id, surface, truth, tags FROM puzzles WHERE id = ?",
            (index,),
        ).fetchone()
        if row is None:
            return False
        new_surface = (surface if surface is not None else row["surface"]).strip()
        new_truth = (truth if truth is not None else row["truth"]).strip()
        if not new_surface or not new_truth:
            return False
        new_tags = (
            _normalize_tags(tags)
            if tags is not None
            else _tags_from_db(row["tags"])
        )
        if not new_tags:
            new_tags = _guess_tags(new_surface, new_truth)
        try:
            conn.execute(
                "UPDATE puzzles SET surface = ?, truth = ?, tags = ? WHERE id = ?",
                (new_surface, new_truth, _tags_to_db(new_tags), index),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
