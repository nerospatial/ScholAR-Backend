from pydantic import BaseModel

class TokenRefreshRequest(BaseModel):
    refreshToken: str

class TokenRefreshResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int  # seconds
