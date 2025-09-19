from pydantic import BaseModel, field_validator
from typing import Optional

class DeviceOtpRequest(BaseModel):
    user_id: int

class DeviceOtpResponse(BaseModel):
    userId: str
    otp: str
    accessToken: str
    expiresIn: int

class DeviceAuthRequest(BaseModel):
    user_id: int
    otp: str
    accessToken: str
    device_id: Optional[str] = None

    @field_validator("otp")
    def validate_otp_format(cls, v):
        if not (v.isdigit() and len(v) == 6):
            raise ValueError("OTP must be a 6-digit numeric code")
        return v

class DeviceAuthResponse(BaseModel):
    userId: str
    accessToken: str
    refreshToken: str
    expiresIn: int
