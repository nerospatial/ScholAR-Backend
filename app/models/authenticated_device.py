# app/models/authenticated_device.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class AuthenticatedDevice(Base):
    __tablename__ = "authenticated_devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    device_id = Column(String(255), nullable=False, unique=True)
    first_connected_at = Column(DateTime, server_default=func.now())
    last_connected_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_authenticated_devices_user_id"),
        UniqueConstraint("device_id", name="uq_authenticated_devices_device_id"),
    )

    user = relationship("User", back_populates="authenticated_device")
