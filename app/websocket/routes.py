# app/websocket/routes.py
# Main WebSocket routes registry
from fastapi import FastAPI
from app.websocket.glasses.routes import register_glasses_ws_routes


def register_ws_routes(app: FastAPI) -> None:
    """
    Register all device-specific WebSocket routes.
    This is the main entry point for WebSocket route registration.
    """
    # Register glasses WebSocket endpoints
    register_glasses_ws_routes(app)

    # Future: register toys WebSocket endpoints
    # from app.websocket.toys.routes import register_toys_ws_routes
    # register_toys_ws_routes(app)
