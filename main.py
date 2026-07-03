"""
main.py — FastAPI entry point for Boozo.ai.

Routes:
  GET  /        → serves static/index.html
  POST /chat    → SSE stream from the ReAct agent
  GET  /health  → liveness check
"""
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agent import run_agent

app = FastAPI(title="Boozo.ai")
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    image: str | None = None
    image_mime: str | None = None
    selected_model: str | None = None  # e.g. "groq:llama-3.3-70b-versatile" or "ollama:llama3.2"


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.post("/chat")
def chat(req: ChatRequest):
    def event_stream():
        for event in run_agent(req.message, req.history, req.image, req.image_mime, req.selected_model):
            data = json.dumps(event)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
