"""
app/main.py — FastAPI application factory for Boozo.ai.

Creates the app, wires up middleware, mounts static files,
registers all routers, and initialises the database.
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import app.db as db
from app.config import SECRET_KEY
from app.routers import auth, sessions, chat

app = FastAPI(title="Boozo.ai")

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=60 * 60 * 24 * 30,  # 30 days
    https_only=False,
    same_site="lax",
)

# ── Static files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Database init ─────────────────────────────────────────────────────────────
db.init_db()

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)


# ── Root routes ───────────────────────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
