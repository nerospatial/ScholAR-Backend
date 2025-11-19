# app/schemas/stories.py
"""
Story Schemas - Request/Response validation for Story API
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ===== Persona Schemas =====
class PersonaBase(BaseModel):
    """Base schema for Persona"""
    persona: str = Field(..., min_length=1, max_length=100, description="Persona name")


class PersonaCreate(PersonaBase):
    """Schema for creating a persona"""
    pass


class PersonaResponse(PersonaBase):
    """Schema for persona response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Language Schemas =====
class LanguageBase(BaseModel):
    """Base schema for Language"""
    lang: str = Field(..., min_length=1, max_length=50, description="Language name or code")


class LanguageCreate(LanguageBase):
    """Schema for creating a language"""
    pass


class LanguageResponse(LanguageBase):
    """Schema for language response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Theme Schemas =====
class ThemeBase(BaseModel):
    """Base schema for Theme"""
    theme: str = Field(..., min_length=1, max_length=50, description="Theme name")


class ThemeCreate(ThemeBase):
    """Schema for creating a theme"""
    pass


class ThemeResponse(ThemeBase):
    """Schema for theme response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Story Schemas =====
class StoryBase(BaseModel):
    """Base schema with common story fields"""
    persona_id: UUID = Field(..., description="Persona ID (e.g., Little Krishna)")
    theme_id: UUID = Field(..., description="Theme/category ID")
    lang_id: UUID = Field(..., description="Language ID")
    title: str = Field(..., min_length=1, max_length=255, description="Story title")
    description: Optional[str] = Field(None, description="Short story description")
    content: str = Field(..., min_length=10, description="Full story text content")


class StoryCreate(StoryBase):
    """Schema for creating a new story"""
    is_active: bool = Field(default=True, description="Whether story is active")


class StoryUpdate(BaseModel):
    """Schema for updating an existing story (all fields optional)"""
    persona_id: Optional[UUID] = None
    theme_id: Optional[UUID] = None
    lang_id: Optional[UUID] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=10)
    is_active: Optional[bool] = None


class StoryResponse(StoryBase):
    """Schema for story response with all story fields"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    word_count: int = Field(description="Approximate word count")
    estimated_duration_minutes: int = Field(description="Estimated duration in minutes")
    
    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    """Schema for list of stories response"""
    stories: list[StoryResponse]
    total: int
    page: int = 1
    page_size: int = 50
