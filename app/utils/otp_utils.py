import hmac
import hashlib
import os
import secrets
from typing import Tuple

PEPPER = os.getenv("SESSION_SECRET_KEY") or os.getenv("SECRET_KEY") or secrets.token_hex(32)

def normalize_email_address(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValueError("malformed email")
    return email

def hash_otp_code_with_salt(code: str, salt: str) -> str:
    if not (isinstance(code, str) and code.isdigit() and len(code) == 6):
        raise ValueError("code must be 6 digits")
    msg = (salt + code).encode()
    return hmac.new(PEPPER.encode(), msg, hashlib.sha256).hexdigest()

def is_otp_expired(created_at_s: int, ttl_seconds: int) -> bool:
    from app.infra.cache.otp_store import now_s
    return (now_s() - created_at_s) >= ttl_seconds

def generate_six_digit_otp_with_hash() -> Tuple[str, str, str]:
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    code_hash = hash_otp_code_with_salt(code, salt)
    return code, salt, code_hash

