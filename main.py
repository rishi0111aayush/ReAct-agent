import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agent import run_agent

app = FastAPI(title="MiniGPT")
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.post("/chat")
def chat(req: ChatRequest):
    def event_stream():
        for event in run_agent(req.message, req.history):
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
