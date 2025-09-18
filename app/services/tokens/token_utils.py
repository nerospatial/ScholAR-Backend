from .jwt_manager import JWTManager
from typing import Dict, Any, Tuple
import os

# Config via env so Android's expected 3600s lines up with backend
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
JWT_ALGORITHM = os.getenv("JWT_ALG", "HS256")
JWT_SECRET_KEY = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "dev_secret_change_me")
JWT_ISSUER = os.getenv("JWT_ISS")
JWT_AUDIENCE = os.getenv("JWT_AUD")

jwt_token_manager = JWTManager(
    secret_key=JWT_SECRET_KEY,
    algorithm=JWT_ALGORITHM,
    access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=REFRESH_TOKEN_EXPIRE_DAYS,
    issuer=JWT_ISSUER,
    audience=JWT_AUDIENCE,
)

def generate_user_tokens(user_id: str) -> Dict[str, str]:
    """Generate access and refresh tokens for authenticated user"""
    access_token = jwt_token_manager.create_access_token({"sub": user_id})
    refresh_token = jwt_token_manager.create_refresh_token({"sub": user_id})
    return {"access_token": access_token, "refresh_token": refresh_token}

def verify_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode access token payload"""
    return jwt_token_manager.decode_access_token(token)

def verify_refresh_token(token: str) -> Dict[str, Any]:
    """Verify and decode refresh token payload"""
    return jwt_token_manager.decode_refresh_token(token)

def create_new_token_pair_from_refresh(old_refresh_token: str) -> Tuple[str, str, Dict[str, Any]]:
    """
    Rotate refresh token and create new token pair.
    Returns (new_access_token, new_refresh_token, old_token_payload).
    Caller should revoke old_token_payload['jti'] to prevent reuse.
    """
    old_payload = jwt_token_manager.decode_refresh_token(old_refresh_token)
    new_refresh_token = jwt_token_manager.create_refresh_token({"sub": old_payload["sub"]})
    new_access_token = jwt_token_manager.create_access_token({"sub": old_payload["sub"]})
    return new_access_token, new_refresh_token, old_payload
