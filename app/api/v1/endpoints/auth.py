from fastapi import APIRouter, Depends, HTTPException
from app.db.database import db_dependency
from app.schemas.user import UserCreate, EmailVerification, UserLogin, UserOut
from app.services.auth import signup, verify_code, authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
async def signup_route(user_in: UserCreate):
    return await signup(user_in)

@router.post("/verify", response_model=UserOut)
def verify_route(verification: EmailVerification, db: db_dependency):
    success, user_or_msg = verify_code(str(verification.email), verification.code, db)
    if not success:
        raise HTTPException(status_code=400, detail=user_or_msg)
    return user_or_msg

@router.post("/login", response_model=UserOut)
def login_route(user_in: UserLogin, db: db_dependency):
    user = authenticate_user(str(user_in.email), user_in.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials.")
    return user