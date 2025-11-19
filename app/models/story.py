# app/models/story.py
"""
Story Model - Database model for NeroDivine story content
Stories are pre-written narratives that can be narrated by AI personas
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Story(Base):
    """
    Story model for storing narrative content.
    Each story is associated with a persona, theme, and language.
    """
    __tablename__ = "stories"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, index=True)
    lang_id = Column(UUID(as_uuid=True), ForeignKey("languages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Story metadata
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)  # Short description/summary
    content = Column(Text, nullable=False)  # Full story text for narration
    
    # Status
    is_active = Column(Boolean, default=True, index=True)  # Active/archived
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    persona_rel = relationship("Persona", back_populates="stories")
    theme_rel = relationship("Theme", back_populates="stories")
    language_rel = relationship("Language", back_populates="stories")
    
    def __repr__(self):
        return f"<Story(id={self.id}, title='{self.title}', persona_id={self.persona_id})>"
    
    @property
    def word_count(self) -> int:
        """Calculate approximate word count of story content"""
        return len(self.content.split()) if self.content else 0
    
    @property
    def estimated_duration_minutes(self) -> int:
        """Estimate duration in minutes based on word count (150 words/min)"""
        return max(1, self.word_count // 150)
