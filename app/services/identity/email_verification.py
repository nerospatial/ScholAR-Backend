# app/services/identity/email_verification.py
from __future__ import annotations

import hmac, hashlib, os, secrets
from datetime import timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.infra.cache.otp_store import otp_store, now_s
from app.infra.email.sender import EmailSender
from app.models.user import User
from app.services.tokens.token_utils import generate_tokens

CODE_TTL_S = int(os.getenv("CODE_TTL_SECONDS", str(10 * 60)))     # 10 minutes
MAX_VERIFY_ATTEMPTS = int(os.getenv("MAX_VERIFY_ATTEMPTS", "3"))  # 3
MAX_RESEND_ATTEMPTS = int(os.getenv("MAX_RESEND_ATTEMPTS", "3"))  # 3


# HMAC pepper for code hashing
PEPPER = os.getenv("SESSION_SECRET_KEY") or os.getenv("SECRET_KEY") or secrets.token_hex(32)
# Secret for JWT (falls back to SECRET_KEY)
TOKEN_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "dev_secret_change_me"

# ---------- Helpers ----------
def _normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValueError("malformed email")
    return email

def _hash_code(code: str, salt: str) -> str:
    if not (isinstance(code, str) and code.isdigit() and len(code) == 6):
        raise ValueError("code must be 6 digits")
    msg = (salt + code).encode()
    return hmac.new(PEPPER.encode(), msg, hashlib.sha256).hexdigest()

def _expired(created_at_s: int) -> bool:
    return (now_s() - created_at_s) >= CODE_TTL_S

def _new_code():
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    code_hash = _hash_code(code, salt)
    return code, salt, code_hash

def _tokens_for_user(db: Session, email: str) -> Dict:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise LookupError("user_not_found")
    tokens = generate_tokens(str(user.id), TOKEN_SECRET)
    return {
        "accessToken": tokens["access_token"],
        "refreshToken": tokens["refresh_token"],
        "expiresIn": 3600,  # keep in sync with JWTManager default
    }

# ---------- Public API ----------
async def issue_code(email: str, *, sender: Optional[EmailSender] = None) -> Dict:
    """Create & email a fresh 6-digit code; replaces any prior record."""
    email_n = _normalize_email(email)
    sender = sender or EmailSender()

    code, salt, code_hash = _new_code()
    otp_store.set(email_n, code_hash, salt)

    body = f"Your ScholAR verification code is {code}. It expires in {CODE_TTL_S//60} minutes."
    await sender.send_verification_code(email_n, subject="Your ScholAR verification code", body=body)

    return {
        "status": "ok",
        "message": "Verification code sent",
        "cooldownSeconds": RESEND_COOLDOWN_S,
        "maxResendAttempts": MAX_RESEND_ATTEMPTS,
    }

def verify_code(email: str, code: str, db: Session) -> Tuple[bool, Dict]:
    """
    Returns:
      (True, TokenResponse) on success
      (False, error_body) on failure (route maps to HTTP code)
    """
    try:
        email_n = _normalize_email(email)
    except Exception:
        return False, {"error": "bad_request", "message": "Malformed email"}

    rec = otp_store.get(email_n)
    if not rec:
        return False, {"error": "invalid_code", "message": "The verification code is invalid or expired"}

    if rec.used:
        otp_store.invalidate(email_n)
        return False, {"error": "code_gone", "message": "The verification code has already been used"}

    if _expired(rec.created_at_s):
        otp_store.invalidate(email_n)
        return False, {"error": "code_gone", "message": "The verification code has expired"}

    if rec.attempts >= MAX_VERIFY_ATTEMPTS:
        return False, {"error": "too_many_attempts", "message": "Too many failed attempts. Try again later"}

    # Validate code
    try:
        expected = rec.code_hash
        actual = _hash_code(code, rec.salt)
    except Exception:
        # don't count malformed 6-digit failure as an auth attempt
        return False, {"error": "bad_request", "message": "Code must be 6 digits"}

    if not hmac.compare_digest(expected, actual):
        attempts = otp_store.inc_attempts(email_n)
        if attempts >= MAX_VERIFY_ATTEMPTS:
            return False, {"error": "too_many_attempts", "message": "Too many failed attempts. Try again later"}
        return False, {"error": "invalid_code", "message": "The verification code is invalid or expired"}

    # Success — one-time use
    otp_store.invalidate(email_n)
    try:
        token_payload = _tokens_for_user(db, email_n)
    except LookupError:
        return False, {"error": "user_not_found", "message": "User not found for this email"}

    return True, token_payload

async def resend_code(email: str, *, sender: Optional[EmailSender] = None):
    """
    Returns:
      (True, body, headers) on success
      (False, error_body, headers) on failure (may include Retry-After)
    """
    email_n = _normalize_email(email)
    sender = sender or EmailSender()

    allowed, retry_after = otp_store.can_resend(email_n, MAX_RESEND_ATTEMPTS, RESEND_COOLDOWN_S)
    if not allowed:
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(int(retry_after))
        return (
            False,
            {
                "error": "rate_limited",
                "message": "Please wait before requesting another code" if retry_after else "Resend limit reached. Try again later",
            },
            headers,
        )

    code, salt, code_hash = _new_code()
    otp_store.set(email_n, code_hash, salt)
    otp_store.mark_resend(email_n)

    body = f"Your ScholAR verification code is {code}. It expires in {CODE_TTL_S//60} minutes."
    await sender.send_verification_code(email_n, subject="Your ScholAR verification code", body=body)

    attempts_remaining = max(0, MAX_RESEND_ATTEMPTS - (otp_store.get(email_n).resend_count))
    return True, {
        "status": "ok",
        "message": "Verification code resent",
        "cooldownSeconds": RESEND_COOLDOWN_S,
        "attemptsRemaining": attempts_remaining
    }, {}
