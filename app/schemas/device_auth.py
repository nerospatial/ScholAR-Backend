from pydantic import BaseModel, field_validator
from typing import Optional


class DeviceRegisterRequest(BaseModel):
    user_id: int


class DeviceRegisterResponse(BaseModel):
    registration_token: str
    access_token: str
    expires_in: int


class DeviceVerifyRequest(BaseModel):
    user_id: int
    registration_token: str
    access_token: str
    hardware_id: Optional[str] = None


class DeviceVerifyResponse(BaseModel):
    user_id: int
    access_token: str
    refresh_token: str
    expires_in: int