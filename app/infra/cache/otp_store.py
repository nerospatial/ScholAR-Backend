# app/infra/cache/otp_store.py
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Optional, Dict, Tuple
import time

def now_s() -> int:
    return int(time.time())

@dataclass
class OtpRecord:
    code_hash: str
    salt: str
    created_at_s: int
    used: bool = False
    attempts: int = 0
    resend_count: int = 0
    last_resend_at_s: int = 0

class InMemoryOtpStore:
    """Thread-safe in-memory OTP store keyed by normalized email."""
    def __init__(self) -> None:
        self._d: Dict[str, OtpRecord] = {}
        self._lock = RLock()

    def set(self, email: str, code_hash: str, salt: str) -> None:
        with self._lock:
            self._d[email.lower()] = OtpRecord(
                code_hash=code_hash,
                salt=salt,
                created_at_s=now_s(),
                used=False,
                attempts=0,
                resend_count=0,
                last_resend_at_s=now_s(),
            )

    def get(self, email: str) -> Optional[OtpRecord]:
        with self._lock:
            return self._d.get(email.lower())

    def invalidate(self, email: str) -> None:
        with self._lock:
            self._d.pop(email.lower(), None)

    def mark_used(self, email: str) -> None:
        with self._lock:
            rec = self._d.get(email.lower())
            if rec:
                rec.used = True

    def inc_attempts(self, email: str) -> int:
        with self._lock:
            rec = self._d.get(email.lower())
            if not rec:
                return 0
            rec.attempts += 1
            return rec.attempts

    def can_resend(self, email: str, max_resend: int, cooldown_s: int) -> Tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        with self._lock:
            rec = self._d.get(email.lower())
            if not rec:
                # no record → allow (will create a new one)
                return True, 0
            if rec.resend_count >= max_resend:
                return False, 0
            delta = now_s() - (rec.last_resend_at_s or 0)
            if delta < cooldown_s:
                return False, cooldown_s - delta
            return True, 0
        
    def mark_resend_and_update_code_hash(self, email: str, new_code_hash: str, new_salt: str) -> None:
        """Mark resend and update with new OTP code hash and salt."""
        with self._lock:
            rec = self._d.get(email.lower())
            if rec:
                # Update with new OTP data
                rec.code_hash = new_code_hash
                rec.salt = new_salt
                # Update resend tracking
                rec.resend_count += 1
                rec.last_resend_at_s = now_s()
                # Reset attempts for the new OTP
                rec.attempts = 0
                # Reset used flag since it's a new code
                rec.used = False
otp_store = InMemoryOtpStore()
