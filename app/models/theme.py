# app/models/theme.py
"""
Theme Model - Represents story themes/categories
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Theme(Base):
    """
    Theme model for story categorization.
    Themes represent story types (playful, moral, adventure, etc.)
    """
    __tablename__ = "themes"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Theme name (e.g., "playful", "moral", "adventure", "devotional")
    theme = Column(String(50), nullable=False, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    stories = relationship("Story", back_populates="theme_rel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Theme(id={self.id}, theme='{self.theme}')>"
