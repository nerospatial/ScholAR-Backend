from fastapi import APIRouter, HTTPException
from app.db.database import db_dependency
from app.services.identity import device_auth
from app.schemas.device_auth import DeviceRegisterResponse, DeviceRegisterRequest, DeviceVerifyRequest,DeviceVerifyResponse

router = APIRouter(prefix="/auth", tags=["auth"])

	

@router.post("/device/register", response_model=DeviceRegisterResponse)
async def register_device(req: DeviceRegisterRequest, db: db_dependency):
	status_code, result = await device_auth.initiate_device_authentication(req.user_id, db)
	if status_code == 200:
		return result
	raise HTTPException(status_code=status_code, detail=result)

@router.post("/device/verify", response_model=DeviceVerifyResponse)
async def verify_device(req: DeviceVerifyRequest, db: db_dependency):
	if req.hardware_id is None:
		raise HTTPException(status_code=400, detail={"error": "missing_hardware_id", "message": "hardware_id is required"})
	status_code, result = device_auth.complete_device_authentication(
		req.user_id, req.registration_token, req.access_token, req.hardware_id, db
	)
	if status_code == 200:
		return result
	raise HTTPException(status_code=status_code, detail=result)


