from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from app.utils.validators import validate_password, validate_passwords_match

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    
    @validator('password')
    def validate_password_requirements(cls, v):
        is_valid, message = validate_password(v)
        if not is_valid:
            raise ValueError(message)
        return v
    
    @validator('confirm_password')
    def validate_passwords_match_field(cls, v, values):
        if 'password' in values:
            is_match, message = validate_passwords_match(values['password'], v)
            if not is_match:
                raise ValueError(message)
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_orm = True