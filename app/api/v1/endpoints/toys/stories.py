from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.toys.story_service import get_stories, get_story_by_id

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("/", response_model=dict)
async def list_stories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    persona_id: Optional[UUID] = Query(None, description="Filter by persona ID"),
    theme_id: Optional[UUID] = Query(None, description="Filter by theme ID"),
    lang_id: Optional[UUID] = Query(None, description="Filter by language ID"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of stories with optional filtering.

    - **page**: Page number (default: 1)
    - **page_size**: Number of items per page (default: 50, max: 100)
    - **persona_id**: Filter stories by persona UUID
    - **theme_id**: Filter stories by theme UUID
    - **lang_id**: Filter stories by language UUID
    """
    status_code, response_data = get_stories(
        db=db,
        page=page,
        page_size=page_size,
        persona_id=persona_id,
        theme_id=theme_id,
        lang_id=lang_id
    )

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response_data)

    return response_data


@router.get("/{story_id}", response_model=dict)
async def get_story(
    story_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific story by ID.

    - **story_id**: UUID of the story to retrieve
    """
    status_code, response_data = get_story_by_id(db=db, story_id=story_id)

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response_data)

    return response_data