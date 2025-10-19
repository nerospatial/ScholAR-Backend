from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from app.utils.validators import validate_password, validate_passwords_match

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator('password')
    def validate_password_requirements(cls, v):
        is_valid, message = validate_password(v)
        if not is_valid:
            raise ValueError(message)
        return v

    @field_validator('confirm_password')
    def validate_passwords_match_field(cls, v, info):
        if 'password' in info.data:
            is_match, message = validate_passwords_match(info.data['password'], v)
            if not is_match:
                raise ValueError(message)
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
