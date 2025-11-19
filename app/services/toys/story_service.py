from __future__ import annotations
from typing import List, Optional, Tuple, Dict
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.story import Story
from app.models.persona import Persona
from app.models.language import Language
from app.models.theme import Theme
from app.schemas.stories import StoryResponse, StoryListResponse


def get_stories(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    persona_id: Optional[UUID] = None,
    theme_id: Optional[UUID] = None,
    lang_id: Optional[UUID] = None
) -> Tuple[int, Dict]:
    """Get paginated list of stories with optional filtering"""
    try:
        query = db.query(Story).filter(Story.is_active == True)

        # Apply filters
        if persona_id:
            query = query.filter(Story.persona_id == persona_id)
        if theme_id:
            query = query.filter(Story.theme_id == theme_id)
        if lang_id:
            query = query.filter(Story.lang_id == lang_id)

        # Get total count
        total = query.count()

        # Apply pagination
        stories = query.offset((page - 1) * page_size).limit(page_size).all()

        # Convert to response format
        story_responses = [StoryResponse.model_validate(story) for story in stories]

        response_data = StoryListResponse(
            stories=story_responses,
            total=total,
            page=page,
            page_size=page_size
        )

        return 200, response_data.model_dump()

    except Exception as e:
        return 500, {
            "error": "database_error",
            "message": f"Failed to fetch stories: {str(e)}"
        }


def get_story_by_id(db: Session, story_id: UUID) -> Tuple[int, Dict]:
    """Get a specific story by ID"""
    try:
        story = db.query(Story).filter(
            and_(Story.id == story_id, Story.is_active == True)
        ).first()

        if not story:
            return 404, {
                "error": "story_not_found",
                "message": "Story not found"
            }

        # Convert to response format
        story_response = StoryResponse.model_validate(story)

        return 200, story_response.model_dump()

    except Exception as e:
        return 500, {
            "error": "database_error",
            "message": f"Failed to fetch story: {str(e)}"
        }