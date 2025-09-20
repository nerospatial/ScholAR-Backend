from pydantic import BaseModel, field_validator
from typing import Optional

class DeviceOtpRequest(BaseModel):
    user_id: int

class DeviceOtpResponse(BaseModel):
    registrationToken: int
    accessToken: str
    expiresIn: int

class DeviceAuthRequest(BaseModel):
    user_id: int
    registrationToken: int
    accessToken: str
    device_id: Optional[str] = None

    @field_validator("registrationToken")
    def validate_registration_token(cls, v):
        if not (isinstance(v, int) and 100000 <= v <= 999999):
            raise ValueError("Registration token must be a 6-digit integer")
        return v

class DeviceAuthResponse(BaseModel):
    userId: int
    accessToken: str
    refreshToken: str
    expiresIn: int
