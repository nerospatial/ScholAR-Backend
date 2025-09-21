# app/services/identity/email_verification.py
from __future__ import annotations

import hmac
import os
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.infra.cache.otp_store import otp_store
from app.infra.email.sender import EmailSender
from app.models.user import User
from app.services.tokens.token_utils import generate_user_tokens
from app.utils.otp_utils import (
    normalize_email_address,
    hash_otp_code_with_salt,
    is_otp_expired,
    generate_six_digit_otp_with_hash
)

CODE_TTL_S = int(os.getenv("CODE_TTL_SECONDS", str(10 * 60)))
MAX_VERIFY_ATTEMPTS = int(os.getenv("MAX_VERIFY_ATTEMPTS", "3"))
MAX_RESEND_ATTEMPTS = int(os.getenv("MAX_RESEND_ATTEMPTS", "3"))
RESEND_COOLDOWN_S = int(os.getenv("RESEND_COOLDOWN_SECONDS", "60"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
TOKEN_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "dev_secret_change_me"


async def issue_code(email: str, *, sender: Optional[EmailSender] = None) -> Dict:
    email_normalized = normalize_email_address(email)
    sender = sender or EmailSender()

    code, salt, code_hash = generate_six_digit_otp_with_hash()
    otp_store.set(email_normalized, code_hash, salt)

    body = f"Your ScholAR verification code is {code}. It expires in {CODE_TTL_S//60} minutes."
    await sender.send_verification_code(email_normalized, subject="Your ScholAR verification code", body=body)

    return {
        "status": "ok",
        "message": "Verification code sent",
        "cooldownSeconds": RESEND_COOLDOWN_S,
        "maxResendAttempts": MAX_RESEND_ATTEMPTS,
    }

def verify_code(email: str, code: str, db: Session) -> Tuple[bool, Dict]:
    try:
        email_normalized = normalize_email_address(email)
    except Exception:
        return False, {"error": "bad_request", "message": "Malformed email"}

    rec = otp_store.get(email_normalized)
    if not rec:
        return False, {"error": "invalid_code", "message": "The verification code is invalid or expired"}

    if rec.used:
        return False, {"error": "code_gone", "message": "The verification code has already been used"}

    if is_otp_expired(rec.created_at_s, CODE_TTL_S):
        otp_store.invalidate(email_normalized)
        return False, {"error": "code_gone", "message": "The verification code has expired"}

    if rec.attempts >= MAX_VERIFY_ATTEMPTS:
        return False, {"error": "too_many_attempts", "message": "Too many failed attempts. Try again later"}

    try:
        expected = rec.code_hash
        actual = hash_otp_code_with_salt(code, rec.salt)
    except Exception:
        return False, {"error": "bad_request", "message": "Code must be 6 digits"}

    if not hmac.compare_digest(expected, actual):
        attempts = otp_store.inc_attempts(email_normalized)
        if attempts >= MAX_VERIFY_ATTEMPTS:
            return False, {"error": "too_many_attempts", "message": "Too many failed attempts. Try again later"}
        return False, {"error": "invalid_code", "message": "The verification code is invalid or expired"}

    otp_store.mark_used(email_normalized)
    otp_store.invalidate(email_normalized)
    
    try:
        token_payload = generate_user_authentication_tokens(db, email_normalized)
    except LookupError:
        return False, {"error": "user_not_found", "message": "User not found for this email"}

    return True, token_payload

async def resend_code(email: str, *, sender: Optional[EmailSender] = None):
    email_normalized = normalize_email_address(email)
    sender = sender or EmailSender()

    allowed, retry_after = otp_store.can_resend(email_normalized, MAX_RESEND_ATTEMPTS, RESEND_COOLDOWN_S)
    if not allowed:
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(int(retry_after))
        message = (
            "You have hit the resend rate limit. Please wait before requesting another code.\n\n"
            "Need help? Contact support@scholar-glasses.com."
        ) if retry_after else (
            "Resend limit reached. Try again later.\n\nNeed help? Contact support@scholar-glasses.com."
        )
        return (
            False,
            {
                "error": "rate_limited",
                "message": message,
            },
            headers,
        )

    code, salt, code_hash = generate_six_digit_otp_with_hash()
    otp_store.mark_resend_and_update_code_hash(email_normalized, code_hash, salt)

    subject = "Your ScholAR verification code-after resend"
    body = (
        f"Your code is {code}. It expires in {CODE_TTL_S//60} minutes. If you didn't request this, ignore.\n\n"
        "Need help? Contact support@scholar-glasses.com."
    )
    await sender.send_verification_code(email_normalized, subject=subject, body=body)

    rec = otp_store.get(email_normalized)
    resend_count = rec.resend_count if rec else 0
    attempts_remaining = max(0, MAX_RESEND_ATTEMPTS - resend_count)
    return True, {
        "status": "ok",
        "message": "Verification code resent",
        "cooldownSeconds": RESEND_COOLDOWN_S,
        "attemptsRemaining": attempts_remaining
    }, {}

def generate_user_authentication_tokens(db: Session, email: str) -> Dict:
    """Generate tokens for verified user"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise LookupError("user_not_found")
    
    tokens = generate_user_tokens(str(user.id))
    return {
        "accessToken": tokens["access_token"],
        "refreshToken": tokens["refresh_token"],
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds for Android
    }
