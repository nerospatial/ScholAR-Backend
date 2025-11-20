# app/websocket/toys/routes.py
"""
Toys WebSocket Routes
Handles /ws/toys endpoint for NeroDivine toys devices
"""
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK
from app.core.log import logger
from app.websocket.toys.session import ToysWebSocketSession
from app.websocket.helpers.messages import get_ready_message


def register_toys_ws_routes(app: FastAPI) -> None:
    """Register toys WebSocket routes"""
    # Store active toy sessions
    active_sessions: Dict[str, ToysWebSocketSession] = {}

    @app.websocket("/ws/toys/queries")
    async def toys_websocket_endpoint(ws: WebSocket):
        await ws.accept()
        session_id = str(id(ws))
        
        # Create toys session
        session = ToysWebSocketSession(ws, session_id)
        active_sessions[session_id] = session
        
        # Send ready message
        await session._send_message(get_ready_message())
        logger.info(f"[Toys] WebSocket connection established: {session_id}")
        
        try:
            while True:
                # Wait for messages from toy device
                # Wait for messages from toy device
                try:
                    # Use receive() to handle both text (JSON) and binary (Audio) frames
                    message = await ws.receive()
                    
                    if "text" in message:
                        # Handle JSON control messages
                        import json
                        try:
                            data = json.loads(message["text"])
                            await session.handle_message(data)
                        except json.JSONDecodeError:
                            logger.warning(f"[Toys] Received invalid JSON: {message['text'][:100]}")
                            await session._send_error("Invalid JSON format")
                            
                    elif "bytes" in message:
                        # Handle Binary Audio Frame
                        await session.handle_message(message["bytes"])
                        
                except ValueError as e:
                    logger.error(f"[Toys] Value error in receive loop: {e}")
                    await session._send_error("Invalid message format")
                    
        except WebSocketDisconnect:
            logger.info(f"[Toys] WebSocket disconnected: {session_id}")
        except ConnectionClosedOK:
            logger.info(f"[Toys] WebSocket connection closed normally: {session_id}")
        except Exception as e:
            logger.error(f"[Toys] WebSocket error: {e}")
        finally:
            # Cleanup session
            if session_id in active_sessions:
                await active_sessions[session_id].stop_llm_session()
                del active_sessions[session_id]
                logger.info(f"[Toys] Session cleaned up: {session_id}")
