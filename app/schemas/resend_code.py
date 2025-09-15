from pydantic import BaseModel, EmailStr
from typing import Optional

class ResendRequest(BaseModel):
	email: EmailStr

class ResendResponse(BaseModel):
	status: str
	message: str
	cooldownSeconds: int
	attemptsRemaining: Optional[int] = None
