from pydantic import BaseModel, EmailStr, Field

class VerifyRequest(BaseModel):
	email: EmailStr
	code: str = Field(pattern=r"^\d{6}$")

class VerifyResponse(BaseModel):
	access_token: str
	refresh_token: str
	expires_in: int
