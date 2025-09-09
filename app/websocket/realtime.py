import asyncio
import json
from websockets.exceptions import ConnectionClosed

from app.websocket.base import BaseWebSocketServer
from app.core.log import logger
from app.llm.base import AudioOut, TextOut, TurnComplete, SessionId, GoAway, Interrupted
from app.schemas.messages import (
    TYPE_SESSION_ID, TYPE_TURN_COMPLETE, TYPE_TEXT, TYPE_INTERRUPTED
)

class RealtimeServer(BaseWebSocketServer):
    """Generic realtime server that talks to any RealtimeLLM adapter."""
    def __init__(self, adapter_factory: callable, host=None, port=None):
        super().__init__(host or "0.0.0.0", port or 8765)
        self._adapter_factory = adapter_factory  # callable returning an adapter instance

    async def process_audio(self, websocket, client_id: int):
        self.active_clients[client_id] = websocket
        try:
            async with self._adapter_factory() as adapter:
                async with asyncio.TaskGroup() as tg:
                    async def recv_client():
                        async for message in websocket:
                            if isinstance(message, bytes):
                                await adapter.send_audio(message)
                            else:
                                try:
                                    data = json.loads(message)
                                    if data.get("type") == "text":
                                        await adapter.send_text(data.get("data", ""))
                                except Exception:
                                    logger.warning("Ignored non-JSON control message")

                    async def fwd_events():
                        async for ev in adapter.events():
                            if isinstance(ev, AudioOut):
                                await websocket.send(ev.pcm)
                            elif isinstance(ev, TextOut):
                                await websocket.send(json.dumps({"type": TYPE_TEXT, "data": ev.text}))
                            elif isinstance(ev, TurnComplete):
                                await websocket.send(json.dumps({"type": TYPE_TURN_COMPLETE}))
                            elif isinstance(ev, SessionId):
                                await websocket.send(json.dumps({"type": TYPE_SESSION_ID, "data": ev.id}))
                            elif isinstance(ev, GoAway):
                                logger.info(f"Session will terminate in: {ev.time_left:.2f}s")
                            elif isinstance(ev, Interrupted):
                                await websocket.send(json.dumps({
                                    "type": TYPE_INTERRUPTED,
                                    "data": "Response interrupted by user input"
                                }))

                    tg.create_task(recv_client())
                    tg.create_task(fwd_events())
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
