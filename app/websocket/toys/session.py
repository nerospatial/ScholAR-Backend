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
    
    PROTOCOL CHANGE (Hybrid Binary/Text):
    - Control messages (JSON): READY, START_QUERY_SESSION, etc.
    - Audio data: Raw Binary Frames (Opcode 0x2) - PCM 16-bit
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

    async def handle_message(self, message: Any):
        """
        Process incoming WebSocket message.
        - Dict: JSON control message
        - Bytes: Raw Audio Data (16kHz PCM)
        """
        try:
            # Handle Binary Audio Frame
            if isinstance(message, bytes):
                await self._handle_binary_audio(message)
                return

            # Handle JSON Control Message
            message_type = message.get("type")

            if message_type == "audio":
                # Legacy: Handle Base64 encoded audio in JSON (if client still sends it)
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

    async def _handle_binary_audio(self, audio_data: bytes):
        """Handle raw binary audio input (16kHz PCM 16-bit)"""
        if not self.llm_provider or not self.active:
            # If session not active, maybe auto-start? 
            # For now, strict protocol: must send START_QUERY_SESSION first.
            # But to be user-friendly, we could warn.
            # logger.warning("[Toys] Received audio but session not active")
            return

        if audio_data:
            try:
                # Ensure streaming tasks are running
                await self._start_response_streaming()
                
                # Send raw bytes to LLM
                # User specified input is 16kHz. gemini_settings.send_sample_rate is 16000.
                await self.llm_provider.send_audio(audio_data, gemini_settings.send_sample_rate)
                logger.debug(f"[Toys] Binary audio sent to LLM: {len(audio_data)} bytes")
            except Exception as e:
                logger.error(f"[Toys] Error processing binary audio: {e}")
                await self._send_error(f"Error processing audio: {str(e)}")

    async def _handle_audio_message(self, message: Dict[str, Any]):
        """Handle audio input from toy device"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return
        audio_data = message.get("data", "")
        sample_rate = message.get("sample_rate", gemini_settings.send_sample_rate)
        if audio_data:
            try:
                # Input from client is still likely Base64 JSON for now unless we change client too.
                # The plan focused on OUTPUT optimization first.
                # If client sends binary, handle_message needs to change to handle bytes.
                # For now, assuming client input is still JSON-wrapped Base64 as per current `routes.py`
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
        """
        Stream audio responses from Little Krishna to toy device.
        OPTIMIZED: Uses Binary Frames + Time-Based Buffering.
        """
        try:
            if not self.llm_provider:
                return
            logger.info(f"[Toys] Audio response streaming started for {self.session_id}")
            await self._send_message(get_query_responder_speaking_message())
            logger.info(f"[Toys] Little Krishna speaking...")
            
            import time
            
            first_chunk = True
            chunk_count = 0
            total_bytes = 0
            
            # OPTIMIZED BUFFERING CONFIGURATION
            # MTU Safety: ~1400 bytes fits in standard TCP packet (1500 MTU - headers)
            # Latency: Flush if data sits for > 100ms
            MTU_SIZE = 1400 
            MAX_BUFFER_AGE = 0.1 # 100ms
            
            audio_buffer = bytearray()
            last_send_time = time.time()

            async for audio_chunk in self.llm_provider.get_audio_response():
                if not self.active:
                    break
                if not audio_chunk:
                    continue

                # Append new data to buffer
                audio_buffer.extend(audio_chunk)
                
                # 1. Size-based Flush: Send full MTU-sized chunks immediately
                while len(audio_buffer) >= MTU_SIZE:
                    chunk_to_send = audio_buffer[:MTU_SIZE]
                    del audio_buffer[:MTU_SIZE]
                    
                    await self._send_audio_chunk_binary(chunk_to_send, first_chunk)
                    if first_chunk: first_chunk = False
                    
                    chunk_count += 1
                    total_bytes += len(chunk_to_send)
                    last_send_time = time.time()
                
                # 2. Time-based Flush: Check if buffer is stale
                # Only flush if we have SOME data and it's been waiting too long
                if len(audio_buffer) > 0 and (time.time() - last_send_time > MAX_BUFFER_AGE):
                    await self._send_audio_chunk_binary(audio_buffer, first_chunk)
                    if first_chunk: first_chunk = False
                    
                    chunk_count += 1
                    total_bytes += len(audio_buffer)
                    audio_buffer.clear()
                    last_send_time = time.time()
                    logger.debug(f"[Toys] Time-based flush triggered for {self.session_id}")

            # Flush remaining buffer at end of stream
            if len(audio_buffer) > 0:
                await self._send_audio_chunk_binary(audio_buffer, first_chunk)
                chunk_count += 1
                total_bytes += len(audio_buffer)

            logger.info(f"[Toys] Audio stream ended. Sent {total_bytes} bytes total in {chunk_count} chunks (Binary)")
            await self._send_message(get_query_responder_done_message())
            
        except Exception as e:
            logger.error(f"[Toys] Error streaming audio responses: {e}")
            await self._send_message(get_query_responder_done_message())

    async def _send_audio_chunk_binary(self, chunk: bytes, is_first: bool):
        """Helper to send raw binary audio chunk"""
        if is_first:
            logger.info(f"[Toys] First audio chunk sent ({len(chunk)} bytes) [BINARY]")
        
        # Send as Raw Binary Frame (Opcode 0x2)
        # No JSON wrapping, No Base64 encoding
        await self.websocket.send_bytes(chunk)