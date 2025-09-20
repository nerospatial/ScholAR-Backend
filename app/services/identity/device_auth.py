from __future__ import annotations
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.models.authenticated_device import AuthenticatedDevice
from sqlalchemy.exc import IntegrityError
from app.services.tokens.token_utils import jwt_token_manager, generate_user_tokens
from app.utils.otp_utils import generate_six_digit_otp_with_hash, hash_otp_code_with_salt
from app.infra.cache.otp_store import otp_store

DEVICE_OTP_TTL_S = 300  # 5 minutes


async def initiate_device_authentication(user_id: int, db: Session) -> Tuple[int, Dict]:
    # Verify that the user exists
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False, User.is_verified==True).first()
    if not user:
        return 404, {"error": "user_not_found", "message": "User not found"}

    # Generate OTP and persist in OTP store
    code, salt, code_hash = generate_six_digit_otp_with_hash()
    otp_store.set(str(user_id), code_hash, salt)

    # Issue short-lived token bound to this OTP
    short_token = jwt_token_manager.create_access_token(
        {"sub": str(user_id), "purpose": "device_auth", "otp": code}
    )

    # return the OTP as an integer registrationToken for client convenience
    try:
        reg_token = int(code)
    except Exception:
        reg_token = int(str(code))

    return 200, {
        "registrationToken": reg_token,
        "accessToken": short_token,
        "expiresIn": DEVICE_OTP_TTL_S,
    }


def complete_device_authentication(user_id: int, otp: "int|str", token: str, device_id: str, db: Session) -> Tuple[int, Dict]:
    # Decode and validate the short-lived token
    try:
        payload = jwt_token_manager.decode_access_token(token)
    except Exception as e:
        return 401, {"error": "invalid_token", "message": str(e)}

    if payload.get("sub") != str(user_id) or payload.get("purpose") != "device_auth":
        return 401, {"error": "invalid_token", "message": "Token not valid for device authentication"}

    # Verify OTP from store
    rec = otp_store.get(str(user_id))
    if not rec:
        return 401, {"error": "invalid_code", "message": "No OTP issued for this user"}

    # Accept registrationToken as int or string; normalize to string for hashing
    otp_str = str(otp)

    expected = rec.code_hash
    actual = hash_otp_code_with_salt(otp_str, rec.salt)
    if expected != actual:
        return 401, {"error": "invalid_code", "message": "OTP did not match"}

    otp_store.invalidate(str(user_id))

    # Enforce one-to-one mapping: check existing records
    existing_for_user = db.query(AuthenticatedDevice).filter(AuthenticatedDevice.user_id == user_id).first()
    existing_for_device = db.query(AuthenticatedDevice).filter(AuthenticatedDevice.device_id == device_id).first()

    if existing_for_device and existing_for_device.user_id != user_id:
        return 409, {
            "error": "device_conflict",
            "message": "device_id already registered to a different user",
            "existingUserId": str(existing_for_device.user_id),
        }

    if existing_for_user and existing_for_user.device_id != device_id:
        return 409, {
            "error": "user_conflict",
            "message": "user already registered a different device",
            "existingDeviceId": existing_for_user.device_id,
        }

    try:
        if existing_for_user:
            existing_for_user.last_connected_at = func.now()
            db.add(existing_for_user)
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
        "userId": user_id,
        "accessToken": tokens["access_token"],
        "refreshToken": tokens["refresh_token"],
        "expiresIn": 60 * 60,  # match ACCESS_TOKEN_EXPIRE_MINUTES default
    }
