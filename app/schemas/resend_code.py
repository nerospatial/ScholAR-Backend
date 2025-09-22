from pydantic import BaseModel, EmailStr
from typing import Optional

class ResendRequest(BaseModel):
	email: EmailStr

class ResendResponse(BaseModel):
	status: str
	message: str
	cooldown_seconds: int
	attempts_remaining: Optional[int] = None
