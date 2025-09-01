from fastapi import APIRouter

# Create a versioned router for v1
router = APIRouter()

# Import endpoint routers here
from ...websocket import audio_ws

# Include them in v1 router
router.include_router(audio_ws.router, prefix="/ws", tags=["WebSocket"])
