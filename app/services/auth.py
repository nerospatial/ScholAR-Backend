import random
import string
import datetime
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from passlib.context import CryptContext
from app.core.email_config import fast_mail
from fastapi_mail import MessageSchema
from app.db.database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory hashmap for verification codes
verification_codes = {}  # email -> (code, expiry, password_hash)

def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

async def signup(user_in: UserCreate):

    # Check for existing user before sending verification code
    db: Session = SessionLocal()
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        return {"error": "User with this email already exists"}
    
    code = generate_verification_code()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    password_hash = pwd_context.hash(user_in.password)
    verification_codes[user_in.email] = (code, expiry, password_hash)
    await send_verification_email(str(user_in.email), code)
    return {"msg": "Verification code sent"}

async def send_verification_email(email: str, code: str):
    message = MessageSchema(
        subject="Your Scholar Backend Verification Code",
        recipients=[email],
        body=f"Your verification code is: {code}",
        subtype="plain"
    )
    await fast_mail.send_message(message)

def verify_code(email: str, code: str, db: Session):
    entry = verification_codes.get(email)
    if not entry:
        return False, "No code found"
    stored_code, expiry, password_hash = entry
    if stored_code != code or expiry < datetime.datetime.utcnow():
        return False, "Invalid or expired code"
    
    # Create user in DB with required fields
    now = datetime.datetime.utcnow()
    user = User(
        email=email,
        hashed_password=password_hash,
        is_deleted=False,
        created_at=now,
        updated_at=now
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    del verification_codes[email]
    return True, user

def authenticate_user(email: str, password: str, db: Session):
    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()
    if not user:
        return None
    if not pwd_context.verify(password, str(user.hashed_password)):
        return None
    return user