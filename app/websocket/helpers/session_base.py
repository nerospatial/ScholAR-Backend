from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from app.core.log import logger


class BaseWebSocketSession(ABC):
    """
    Base class for all device WebSocket sessions.
    Provides shared logic for session management, LLM connection, and message sending.
    Each device type (glasses, toys) extends this class with device-specific behavior.
    """

    def __init__(self, websocket: WebSocket, session_id: str, device_type: str):
        """
        Initialize base WebSocket session.

        Args:
            websocket: FastAPI WebSocket connection
            session_id: Unique session identifier
            device_type: Type of device ('glasses' | 'toys')
        """
        self.websocket = websocket
        self.session_id = session_id
        self.device_type = device_type
        self.llm_provider = None
        self.active = False
        self.background_tasks = []
        self.response_streaming_started = False

    async def start_llm_session(self):
        """
        Start LLM provider connection.
        Common logic for all device types.
        """
        try:
            if self.llm_provider and self.active:
                logger.warning(f"[{self.device_type}] Session already active for {self.session_id}")
                return

            # Import here to avoid circular dependency
            from app.llm.providers.llm_provider_factory import get_llm_provider, LLMProviderType
            from app.websocket.helpers.messages import get_start_query_session_message

            self.llm_provider = get_llm_provider(LLMProviderType.GEMINI)
            await self.llm_provider.connect()
            self.active = True

            await self._send_message(get_start_query_session_message())
            logger.info(f"[{self.device_type}] LLM session started for {self.session_id}")

        except Exception as e:
            logger.error(f"[{self.device_type}] Failed to start LLM session: {e}")
            await self._send_error(f"Failed to start session: {str(e)}")
            # Cleanup
            if self.llm_provider:
                try:
                    await self.llm_provider.disconnect()
                except:
                    pass
                self.llm_provider = None
            self.active = False

    async def stop_llm_session(self):
        """
        Stop LLM provider connection and cleanup.
        Common logic for all device types.
        """
        try:
            self.active = False
            self.response_streaming_started = False

            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            self.background_tasks.clear()

            # Disconnect provider
            if self.llm_provider:
                await self.llm_provider.disconnect()
                self.llm_provider = None

            from app.websocket.helpers.messages import get_session_ended_message
            await self._send_message(get_session_ended_message())
            logger.info(f"[{self.device_type}] Session stopped for {self.session_id}")

        except Exception as e:
            logger.error(f"[{self.device_type}] Error stopping session: {e}")

    async def _send_message(self, message: Any):
        """
        Send message to WebSocket client.

        Args:
            message: Message to send (string or dict)
        """
        if self.websocket.client_state == WebSocketState.CONNECTED:
            if isinstance(message, str):
                await self.websocket.send_text(message)
            else:
                await self.websocket.send_json(message)

    async def _send_error(self, error_msg: str):
        """
        Send error message to client.

        Args:
            error_msg: Error message text
        """
        from app.websocket.helpers.messages import get_error_message
        await self._send_message({
            "type": get_error_message(),
            "message": error_msg
        })

    # Abstract methods - each device type must implement

    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]):
        """
        Process incoming WebSocket message.
        Device-specific implementation required.

        Args:
            message: Incoming message from client
        """
        pass

    @abstractmethod
    async def _start_response_streaming(self):
        """
        Start response streaming tasks.
        Device-specific implementation required (e.g., audio-only vs multimodal).
        """
        pass
