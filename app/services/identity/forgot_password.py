from __future__ import annotations
from typing import Dict, Tuple

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.services.identity.email_verification import issue_code, verify_code
from app.utils.otp_utils import normalize_email_address
from app.utils.validators import validate_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def initiate_password_reset_request(email: str, db: Session) -> Tuple[int, Dict]:
    """Handle forgot password request - always return success to prevent user enumeration"""
    try:
        normalized_email = normalize_email_address(email)
    except ValueError:
        return 200, {
            "status": "ok",
            "message": "If an account exists, a reset email has been sent."
        }
    
    existing_user = find_verified_user_by_email(normalized_email, db)
    if existing_user:
        await issue_code(normalized_email)
    
    return 200, {
        "status": "ok", 
        "message": "If an account exists, a reset email has been sent."
    }

def complete_password_reset_verification(email: str, verification_code: int, new_password: str, db: Session) -> Tuple[int, Dict]:
    """Complete password reset after email verification"""
    try:
        normalized_email = normalize_email_address(email)
    except ValueError:
        return 400, {
            "error": "invalid_email",
            "message": "Invalid email format"
        }
    
    is_valid, validation_message = validate_password(new_password)
    if not is_valid:
        return 400, {
            "error": "invalid_password", 
            "message": validation_message
        }
    
    verification_successful, verification_result = verify_code(normalized_email, verification_code, db)
    if not verification_successful:
        error_code = verification_result.get("error")
        
        if error_code == "invalid_code":
            return 401, verification_result
        elif error_code == "code_gone" or error_code == "code_expired":
            return 410, verification_result
        elif error_code == "too_many_attempts":
            return 423, verification_result
        elif error_code == "bad_request":
            return 400, verification_result
        elif error_code == "user_not_found":
            return 401, {
                "error": "invalid_code",
                "message": "Invalid verification code"
            }
        else:
            return 401, verification_result
    
    update_user_password(normalized_email, new_password, db)
    
    return 200, {
        "status": "ok",
        "message": "Password reset successfully"
    }

def find_verified_user_by_email(email: str, db: Session) -> User | None:
    """Find verified active user by email"""
    return db.query(User).filter(
        User.email == email,
        User.is_verified == True,
        User.is_deleted == False
    ).first()

def update_user_password(email: str, new_password: str, db: Session) -> None:
    """Update user password with new hash"""
    user = find_verified_user_by_email(email, db)
    if user:
        user.hashed_password = pwd_context.hash(new_password)
        db.commit()
