from fastapi import APIRouter, HTTPException, status
from app.db.database import db_dependency
from app.schemas.user import UserCreate, UserLogin
from app.schemas.verify_code import VerifyRequest, VerifyResponse
from app.schemas.resend_code import ResendRequest, ResendResponse
from app.schemas.forgot_password import ForgotPasswordRequest, ResetPasswordRequest, ForgotPasswordResponse, ResetPasswordResponse
from app.services.identity.registration import process_registration_request, complete_registration_verification
from app.services.identity.login import process_login_request, complete_login_verification
from app.services.identity.forgot_password import initiate_password_reset_request, complete_password_reset_verification
from app.services.identity.email_verification import resend_code as resend_verification_code
from app.services.tokens.token_utils import create_new_token_pair_from_refresh
from app.schemas.token_refresh import TokenRefreshRequest, TokenRefreshResponse


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
async def signup_route(user_in: UserCreate, db: db_dependency):
    status_code, result = await process_registration_request(str(user_in.email), user_in.password, db)
    if status_code == 200:
        return result
    raise HTTPException(status_code=status_code, detail=result)


@router.post("/verify", response_model=VerifyResponse)
def verify_code_route(req: VerifyRequest, db: db_dependency):
    # For signup verification - complete registration
    status_code, result = complete_registration_verification(str(req.email), req.code, db)
    if status_code == 200:
        return result
    
    # If registration verification fails, try login verification
    if status_code in [401, 410, 423]:
        login_status_code, login_result = complete_login_verification(str(req.email), req.code, db)
        if login_status_code == 200:
            return login_result
        # Return the original registration error if login also fails
    
    raise HTTPException(status_code=status_code, detail=result)



@router.post("/resend", response_model=ResendResponse)
async def resend_code_route(req: ResendRequest):
    try:
        success, result, headers = await resend_verification_code(str(req.email))
        if success:
            return result
        
        # Map service errors to HTTP status codes
        error_code = result.get("error", "server_error")
        if error_code == "rate_limited":
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            
        raise HTTPException(
            status_code=status_code, 
            detail=result, 
            headers=headers or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"error": "server_error", "message": str(e)}
        )


@router.post("/login")
async def login_request_code(user_in: UserLogin, db: db_dependency):
    status_code, result = await process_login_request(str(user_in.email), user_in.password, db)
    if status_code == 200:
        return result
    raise HTTPException(status_code=status_code, detail=result)


@router.post("/forgot", response_model=ForgotPasswordResponse)
async def forgot_password_route(req: ForgotPasswordRequest, db: db_dependency):
    """Request password reset code"""
    status_code, result = await initiate_password_reset_request(str(req.email), db)
    return result  # Always return 200 per auth spec


@router.post("/reset", response_model=ResetPasswordResponse)
async def reset_password_route(req: ResetPasswordRequest, db: db_dependency):
    """Reset password with verification code"""
    status_code, result = complete_password_reset_verification(str(req.email), req.code, req.new_password, db)
    if status_code == 200:
        return result
    raise HTTPException(status_code=status_code, detail=result)

@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(req: TokenRefreshRequest):
    try:
        new_access, new_refresh = create_new_token_pair_from_refresh(req.refreshToken)
        return TokenRefreshResponse(
            accessToken=new_access,
            refreshToken=new_refresh,
            expiresIn=300,  
        )
    except Exception as e:
        # TODO: hook revocation list & abuse protection here
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_refresh", "message": str(e)}
        )