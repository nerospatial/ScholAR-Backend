
from fastapi import APIRouter, Depends, HTTPException, status
from app.db.database import db_dependency
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.schemas.verify_code import VerifyRequest, TokenResponse
from app.schemas.resend_code import ResendRequest, ResendResponse
from app.services.auth import signup, verify_code, authenticate_user
from app.services.identity.email_verification import verify_code as verify_email_code, resend_code as resend_verification_code


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
async def signup_route(user_in: UserCreate):
    return await signup(user_in)


@router.post("/verify", response_model=TokenResponse)
def verify_code_route(req: VerifyRequest, db: db_dependency):
    success, result = verify_email_code(str(req.email), req.code, db)
    if success:
        return result
    error_map = {
        "bad_request": status.HTTP_400_BAD_REQUEST,
        "invalid_code": status.HTTP_401_UNAUTHORIZED,
        "code_gone": status.HTTP_410_GONE,
        "too_many_attempts": status.HTTP_423_LOCKED,
        "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
        "user_not_found": status.HTTP_404_NOT_FOUND,
    }
    code = result.get("error", "server_error")
    http_code = error_map.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(status_code=http_code, detail={"code": http_code, "message": result.get("message")})



@router.post("/resend", response_model=ResendResponse)
async def resend_code_route(req: ResendRequest):
    try:
        ok, result, headers = await resend_verification_code(str(req.email))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "message": str(e)})
    if ok:
        return result
    error_map = {
        "bad_request": status.HTTP_400_BAD_REQUEST,
        "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    code = result.get("error", "server_error")
    http_code = error_map.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(status_code=http_code, detail={"code": http_code, "message": result.get("message")}, headers=headers or {})

@router.post("/login", response_model=UserOut)
def login_route(user_in: UserLogin, db: db_dependency):
    user = authenticate_user(str(user_in.email), user_in.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials.")
    return user