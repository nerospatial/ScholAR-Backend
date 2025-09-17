from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
import re

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        if not re.search("[a-zA-Z]", v):
            raise ValueError('Password must contain at least one letter')
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