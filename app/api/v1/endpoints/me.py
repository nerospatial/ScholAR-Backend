from fastapi import APIRouter, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, Annotated
import jwt

from app.db.database import SessionLocal
from app.services.tokens.token_utils import verify_access_token
from app.models.user import User
from app.models.google_user import GoogleUser

from pydantic import BaseModel
from uuid import UUID

router = APIRouter(tags=["user"])

class UserProfile(BaseModel):
    id: UUID
    email: str
    username: Optional[str] = None
    is_verified: bool
    auth_type: str  # "email" or "google"
    class Config:
        from_attributes = True

@router.get("/me", response_model=UserProfile)
def get_user_profile(authorization: Annotated[str, Header()]):
    """Get current user profile information"""
    # Create database session manually
    db = SessionLocal()
    
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )

        token = authorization.split(" ")[1]

        # Verify the access token using existing token utils
        payload = verify_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )

        # Try to find user in regular users table first
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return UserProfile(
                id=user.id,
                email=user.email,
                username=user.email.split('@')[0],  # Extract username from email
                is_verified=user.is_verified,
                auth_type="email"
            )

        # Try to find user in Google users table
        google_user = db.query(GoogleUser).filter(GoogleUser.id == user_id).first()
        if google_user:
            return UserProfile(
                id=google_user.id,
                email=google_user.email,
                username=google_user.username,
                is_verified=True,  # Google users are always verified
                auth_type="google"
            )

        # User not found in either table
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )
    finally:
        db.close()