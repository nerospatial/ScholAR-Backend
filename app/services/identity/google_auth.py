from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.google_user import GoogleUser as GoogleUserModel
from app.schemas.google_user import GoogleUser as GoogleUserSchema

def get_user_by_google_sub(sub: str, db: Session):
    return db.query(GoogleUserModel).filter(GoogleUserModel.google_sub == sub).first()

def create_user_from_google_info(google_user: GoogleUserSchema, db: Session):
    # Check for existing user by google_sub or email
    existing_user = db.query(GoogleUserModel).filter(
        (GoogleUserModel.google_sub == google_user.google_sub) | (GoogleUserModel.email == google_user.email)
    ).first()
    if existing_user:
        return existing_user

    user = GoogleUserModel(
        username=google_user.username,
        email=google_user.email,
        google_sub=google_user.google_sub
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        # Try to fetch the user by email or google_sub
        return db.query(GoogleUserModel).filter(
            (GoogleUserModel.google_sub == google_user.google_sub) | (GoogleUserModel.email == google_user.email)
        ).first()