# app/models/persona.py
"""
Persona Model - Represents AI personas for storytelling (e.g., Little Krishna)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Persona(Base):
    """
    Persona model for AI storyteller characters.
    Each persona has a unique identity and can narrate stories.
    """
    __tablename__ = "personas"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Persona name (e.g., "Little Krishna", "Wise Guru", etc.)
    persona = Column(String(100), nullable=False, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    stories = relationship("Story", back_populates="persona_rel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Persona(id={self.id}, persona='{self.persona}')>"
