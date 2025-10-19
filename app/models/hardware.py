from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base

class Hardware(Base):
    __tablename__ = "hardware"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    hardware_id = Column(String, unique=True, nullable=False, index=True)