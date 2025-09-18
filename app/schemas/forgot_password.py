from pydantic import BaseModel, EmailStr, validator, field_validator
from app.utils.validators import validate_password, validate_passwords_match

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str
    confirm_new_password: str
    
    @field_validator('new_password')
    def validate_new_password_requirements(cls, v):
        is_valid, message = validate_password(v)
        if not is_valid:
            raise ValueError(message)
        return v
    
    @field_validator('confirm_new_password')
    def validate_passwords_match_field(cls, v, values):
        if 'new_password' in values:
            is_match, message = validate_passwords_match(values['new_password'], v)
            if not is_match:
                raise ValueError(message)
        return v

class ForgotPasswordResponse(BaseModel):
    status: str
    message: str

class ResetPasswordResponse(BaseModel):
    status: str
    message: str