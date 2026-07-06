"""
oauth_client.py — Shared Authlib OAuth instance.

Centralised here so both app/main.py and app/routers/auth.py
can reference the same registered client without circular imports.
"""
from authlib.integrations.starlette_client import OAuth
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
