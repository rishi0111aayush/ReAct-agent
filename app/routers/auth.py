"""
routers/auth.py — Google OAuth 2.0 authentication routes.
"""
from urllib.parse import quote as url_quote

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

import app.db as db
from app.oauth_client import oauth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
async def auth_google(request: Request):
    redirect_uri = str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    try:
        token     = await oauth.google.authorize_access_token(request)
        userinfo  = token.get("userinfo") or await oauth.google.userinfo(token=token)
        google_id = userinfo["sub"]
        db.upsert_user(
            google_id=google_id,
            email=userinfo.get("email", ""),
            name=userinfo.get("name", ""),
            avatar=userinfo.get("picture", ""),
        )
        request.session["user_id"] = google_id
        return RedirectResponse(url="/")
    except Exception as e:
        return RedirectResponse(url=f"/?auth_error={url_quote(str(e))}")


@router.get("/me")
def auth_me(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/logout")
def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}
