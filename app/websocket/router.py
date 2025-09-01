from fastapi import APIRouter
from .audio_ws import router as audio_ws_router

router = APIRouter()
router.include_router(audio_ws_router, tags=["ws"])
