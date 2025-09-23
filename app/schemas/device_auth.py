
from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID

class DeviceRegisterRequest(BaseModel):
    user_id: UUID


class DeviceRegisterResponse(BaseModel):
    registration_token: int  # 6-digit code as int
    access_token: str
    expires_in: int


class DeviceVerifyRequest(BaseModel):
    user_id: UUID
    registration_token: int  # 6-digit code as int
    access_token: str
    hardware_id: Optional[str] = None

class DeviceVerifyResponse(BaseModel):
    user_id: UUID
    access_token: str
    refresh_token: str
    expires_in: int