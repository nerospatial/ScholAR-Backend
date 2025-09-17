from __future__ import annotations
from typing import Dict, Tuple

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.services.identity.email_verification import issue_code, verify_code
from app.utils.otp_utils import normalize_email_address

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def process_login_request(email: str, password: str, db: Session) -> Tuple[int, Dict]:
    """Handle login request - verify credentials and send verification code"""
    try:
        normalized_email = normalize_email_address(email)
    except ValueError:
        return 400, {
            "error": "invalid_email",
            "message": "Invalid email format"
        }
    
    user = find_active_user_by_email(normalized_email, db)
    if not user:
        return 401, {
            "error": "invalid_credentials", 
            "message": "Invalid email or password"
        }
    
    if not verify_password(password, user.hashed_password):
        return 401, {
            "error": "invalid_credentials",
            "message": "Invalid email or password"
        }
    
    verification_response = await issue_code(normalized_email)
    
    return 200, {
        "status": "ok",
        "message": "Verification code sent"
    }

def complete_login_verification(email: str, verification_code: str, db: Session) -> Tuple[int, Dict]:
    """Complete login after email verification - return tokens"""
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
                "error": "invalid_credentials",
                "message": "Invalid email or code"
            }
        else:
            return 401, verification_result
    
    return 200, {
        "accessToken": verification_result["accessToken"],
        "refreshToken": verification_result["refreshToken"], 
        "expiresIn": verification_result["expiresIn"]
    }

def find_active_user_by_email(email: str, db: Session) -> User | None:
    """Find active user by email address"""
    return db.query(User).filter(
        User.email == email,
        User.is_deleted == False
    ).first()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)