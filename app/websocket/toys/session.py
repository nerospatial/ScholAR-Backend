# app/websocket/toys/session.py
"""
Toys WebSocket Session - Audio-Only Bidirectional Communication
Little Krishna AI Persona for NeroDivine Toys
"""
import asyncio
import base64
import traceback
from typing import Dict, Any, Optional
from fastapi import WebSocket
from app.core.log import logger
from app.llm.providers.llm_provider_factory import get_llm_provider, LLMProviderType
from app.llm.providers.tts_provider_factory import get_tts_provider, TTSProviderType
from app.websocket.helpers.session_base import BaseWebSocketSession
from app.websocket.helpers.messages import (
    get_start_query_session_message,
    get_stop_query_session_message,
    get_query_responder_speaking_message,
    get_query_responder_done_message,
    get_error_message,
    get_user_interrupted_message,
    get_start_story_session_message,
    get_stop_story_session_message,
    get_story_responder_speaking_message,
    get_story_responder_done_message,
    get_play_story_message,
)
from app.core.toys_config import LITTLE_KRISHNA_SYSTEM_INSTRUCTION
from app.llm.providers.gemini.gemini_settings import gemini_settings
from app.llm.providers.elevenlabs.elevenlabs_settings import elevenlabs_settings
from app.services.toys.story_service import get_story_by_id
from app.db.database import get_db
from sqlalchemy.orm import Session


