"""
routers/chat.py — POST /chat — SSE streaming endpoint.
"""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import app.db as db
from app.cache import cache
from app.deps import get_current_user

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message:        str
    history:        list[dict] = []
    image:          str | None = None
    image_mime:     str | None = None
    selected_model: str | None = None
    session_id:     str | None = None


@router.post("/chat")
def chat(req: ChatRequest, request: Request):
    from app.agent import run_agent  # lazy import avoids startup conflict with authlib

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(req.message) > 4_000:
        raise HTTPException(status_code=400, detail="Message too long (max 4000 characters).")

    user    = get_current_user(request)
    rl_key  = user["id"] if user else request.client.host
    allowed, count = cache.check_rate_limit(rl_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({count} req/min). Please wait.",
        )

    user_id = user["id"] if user else None

    def event_stream():
        for event in run_agent(
            req.message, req.history,
            req.image, req.image_mime,
            req.selected_model,
            user_id=user_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
