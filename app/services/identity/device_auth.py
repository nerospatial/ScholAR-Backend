from __future__ import annotations
from typing import Dict, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.models.authenticated_device import AuthenticatedDevice
from sqlalchemy.exc import IntegrityError
from app.services.tokens.token_utils import jwt_token_manager, generate_user_tokens
from app.utils.otp_utils import generate_six_digit_otp_with_hash, hash_otp_code_with_salt
from app.infra.cache.otp_store import otp_store


DEVICE_REGISTRATION_TOKEN_TTL_S = 300  # 5 minutes


async def initiate_device_authentication(user_id: UUID, db: Session) -> Tuple[int, Dict]:
    # Verify that the user exists
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False, User.is_verified == True).first()
    if not user:
        return 404, {"error": "user_not_found", "message": "User not found"}

    # Generate registration token and persist in OTP store
    code, salt, code_hash = generate_six_digit_otp_with_hash()
    otp_store.set(str(user_id), code_hash, salt)

    # Issue short-lived registration token bound to this code
    access_token = jwt_token_manager.create_access_token(
        {"sub": str(user_id), "purpose": "device_auth", "registration_code": code}
    )

    return 200, {
        "registration_token": code,
        "access_token": access_token,
        "expires_in": DEVICE_REGISTRATION_TOKEN_TTL_S,
    }



def complete_device_authentication(
    user_id: UUID,
    registration_token: int,
    access_token: str,
    hardware_id: str,
    device_name: str,
    firmware_version: str,
    db: Session
) -> Tuple[int, Dict]:
    from app.models.hardware import Hardware
    from app.models.device import Device
    from app.models.authenticated_device import AuthenticatedDevice
    from sqlalchemy.exc import SQLAlchemyError, IntegrityError
    import uuid as uuidlib

    # Decode and validate the short-lived access token (JWT)
    try:
        payload = jwt_token_manager.decode_access_token(access_token)
    except Exception as e:
        return 401, {"error": "invalid_token", "message": str(e)}

    if payload.get("sub") != str(user_id) or payload.get("purpose") != "device_auth":
        return 401, {"error": "invalid_token", "message": "Token not valid for device authentication"}

    # Verify registration code from store using user-supplied registration_token (OTP code)
    rec = otp_store.get(str(user_id))
    if not rec:
        return 401, {"error": "invalid_code", "message": "No registration code issued for this user"}

    expected = rec.code_hash
    reg_code_str = str(registration_token).zfill(6)
    actual = hash_otp_code_with_salt(reg_code_str, rec.salt)
    if expected != actual:
        return 401, {"error": "invalid_code", "message": "Registration code did not match"}

    otp_store.invalidate(str(user_id))

    # Check if hardware_id exists in Hardware table
    hardware = db.query(Hardware).filter(Hardware.hardware_id == hardware_id).first()
    if not hardware:
        return 404, {"error": "hardware_not_found", "message": "Hardware ID not registered"}

    try:
        # Start transaction
        device_uuid = uuidlib.uuid4()
        # Create Device entry
        device = Device(id=device_uuid, device_name=device_name, firmware_version=firmware_version)
        db.add(device)
        db.flush()  # To get device.id

        # Prevent the same device from being registered to multiple users
        existing_for_device = db.query(AuthenticatedDevice).filter(AuthenticatedDevice.device_id == device_uuid).first()
        if existing_for_device and existing_for_device.user_id != user_id:
            db.rollback()
            return 409, {
                "error": "device_conflict",
                "message": "device_id already registered to a different user",
                "existingUserId": str(existing_for_device.user_id),
            }

        # Allow multiple devices per user (1-n)
        auth_device = AuthenticatedDevice(user_id=user_id, device_id=device_uuid)
        db.add(auth_device)
        db.commit()
    except IntegrityError:
        db.rollback()
        return 409, {"error": "unique_constraint_violation", "message": "Concurrent update conflict, please retry"}
    except SQLAlchemyError as e:
        db.rollback()
        return 500, {"error": "db_error", "message": str(e)}

    # Issue full tokens for authenticated session
    tokens = generate_user_tokens(str(user_id))
    return 200, {
        "user_id": str(user_id),
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": 60 * 60,
    }
