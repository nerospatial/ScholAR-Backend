from .jwt_manager import JWTManager
from typing import Dict, Any, Tuple
import os, secrets, jwt

# Config via env so Android's expected 3600s lines up with backend
ACCESS_MIN = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "dev_secret_change_me")
JWT_ISS = os.getenv("JWT_ISS")  # optional
JWT_AUD = os.getenv("JWT_AUD")  # optional

_manager = JWTManager(
    secret_key=JWT_SECRET,
    algorithm=JWT_ALG,
    access_token_expire_minutes=ACCESS_MIN,
    refresh_token_expire_days=REFRESH_DAYS,
    issuer=JWT_ISS,
    audience=JWT_AUD,
)

def generate_tokens(user_id: str, secret_key: str = JWT_SECRET) -> Dict[str, str]:
    access_token = _manager.create_access_token({"sub": user_id})
    refresh_token = _manager.create_refresh_token({"sub": user_id})
    return {"access_token": access_token, "refresh_token": refresh_token}

def verify_token(token: str, secret_key: str = JWT_SECRET) -> Dict[str, Any]:
    return _manager.decode_token(token)

# Helpers for /auth/refresh:
def decode_refresh(token: str) -> Dict[str, Any]:
    return _manager.decode_refresh_token(token)

def rotate_refresh_token(old_refresh: str) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (new_refresh_token, old_payload).
    NOTE: you should mark old_payload['jti'] as 'used'/'revoked' in your store to prevent reuse.
    """
    payload = _manager.decode_refresh_token(old_refresh)
    new_refresh = _manager.create_refresh_token({"sub": payload["sub"]})
    return new_refresh, payload
