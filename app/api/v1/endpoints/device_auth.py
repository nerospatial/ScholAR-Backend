from fastapi import APIRouter, HTTPException, Header, Path
from app.db.database import db_dependency
from app.services.identity import device_auth
from app.schemas.device_auth import (
    DeviceRegisterResponse,
    DeviceRegisterRequest,
    DeviceVerifyRequest,
    DeviceVerifyResponse,
    UserDevicesResponse,
    DeviceInfo,
)
from app.models.device import Device
from app.models.authenticated_device import AuthenticatedDevice
from uuid import UUID

router = APIRouter(prefix="/auth", tags=["auth"])



@router.post("/device/register", response_model=DeviceRegisterResponse)
async def register_device(req: DeviceRegisterRequest, db: db_dependency):
    status_code, result = await device_auth.initiate_device_authentication(req.user_id, db)
    if status_code == 200:
        return result
    raise HTTPException(status_code=status_code, detail=result)

@router.post("/device/verify", response_model=DeviceVerifyResponse)
async def verify_device(
    req: DeviceVerifyRequest,
    db: db_dependency,
    authorization: str = Header(None)
):
    if req.hardware_id is None:
        raise HTTPException(status_code=400, detail={"error": "missing_hardware_id", "message": "hardware_id is required"})
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "missing_token", "message": "Authorization header missing or invalid"})
    access_token = authorization.split(" ", 1)[1]
    status_code, result = device_auth.complete_device_authentication(
        req.user_id,
        req.registration_token,
        access_token,
        req.hardware_id,
        req.device_name,
        req.firmware_version,
        db
    )
    if status_code == 200:
        return result
    raise HTTPException(status_code=status_code, detail=result)


@router.get("/device/get-devices/{user_id}", response_model=UserDevicesResponse)
async def get_user_devices(
    user_id: UUID = Path(..., description="User ID to fetch devices for"),
    db: db_dependency = None,
    authorization: str = Header(None),
):
    # Check for Authorization header and validate token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "missing_token", "message": "Authorization header missing or invalid"})
    access_token = authorization.split(" ", 1)[1]
    try:
        payload = device_auth.jwt_token_manager.decode_access_token(access_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": str(e)})

    results = (
        db.query(Device.id, Device.device_name, Device.firmware_version)
        .join(AuthenticatedDevice, AuthenticatedDevice.device_id == Device.id)
        .filter(AuthenticatedDevice.user_id == user_id)
        .all()
    )
    devices = [
        DeviceInfo(
            device_id=device.id,
            device_name=device.device_name,
            firmware_version=device.firmware_version,
        )
        for device in results
    ]
    return UserDevicesResponse(devices=devices)