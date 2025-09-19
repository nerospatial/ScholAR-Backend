from fastapi import APIRouter, HTTPException
import secrets

from app.db.database import db_dependency
from app.services.identity import device_auth
from app.schemas.device_auth import (
	DeviceOtpRequest,
	DeviceOtpResponse,
	DeviceAuthRequest,
	DeviceAuthResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/device/otp", response_model=DeviceOtpResponse)
async def request_device_otp(req: DeviceOtpRequest, db: db_dependency):
	status_code, result = await device_auth.initiate_device_authentication(req.user_id, db)
	if status_code == 200:
		return result
	raise HTTPException(status_code=status_code, detail=result)


@router.post("/device", response_model=DeviceAuthResponse)
def verify_device_auth(req: DeviceAuthRequest, db: db_dependency):
	if not req.device_id:
		raise HTTPException(status_code=400, detail={"error": "missing_device_id", "message": "device_id is required"})
	device_id = req.device_id
	status_code, result = device_auth.complete_device_authentication(
		req.user_id, req.otp, req.accessToken, device_id, db
	)
	if status_code == 200:
		return result
	raise HTTPException(status_code=status_code, detail=result)
