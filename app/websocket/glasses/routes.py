from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK
from app.core.log import logger
from app.websocket.glasses.session import GlassesWebSocketSession
from app.websocket.helpers.messages import get_ready_message


def register_glasses_ws_routes(app: FastAPI) -> None:
    """
    Register glasses WebSocket routes.
    Endpoint: /ws/queries (maintains backward compatibility)
    """
    # Store active glasses sessions
    active_sessions: Dict[str, GlassesWebSocketSession] = {}

    @app.websocket("/ws/glasses/queries")
    async def queries_websocket_endpoint(ws: WebSocket):
        """
        Main WebSocket endpoint for glasses devices.
        Handles audio, video, and text interactions.
        """
        await ws.accept()
        session_id = str(id(ws))

        # Create glasses session
        session = GlassesWebSocketSession(ws, session_id)
        active_sessions[session_id] = session

        # Send ready message
        await session._send_message(get_ready_message())
        logger.info(f"[glasses] WebSocket connection established: {session_id}")

        try:
            while True:
                # Wait for messages from client
                try:
                    message = await ws.receive_json()
                    await session.handle_message(message)
                except ValueError:
                    # Try to receive as text
                    text_message = await ws.receive_text()
                    await session.handle_message({"type": "text", "data": text_message})

        except WebSocketDisconnect:
            logger.info(f"[glasses] WebSocket disconnected: {session_id}")
        except ConnectionClosedOK:
            logger.info(f"[glasses] WebSocket connection closed normally: {session_id}")
        except Exception as e:
            logger.error(f"[glasses] WebSocket error: {e}")
        finally:
            # Cleanup session
            if session_id in active_sessions:
                await active_sessions[session_id].stop_llm_session()
                del active_sessions[session_id]
