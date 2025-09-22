from sqlalchemy import Column, Integer, ForeignKey, DateTime
from app.db.database import Base
from datetime import datetime

class AuthenticatedDevice(Base):
    __tablename__ = "authenticated_devices"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    first_connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_connected_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)