class ToysWebSocketSession(BaseWebSocketSession):
    """
    Manages a single WebSocket session for Toys devices (audio-only).
    Extends BaseWebSocketSession with toys-specific audio-only handling.
    """
    
    def __init__(self, websocket: WebSocket, session_id: str):
        super().__init__(websocket, session_id, device_type="toys")
        self.response_streaming_started = False
        # Story playback attributes
        self.story_tts_provider = None
        self.story_streaming_started = False
        self.current_story_text = ""
        self.user_name = ""
        
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
            
    async def stop_llm_session(self):
        """Stop both LLM and story sessions"""
        # Stop story session first
        if(self.story_tts_provider):    
            await self.stop_story_session()
        
        # Then stop regular LLM session
        if(self.llm_provider):
            await super().stop_llm_session()
            
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
            elif message_type == get_start_story_session_message():
                story_id = message.get("story_id")
                user_name = message.get("user_name", "Harii")
                if story_id:
                    await self.start_story_session(story_id, user_name)
                else:
                    await self._send_error("story_id is required for story session")
            elif message_type == get_stop_story_session_message():
                await self.stop_story_session()
            elif message_type == get_play_story_message():
                await self.play_story()
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

            await self._send_message({"type": get_query_responder_speaking_message()})
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
            await self._send_message({"type": get_query_responder_done_message()})

        except Exception as e:
            logger.error(f"[Toys] Error streaming audio responses: {e}")
            logger.error(f"[Toys] Exception details: {traceback.format_exc()}")
            await self._send_message({"type": get_query_responder_done_message()})

    # ===== Story Playback Methods =====

    async def start_story_session(self, story_id: str, user_name: str):
        """Start story playback session with ElevenLabs TTS"""
        try:
            if self.story_tts_provider and self.active:
                logger.warning(f"[Toys] Story session already active for {self.session_id}")
                return

            # Get story from database
            db = next(get_db())
            status_code, response_data = get_story_by_id(db, story_id)
            if status_code != 200:
                await self._send_error(f"Story not found: {story_id}")
                return

            story_data = response_data
            self.current_story_text = story_data["content"]
            self.user_name = user_name

            # Replace "Harii" with user name in real-time during streaming
            # We'll do this during text processing, not here

            # Create TTS provider using factory pattern
            self.story_tts_provider = get_tts_provider(TTSProviderType.ELEVENLABS)

            await self.story_tts_provider.connect()
            self.active = True

            await self._send_message(get_start_story_session_message())
            logger.info(f"[Toys] Story session started for {self.session_id} - Story: {story_id}, User: {user_name}")

        except Exception as e:
            logger.error(f"[Toys] Failed to start story session: {e}")
            logger.error(f"[Toys] Exception details: {traceback.format_exc()}")
            await self._send_error(f"Failed to start story session: {str(e)}")
            # Clean up failed session
            if self.story_tts_provider:
                try:
                    await self.story_tts_provider.disconnect()
                except:
                    pass
                self.story_tts_provider = None
            self.active = False

    async def stop_story_session(self):
        """Stop story playback session"""
        try:
            if self.story_tts_provider:
                await self.story_tts_provider.disconnect()
                self.story_tts_provider = None

            self.story_streaming_started = False
            self.current_story_text = ""
            self.user_name = ""
            self.active = False

            await self._send_message(get_stop_story_session_message())
            logger.info(f"[Toys] Story session stopped for {self.session_id}")

        except Exception as e:
            logger.error(f"[Toys] Error stopping story session: {e}")

    async def play_story(self):
        """Start story playback with real-time name replacement and TTS streaming"""
        if not self.story_tts_provider or not self.active or not self.current_story_text:
            await self._send_error("Story session not active")
            return

        try:
            # Start story streaming
            await self._start_story_streaming()

            # Process story text with name replacement in real-time
            story_chunks = self._process_story_text_realtime()

            await self._send_message(get_story_responder_speaking_message())
            logger.info(f"[Toys] Story narrator speaking...")

            for text_chunk in story_chunks:
                if not self.active:
                    break

                # Send text chunk to ElevenLabs for TTS
                await self.story_tts_provider.send_text(text_chunk)
                logger.debug(f"[Toys] Story text chunk sent: {text_chunk[:50]}...")

            # Signal end of text input
            await self.story_tts_provider.send_text("")

        except Exception as e:
            logger.error(f"[Toys] Error playing story: {e}")
            await self._send_error(f"Error playing story: {str(e)}")

    def _process_story_text_realtime(self):
        """Process story text with real-time name replacement"""
        # Split story into sentences for chunked processing
        import re

        # Replace "Harii" with user name
        processed_text = self.current_story_text.replace("Harii", self.user_name)

        # Split into sentences (simple approach)
        sentences = re.split(r'(?<=[.!?])\s+', processed_text.strip())

        # Yield chunks for real-time processing
        for sentence in sentences:
            if sentence.strip():
                yield sentence.strip() + " "

    async def _start_story_streaming(self):
        """Start audio response streaming for story playback"""
        if not self.story_streaming_started and self.story_tts_provider and self.active:
            # Start only audio streaming task
            self.background_tasks = [
                asyncio.create_task(self._stream_story_audio_responses())
            ]
            self.story_streaming_started = True
            logger.info(f"[Toys] Story audio-only response streaming started for {self.session_id}")

    async def _stream_story_audio_responses(self):
        """Stream story audio responses from ElevenLabs to toy device"""
        try:
            if not self.story_tts_provider:
                return

            logger.info(f"[Toys] Story audio response streaming started for {self.session_id}")

            first_chunk = True
            chunk_count = 0
            total_bytes = 0

            async for audio_chunk in self.story_tts_provider.get_audio_response():
                if not self.active:
                    break

                if not audio_chunk:
                    logger.warning(f"[Toys] Received empty story audio chunk from provider")
                    continue

                chunk_count += 1
                total_bytes += len(audio_chunk)

                audio_b64 = base64.b64encode(audio_chunk).decode()

                if first_chunk:
                    logger.info(
                        f"[Toys] First story audio chunk → {len(audio_chunk)} bytes "
                        f"({len(audio_b64)} base64 chars)"
                    )
                    first_chunk = False
                else:
                    logger.debug(
                        f"[Toys] Story audio chunk #{chunk_count}: {len(audio_chunk)} bytes"
                    )

                await self._send_message({
                    "type": "story_audio_response",
                    "data": audio_b64,
                    "sample_rate": elevenlabs_settings.sample_rate,
                    "encoding": "pcm_s16le",
                    "channels": 1  # ElevenLabs typically mono
                })

            logger.info(
                f"[Toys] Story audio stream ended. "
                f"Sent {chunk_count} chunks ({total_bytes} bytes total)"
            )
            await self._send_message(get_story_responder_done_message())

        except Exception as e:
            logger.error(f"[Toys] Error streaming story audio responses: {e}")
            logger.error(f"[Toys] Exception details: {traceback.format_exc()}")
            await self._send_message(get_story_responder_done_message())
