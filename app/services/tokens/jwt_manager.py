import os
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

class JWTManager:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,   # 1 hour
        refresh_token_expire_days: int = 7,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

    # create tokens

    def create_access_token(self, data: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        to_encode = {
            **data,
            "type": "access",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.access_token_expire_minutes)).timestamp()),
        }
        if self.issuer: to_encode["iss"] = self.issuer
        if self.audience: to_encode["aud"] = self.audience
        # add jti if not provided
        to_encode.setdefault("jti", secrets.token_urlsafe(16))
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        to_encode = {
            **data,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(days=self.refresh_token_expire_days)).timestamp()),
        }
        if self.issuer: to_encode["iss"] = self.issuer
        if self.audience: to_encode["aud"] = self.audience
        # refresh tokens should always have a unique jti for rotation/revocation
        to_encode.setdefault("jti", secrets.token_urlsafe(24))
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    # decode tokens

    def decode_access_token(self, token: str) -> Dict[str, Any]:
        payload = self._decode(token)
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Wrong token type")
        return payload

    def decode_refresh_token(self, token: str) -> Dict[str, Any]:
        payload = self._decode(token)
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Wrong token type")
        return payload

    # Back-compat with your existing code that calls verify_token(...)
    def decode_token(self, token: str) -> Dict[str, Any]:
        return self._decode(token)

    # internal decode helper
    def _decode(self, token: str) -> Dict[str, Any]:
        options = {
            "require": ["exp", "iat", "nbf", "type", "sub", "jti"],
        }
        audience = self.audience or None
        issuer = self.issuer or None
        return jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            audience=audience,
            issuer=issuer,
            options=options,
        )
