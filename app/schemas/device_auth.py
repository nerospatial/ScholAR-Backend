from pydantic import BaseModel, field_validator
from typing import List, Optional
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
    hardware_id: str
    device_name: str
    firmware_version: str

class DeviceVerifyResponse(BaseModel):
    user_id: UUID
    access_token: str
    refresh_token: str
    expires_in: int

class DeviceInfo(BaseModel):
    device_id: UUID
    device_name: str
    firmware_version: str

class UserDevicesResponse(BaseModel):
    devices: List[DeviceInfo]