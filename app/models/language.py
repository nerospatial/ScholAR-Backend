# app/models/language.py
"""
Language Model - Represents languages for story content
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Language(Base):
    """
    Language model for story localization.
    Supports multiple languages for story content.
    """
    __tablename__ = "languages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Language name/code (e.g., "English", "Hindi", "en", "hi")
    lang = Column(String(50), nullable=False, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    stories = relationship("Story", back_populates="language_rel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Language(id={self.id}, lang='{self.lang}')>"
