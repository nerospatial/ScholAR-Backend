import asyncio
import base64
import traceback
from typing import Dict, Any
from fastapi import WebSocket
from app.websocket.helpers.session_base import BaseWebSocketSession
from app.core.log import logger
from app.websocket.helpers.messages import (
    get_start_query_session_message,
    get_stop_query_session_message,
    get_query_responder_speaking_message,
    get_query_responder_done_message,
    get_user_interrupted_message,
)


class GlassesWebSocketSession(BaseWebSocketSession):
    """
    Glasses-specific WebSocket session.
    Supports multimodal interactions: audio IN/OUT, video IN, text IN/OUT.
    """

    def __init__(self, websocket: WebSocket, session_id: str):
        """Initialize glasses WebSocket session"""
        super().__init__(websocket, session_id, device_type="glasses")

    async def handle_message(self, message: Dict[str, Any]):
        """Process incoming WebSocket message from glasses device"""
        try:
            message_type = message.get("type")

            if message_type == "text":
                await self._handle_text_message(message)
            elif message_type == "audio":
                await self._handle_audio_message(message)
            elif message_type == "video":
                await self._handle_video_message(message)
            elif message_type == get_start_query_session_message():
                await self.start_llm_session()
            elif message_type == get_stop_query_session_message():
                await self.stop_llm_session()
            elif message_type == get_user_interrupted_message():
                await self._handle_user_interrupt()
            else:
                logger.warning(f"[glasses] Unknown message type: {message_type}")
                await self._send_error(f"Unknown message type: {message_type}")

        except Exception as e:
            logger.error(f"[glasses] Error handling message: {e}")
            await self._send_error(f"Error processing message: {str(e)}")

    async def _start_response_streaming(self):
        """Start response streaming tasks (audio + text) for glasses"""
        if not self.response_streaming_started and self.llm_provider and self.active:
            # Start LLM provider response streaming
            await self.llm_provider.start_response_streaming()

            # Start WebSocket response streaming tasks
            self.background_tasks = [
                asyncio.create_task(self._stream_text_responses()),
                asyncio.create_task(self._stream_audio_responses())
            ]
            self.response_streaming_started = True
            logger.info(f"[glasses] Response streaming started for session {self.session_id}")

    async def _handle_text_message(self, message: Dict[str, Any]):
        """Handle text input from glasses"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return

        text = message.get("data", "")
        if text:
            # Ensure streaming tasks are running
            await self._start_response_streaming()
            await self.llm_provider.send_text(text)

    async def _handle_audio_message(self, message: Dict[str, Any]):
        """Handle audio input from glasses"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return

        audio_data = message.get("data", "")
        sample_rate = message.get("sample_rate", 16000)

        if audio_data:
            try:
                audio_bytes = base64.b64decode(audio_data)
                # Ensure streaming tasks are running
                await self._start_response_streaming()
                await self.llm_provider.send_audio(audio_bytes, sample_rate)
            except Exception as e:
                await self._send_error(f"Invalid audio data: {str(e)}")

    async def _handle_video_message(self, message: Dict[str, Any]):
        """Handle video/image input from glasses camera"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return

        video_data = message.get("data", "")
        mime_type = message.get("mime_type", "image/jpeg")

        if video_data:
            try:
                video_bytes = base64.b64decode(video_data)
                await self.llm_provider.send_video(video_bytes, mime_type)
            except Exception as e:
                await self._send_error(f"Invalid video data: {str(e)}")

    async def _handle_user_interrupt(self):
        """Handle user interruption"""
        if self.llm_provider and self.active:
            logger.info(f"[glasses] User interrupted session {self.session_id}")

    async def _stream_text_responses(self):
        """Stream text responses from LLM to glasses"""
        try:
            if not self.llm_provider:
                return

            async for text_chunk in self.llm_provider.get_text_response():
                if not self.active:
                    break

                await self._send_message({
                    "type": "text_response",
                    "data": text_chunk
                })

        except Exception as e:
            logger.error(f"[glasses] Error streaming text responses: {e}")

    async def _stream_audio_responses(self):
        """Stream audio responses from LLM to glasses"""
        try:
            if not self.llm_provider:
                return

            logger.info(f"[glasses/{self.session_id}] Audio streaming started")

            await self._send_message(get_query_responder_speaking_message())
            logger.info(f"[glasses/{self.session_id}] Query responder speaking...")

            first_chunk = True
            chunk_count = 0
            total_bytes = 0

            async for audio_chunk in self.llm_provider.get_audio_response():
                if not self.active:
                    break

                if not audio_chunk:
                    logger.warning(f"[glasses/{self.session_id}] Received empty audio chunk")
                    continue

                chunk_count += 1
                total_bytes += len(audio_chunk)

                audio_b64 = base64.b64encode(audio_chunk).decode()

                if first_chunk:
                    logger.info(
                        f"[glasses/{self.session_id}] First audio chunk → {len(audio_chunk)} bytes "
                        f"({len(audio_b64)} base64 chars)"
                    )
                    first_chunk = False
                else:
                    logger.debug(
                        f"[glasses/{self.session_id}] Audio chunk #{chunk_count}: "
                        f"{len(audio_chunk)} bytes raw"
                    )

                await self._send_message({
                    "type": "audio_response",
                    "data": audio_b64,
                    "sample_rate": 24000,  # Gemini default
                    "encoding": "pcm_s16le",
                    "channels": 1
                })

            logger.info(
                f"[glasses/{self.session_id}] Audio stream ended. "
                f"Sent {chunk_count} chunks ({total_bytes} bytes total)"
            )
            await self._send_message(get_query_responder_done_message())

        except Exception as e:
            logger.error(f"[glasses/{self.session_id}] Error streaming audio: {e}")
            await self._send_message(get_query_responder_done_message())
