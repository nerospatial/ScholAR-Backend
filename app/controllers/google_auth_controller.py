from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.db.database import db_dependency
from app.services.google_auth import get_user_by_google_sub, create_user_from_google_info
from app.schemas.google_user import GoogleUser
from authlib.integrations.starlette_client import OAuth
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/api/v1/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL")

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

@router.get("/google/login")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)

@router.get("/google/callback")
async def auth_google(request: Request, db: db_dependency):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user_info = token.get("userinfo")
    google_user = GoogleUser(**user_info)
    user = get_user_by_google_sub(google_user.sub, db)
    if not user:
        user = create_user_from_google_info(google_user, db)
    if not user:
        raise HTTPException(status_code=500, detail="User could not be created or found.")
    return RedirectResponse(f"{FRONTEND_URL}/auth?user_id={user.id}")