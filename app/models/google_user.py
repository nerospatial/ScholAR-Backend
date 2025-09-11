from sqlalchemy import Column, Integer, String
from app.db.database import Base

class GoogleUser(Base):
    __tablename__ = "google_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    google_sub = Column(String, unique=True, index=True)