import asyncio
import json
import traceback
import websockets
from websockets.exceptions import ConnectionClosed

from app.core.log import logger


class BaseWebSocketServer:
    """Accepts a websocket, sends READY, and delegates to process_audio()."""
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.active_clients: dict[int, object] = {}

    async def start(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # run forever

    async def handle_client(self, websocket):
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")
        await websocket.send(json.dumps())
        try:
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.active_clients.pop(client_id, None)

    async def process_audio(self, websocket, client_id: int):
        raise NotImplementedError("Subclasses must implement process_audio()")
