from __future__ import annotations
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import secrets

from app.models.user import User
from app.models.authenticated_device import AuthenticatedDevice
from sqlalchemy.exc import IntegrityError
from app.services.tokens.token_utils import jwt_token_manager, generate_user_tokens
from app.utils.otp_utils import generate_six_digit_otp_with_hash, hash_otp_code_with_salt
from app.infra.cache.otp_store import otp_store


DEVICE_REGISTRATION_TOKEN_TTL_S = 300  # 5 minutes


async def initiate_device_authentication(user_id: int, db: Session) -> Tuple[int, Dict]:
    # Verify that the user exists
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False,User.is_verified==True).first()
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



def complete_device_authentication(user_id: int, registration_token: str, access_token: str, device_id: int, db: Session) -> Tuple[int, Dict]:
    # Decode and validate the short-lived registration token
    try:
        payload = jwt_token_manager.decode_access_token(registration_token)
    except Exception as e:
        return 401, {"error": "invalid_token", "message": str(e)}

    if payload.get("sub") != str(user_id) or payload.get("purpose") != "device_auth":
        return 401, {"error": "invalid_token", "message": "Token not valid for device authentication"}

    # Verify registration code from store
    rec = otp_store.get(str(user_id))
    if not rec:
        return 401, {"error": "invalid_code", "message": "No registration code issued for this user"}

    expected = rec.code_hash
    actual = hash_otp_code_with_salt(payload.get("registration_code", ""), rec.salt)
    if expected != actual:
        return 401, {"error": "invalid_code", "message": "Registration code did not match"}

    otp_store.invalidate(str(user_id))

    # Prevent the same device from being registered to multiple users
    existing_for_device = db.query(AuthenticatedDevice).filter(AuthenticatedDevice.device_id == device_id).first()
    if existing_for_device and existing_for_device.user_id != user_id:
        return 409, {
            "error": "device_conflict",
            "message": "device_id already registered to a different user",
            "existingUserId": str(existing_for_device.user_id),
        }

    # Allow multiple devices per user (1-n)
    existing_mapping = db.query(AuthenticatedDevice).filter(
        AuthenticatedDevice.user_id == user_id,
        AuthenticatedDevice.device_id == device_id
    ).first()

    try:
        if existing_mapping:
            existing_mapping.last_connected_at = func.now()
            db.add(existing_mapping)
        else:
            device = AuthenticatedDevice(user_id=user_id, device_id=device_id)
            db.add(device)
        db.commit()
    except IntegrityError:
        db.rollback()
        return 409, {"error": "unique_constraint_violation", "message": "Concurrent update conflict, please retry"}

    # Issue full tokens for authenticated session
    tokens = generate_user_tokens(str(user_id))
    return 200, {
        "user_id": user_id,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": 60 * 60,
    }
