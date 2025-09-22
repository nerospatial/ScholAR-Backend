from __future__ import annotations
from typing import Dict, Tuple

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.services.identity.email_verification import issue_code, verify_code
from app.utils.otp_utils import normalize_email_address
from app.utils.validators import validate_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def process_registration_request(email: str, password: str, db: Session) -> Tuple[int, Dict]:
    """Handle registration request - validate data and send verification code"""
    try:
        normalized_email = normalize_email_address(email)
    except ValueError:
        return 400, {
            "error": "invalid_email",
            "message": "Invalid email format"
        }
    
    is_valid, validation_message = validate_password(password)
    if not is_valid:
        return 400, {
            "error": "invalid_password",
            "message": validation_message
        }
    
    existing_user = find_user_by_email(normalized_email, db)
    if existing_user:
        return 409, {
            "error": "email_exists",
            "message": "Email already registered"
        }
    
    hashed_password = hash_password(password)
    create_pending_user(normalized_email, hashed_password, db)
    
    verification_response = await issue_code(normalized_email)
    
    return 200, {
        "status": "ok",
        "message": "Verification code sent"
    }

def complete_registration_verification(email: str, verification_code: str, db: Session) -> Tuple[int, Dict]:
    """Complete registration after email verification - activate user and return tokens"""
    verification_successful, verification_result = verify_code(email, verification_code, db)
    
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
    
    activate_pending_user(email, db)
    
    return 200, verification_result

def find_user_by_email(email: str, db: Session) -> User | None:
    """Find user by email including pending users"""
    return db.query(User).filter(User.email == email).first()

def create_pending_user(email: str, hashed_password: str, db: Session) -> User:
    """Create user in pending verification state"""
    pending_user = User(
        email=email,
        hashed_password=hashed_password,
        is_verified=False,
        is_deleted=False
    )
    db.add(pending_user)
    db.commit()
    db.refresh(pending_user)
    return pending_user

def activate_pending_user(email: str, db: Session) -> None:
    """Mark user as verified after successful email verification"""
    user = find_user_by_email(email, db)
    if user:
        user.is_verified = True
        db.commit()

def hash_password(password: str) -> str:
    """Generate password hash using bcrypt"""
    return pwd_context.hash(password)