"""管理端鉴权：校验 X-Admin-Key。"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

import config


def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    if not config.admin_ready():
        raise HTTPException(status_code=503, detail="管理端未配置 ADMIN_KEY")
    provided = (x_admin_key or "").strip()
    if not provided or not secrets.compare_digest(provided, config.ADMIN_KEY):
        raise HTTPException(status_code=401, detail="管理员密钥无效")
