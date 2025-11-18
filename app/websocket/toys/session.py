# app/websocket/toys/session.py
"""
Toys WebSocket Session - Audio-Only Bidirectional Communication
Little Krishna AI Persona for NeroDivine Toys
"""
import asyncio
import base64
import traceback
from typing import Dict, Any
from fastapi import WebSocket
from app.core.log import logger
from app.llm.providers.llm_provider_factory import get_llm_provider, LLMProviderType
from app.websocket.helpers.session_base import BaseWebSocketSession
from app.websocket.helpers.messages import (
    get_start_query_session_message,
    get_stop_query_session_message,
    get_query_responder_speaking_message,
    get_query_responder_done_message,
    get_error_message,
    get_user_interrupted_message,
)
from app.core.toys_config import LITTLE_KRISHNA_SYSTEM_INSTRUCTION
from app.llm.providers.gemini.gemini_settings import gemini_settings


class ToysWebSocketSession(BaseWebSocketSession):
    """
    Manages a single WebSocket session for Toys devices (audio-only).
    Extends BaseWebSocketSession with toys-specific audio-only handling.
    """
    
    def __init__(self, websocket: WebSocket, session_id: str):
        super().__init__(websocket, session_id, device_type="toys")
        self.response_streaming_started = False
        
    async def start_llm_session(self):
        """Start LLM provider connection with Little Krishna system prompt"""
        try:
            if self.llm_provider and self.active:
                logger.warning(f"[Toys] Session already active for {self.session_id}")
                return

            # Get Gemini provider with Little Krishna system instruction
            # Uses gemini_settings for all config except system_instruction
            self.llm_provider = get_llm_provider(
                LLMProviderType.GEMINI,
                system_instruction=LITTLE_KRISHNA_SYSTEM_INSTRUCTION
            )
            
            await self.llm_provider.connect()
            self.active = True

            await self._send_message(get_start_query_session_message())
            logger.info(f"[Toys] LLM session started with Little Krishna persona for {self.session_id}")

        except Exception as e:
            logger.error(f"[Toys] Failed to start LLM session: {e}")
            logger.error(f"[Toys] Exception details: {traceback.format_exc()}")
            await self._send_error(f"Failed to start session: {str(e)}")
            # Clean up failed session
            if self.llm_provider:
                try:
                    await self.llm_provider.disconnect()
                except:
                    pass
                self.llm_provider = None
            self.active = False
            
    async def _start_response_streaming(self):
        """Start audio response streaming on first user input"""
        if not self.response_streaming_started and self.llm_provider and self.active:
            # Start LLM provider response streaming
            await self.llm_provider.start_response_streaming()
            
            # Start only audio streaming task (no text for toys)
            self.background_tasks = [
                asyncio.create_task(self._stream_audio_responses())
            ]
            self.response_streaming_started = True
            logger.info(f"[Toys] Audio-only response streaming started for {self.session_id}")
            
    async def handle_message(self, message: Dict[str, Any]):
        """
        Process incoming WebSocket message - audio-only for toys.
        Toys only support audio input, no video or text.
        """
        try:
            message_type = message.get("type")
            
            if message_type == "audio":
                await self._handle_audio_message(message)
            elif message_type == get_start_query_session_message():
                await self.start_llm_session()
            elif message_type == get_stop_query_session_message():
                await self.stop_llm_session()
            elif message_type == get_user_interrupted_message():
                await self._handle_user_interrupt()
            else:
                logger.warning(f"[Toys] Unknown or unsupported message type: {message_type}")
                if message_type in ["text", "video"]:
                    await self._send_error(f"Toys only support audio input. Text/video not supported.")
                else:
                    await self._send_error(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"[Toys] Error handling message: {e}")
            await self._send_error(f"Error processing message: {str(e)}")
            
    async def _handle_audio_message(self, message: Dict[str, Any]):
        """Handle audio input from toy device"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return

        audio_data = message.get("data", "")
        sample_rate = message.get("sample_rate", gemini_settings.send_sample_rate)

        if audio_data:
            try:
                audio_bytes = base64.b64decode(audio_data)
                # Ensure streaming tasks are running
                await self._start_response_streaming()
                await self.llm_provider.send_audio(audio_bytes, sample_rate)
                logger.debug(f"[Toys] Audio sent to LLM: {len(audio_bytes)} bytes at {sample_rate}Hz")
            except Exception as e:
                await self._send_error(f"Invalid audio data: {str(e)}")
                
    async def _handle_user_interrupt(self):
        """Handle user interruption"""
        if self.llm_provider and self.active:
            logger.info(f"[Toys] User interrupted session {self.session_id}")
            # Could implement interrupt handling in provider if needed
            
    async def _stream_audio_responses(self):
        """Stream audio responses from Little Krishna to toy device"""
        try:
            if not self.llm_provider:
                return
            
            logger.info(f"[Toys] Audio response streaming started for {self.session_id}")

            await self._send_message(get_query_responder_speaking_message())
            logger.info(f"[Toys] Little Krishna speaking...")

            first_chunk = True
            chunk_count = 0
            total_bytes = 0

            async for audio_chunk in self.llm_provider.get_audio_response():
                if not self.active:
                    break

                if not audio_chunk:
                    logger.warning(f"[Toys] Received empty audio chunk from provider")
                    continue

                chunk_count += 1
                total_bytes += len(audio_chunk)

                audio_b64 = base64.b64encode(audio_chunk).decode()

                if first_chunk:
                    logger.info(
                        f"[Toys] First audio chunk from Krishna → {len(audio_chunk)} bytes "
                        f"({len(audio_b64)} base64 chars)"
                    )
                    first_chunk = False
                else:
                    logger.debug(
                        f"[Toys] Audio chunk #{chunk_count}: {len(audio_chunk)} bytes"
                    )

                await self._send_message({
                    "type": "audio_response",
                    "data": audio_b64,
                    "sample_rate": gemini_settings.receive_sample_rate,
                    "encoding": "pcm_s16le",
                    "channels": gemini_settings.audio_channels
                })

            logger.info(
                f"[Toys] Audio stream ended. "
                f"Sent {chunk_count} chunks ({total_bytes} bytes total)"
            )
            await self._send_message(get_query_responder_done_message())

        except Exception as e:
            logger.error(f"[Toys] Error streaming audio responses: {e}")
            logger.error(f"[Toys] Exception details: {traceback.format_exc()}")
            await self._send_message(get_query_responder_done_message())
