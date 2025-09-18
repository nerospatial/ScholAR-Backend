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
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 7,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        if not secret_key or secret_key == "dev_secret_change_me":
            raise ValueError("JWT secret key must be set for production use")
        
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token with user data"""
        current_time = datetime.now(timezone.utc)
        token_payload = {
            **user_data,
            "type": "access",
            "iat": int(current_time.timestamp()),
            "nbf": int(current_time.timestamp()),
            "exp": int((current_time + timedelta(minutes=self.access_token_expire_minutes)).timestamp()),
            "jti": secrets.token_urlsafe(16),
        }
        
        if self.issuer:
            token_payload["iss"] = self.issuer
        if self.audience:
            token_payload["aud"] = self.audience
            
        return jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT refresh token with user data"""
        current_time = datetime.now(timezone.utc)
        token_payload = {
            **user_data,
            "type": "refresh",
            "iat": int(current_time.timestamp()),
            "nbf": int(current_time.timestamp()),
            "exp": int((current_time + timedelta(days=self.refresh_token_expire_days)).timestamp()),
            "jti": secrets.token_urlsafe(24),  # Longer for refresh tokens
        }
        
        if self.issuer:
            token_payload["iss"] = self.issuer
        if self.audience:
            token_payload["aud"] = self.audience
            
        return jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify access token"""
        payload = self._decode_and_verify_token(token)
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Expected access token, got different type")
        return payload

    def decode_refresh_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify refresh token"""
        payload = self._decode_and_verify_token(token)
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Expected refresh token, got different type")
        return payload

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Generic token decoder - use specific methods when possible"""
        return self._decode_and_verify_token(token)

    def _decode_and_verify_token(self, token: str) -> Dict[str, Any]:
        """Internal token verification with all required claims"""
        verification_options = {
            "require": ["exp", "iat", "nbf", "type", "sub", "jti"],
        }
        
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options=verification_options,
            )
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidSignatureError:
            raise jwt.InvalidTokenError("Invalid token signature")
        except jwt.InvalidTokenError as error:
            raise jwt.InvalidTokenError(f"Token validation failed: {str(error)}")
