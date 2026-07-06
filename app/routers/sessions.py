"""
routers/sessions.py — Chat session and message history API.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import app.db as db
from app.deps import require_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def list_sessions(user: dict = Depends(require_user)):
    return db.get_sessions(user["id"])


@router.post("")
def create_session(user: dict = Depends(require_user)):
    sid = db.create_session(user["id"])
    return {"id": sid, "title": "New Chat"}


class RenameBody(BaseModel):
    title: str


@router.patch("/{session_id}")
def rename_session(
    session_id: str,
    body: RenameBody,
    user: dict = Depends(require_user),
):
    db.rename_session(session_id, user["id"], body.title.strip() or "New Chat")
    return {"ok": True}


@router.delete("/{session_id}")
def delete_session(session_id: str, user: dict = Depends(require_user)):
    db.delete_session(session_id, user["id"])
    return {"ok": True}


@router.get("/{session_id}")
def get_session(session_id: str, user: dict = Depends(require_user)):
    messages = db.get_messages(session_id, user["id"])
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": messages}


class SaveMessageBody(BaseModel):
    role:    str
    content: str


@router.post("/{session_id}/message")
def save_message(
    session_id: str,
    body: SaveMessageBody,
    user: dict = Depends(require_user),
):
    if db.get_messages(session_id, user["id"]) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    db.add_message(session_id, body.role, body.content)
    db.auto_title(session_id, user["id"])
    return {"ok": True}
