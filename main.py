"""
main.py — Application entry point.

Re-exports the FastAPI app instance for uvicorn:
  uvicorn main:app --reload
  python -m uvicorn main:app --host 0.0.0.0 --port $PORT
"""
from app.main import app  # noqa: F401
