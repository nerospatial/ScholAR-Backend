from pydantic import BaseModel, EmailStr, Field


class VerifyRequest(BaseModel):
	email: EmailStr
	code: int = Field(ge=100000, le=999999, description="6-digit OTP code as integer")

class VerifyResponse(BaseModel):
	access_token: str
	refresh_token: str
	expires_in: int
