"""
deps.py — Shared FastAPI dependency functions.
"""
from fastapi import Request, HTTPException
import app.db as db


def get_current_user(request: Request) -> dict | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    return db.get_user(uid)


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
