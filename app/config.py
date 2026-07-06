"""
config.py — Centralised settings for Boozo.ai.

All environment variables and application constants live here.
Import from this module instead of calling os.getenv() directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Auth ──────────────────────────────────────────────────────────────────────
SECRET_KEY           = os.getenv("SECRET_KEY", "change-me-in-production")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# ── LLM API keys ──────────────────────────────────────────────────────────────
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

# ── LLM API URLs ──────────────────────────────────────────────────────────────
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
OLLAMA_URL   = "http://localhost:11434/api/generate"

# ── Default model names ───────────────────────────────────────────────────────
GROQ_MODEL      = "llama-3.3-70b-versatile"
VISION_MODEL    = "meta-llama/llama-4-scout-17b-16e-instruct"
GEMINI_MODEL    = "gemini-2.0-flash"
CEREBRAS_MODEL  = "gpt-oss-120b"
OLLAMA_MODEL    = "llama3.2"

# ── Agent ─────────────────────────────────────────────────────────────────────
MAX_ITERATIONS  = 5
NUM_CTX         = 8_192
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS  = 2_048

# ── Database ──────────────────────────────────────────────────────────────────
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_PATH  = os.path.join(DATA_DIR, "boozo.db")

# ── Redis / cache ─────────────────────────────────────────────────────────────
REDIS_URL      = os.getenv("REDIS_URL", "redis://localhost:6379")
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "30"))
