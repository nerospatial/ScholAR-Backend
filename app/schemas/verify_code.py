from pydantic import BaseModel, EmailStr, constr

class VerifyRequest(BaseModel):
	email: EmailStr
	code: constr(regex=r"^\d{6}$")

class VerifyResponse(BaseModel):
	accessToken: str
	refreshToken: str
	expiresIn: int
