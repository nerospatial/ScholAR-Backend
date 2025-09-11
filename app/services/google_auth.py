from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.schemas.google_user import GoogleUser

def get_user_by_google_sub(sub: str, db: Session):
    return db.query(User).filter(User.google_sub == sub).first()

def create_user_from_google_info(google_user: GoogleUser, db: Session):
    # Check for existing user by google_sub or email
    existing_user = db.query(User).filter(
        (User.google_sub == google_user.sub) | (User.email == google_user.email)
    ).first()
    if existing_user:
        return existing_user

    user = User(
        username=google_user.name,
        email=google_user.email,
        google_sub=google_user.sub
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        # Try to fetch the user by email or google_sub
        return db.query(User).filter(
            (User.google_sub == google_user.sub) | (User.email == google_user.email)
        ).first()