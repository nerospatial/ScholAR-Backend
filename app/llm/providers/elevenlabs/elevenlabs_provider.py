# app/llm/providers/elevenlabs/elevenlabs_provider.py
"""
ElevenLabs TTS Provider - Real-time Text-to-Speech
Implements BaseLLMProviderInterface for TTS functionality
"""
import asyncio
import json
import websockets
from typing import AsyncGenerator, Dict, Any, Optional
import traceback
from app.core.log import logger
from app.llm.interfaces.base_tts_provider_interface import BaseTTSProviderInterface
from app.llm.providers.elevenlabs.elevenlabs_settings import elevenlabs_settings


class ElevenLabsProvider(BaseTTSProviderInterface):
    """
    ElevenLabs Text-to-Speech provider for real-time audio streaming.
    Implements BaseTTSProviderInterface for TTS functionality.
    """

    def __init__(self):
        self.voice_id = elevenlabs_settings.voice_id
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.text_queue = asyncio.Queue()
        self.audio_queue = asyncio.Queue()
        self.streaming_task: Optional[asyncio.Task] = None
        self.text_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Establish WebSocket connection to ElevenLabs"""
        try:
            # ElevenLabs WebSocket URL for real-time TTS
            ws_url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={elevenlabs_settings.model_id}&output_format={elevenlabs_settings.output_format}&optimize_streaming_latency={elevenlabs_settings.optimize_streaming_latency}"

            headers = {
                "xi-api-key": elevenlabs_settings.api_key
            }

            logger.info(f"[ElevenLabs] Connecting to WebSocket: {ws_url}")
            self.websocket = await websockets.connect(ws_url, additional_headers=headers)
            self.connected = True

            # Send initial config message (required by ElevenLabs)
            config_message = {
                "text": " ",  # Start with empty space
                "voice_settings": {
                    "stability": elevenlabs_settings.stability,
                    "similarity_boost": elevenlabs_settings.similarity_boost
                }
            }
            await self.websocket.send(json.dumps(config_message))
            logger.debug("[ElevenLabs] Sent config message")

            # Start the streaming task
            self.streaming_task = asyncio.create_task(self._stream_audio())
            self.text_task = asyncio.create_task(self._send_text())

            logger.info(f"[ElevenLabs] Connected successfully with voice ID: {self.voice_id}")
            logger.debug(f"[ElevenLabs] Tasks created: streaming={self.streaming_task is not None}, text={self.text_task is not None}")

        except Exception as e:
            logger.error(f"[ElevenLabs] Failed to connect: {e}")
            logger.error(f"[ElevenLabs] Exception details: {traceback.format_exc()}")
            raise

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        try:
            if self.streaming_task:
                self.streaming_task.cancel()
                try:
                    await self.streaming_task
                except asyncio.CancelledError:
                    pass

            if self.text_task:
                self.text_task.cancel()
                try:
                    await self.text_task
                except asyncio.CancelledError:
                    pass

            if self.websocket and self.connected:
                # Send EOS (End of Stream) message
                eos_message = {
                    "text": " "
                }
            if self.websocket and self.connected:
                # Send EOS (End of Stream) message
                eos_message = {
                    "text": ""
                }
                await self.websocket.send(json.dumps(eos_message))

                await self.websocket.close()
                self.connected = False
                logger.info("[ElevenLabs] Disconnected successfully")

        except Exception as e:
            logger.error(f"[ElevenLabs] Error during disconnect: {e}")

    async def send_text(self, text: str) -> None:
        """Send text to ElevenLabs for TTS conversion"""
        if not self.connected or not self.websocket:
            raise Exception("ElevenLabs provider not connected")

        try:
            # Queue the text for processing
            await self.text_queue.put(text)
            logger.debug(f"[ElevenLabs] Text queued for TTS: {text[:50]}...")

        except Exception as e:
            logger.error(f"[ElevenLabs] Error sending text: {e}")
            raise

    async def send_audio(self, audio_data: bytes, sample_rate: int = 16000) -> None:
        """Not implemented for TTS provider - audio input not supported"""
        logger.warning("[ElevenLabs] Audio input not supported for TTS provider")
        pass

    async def send_video(self, video_data: bytes, mime_type: str = "image/jpeg") -> None:
        """Not implemented for TTS provider - video input not supported"""
        logger.warning("[ElevenLabs] Video input not supported for TTS provider")
        pass

    async def get_text_response(self) -> AsyncGenerator[str, None]:
        """Not implemented for TTS provider - text output not supported"""
        logger.warning("[ElevenLabs] Text response not supported for TTS provider")
        return
        yield  # Make it an async generator

    async def set_voice(self, voice_id: str) -> None:
        """Set the voice ID for TTS - not supported, voice is fixed in settings"""
        logger.warning("[ElevenLabs] Voice changes not supported - using voice from settings")
        pass

    async def get_audio_response(self) -> AsyncGenerator[bytes, None]:
        """Get audio chunks from ElevenLabs as they become available"""
        try:
            while self.connected:
                # Wait for audio chunk from queue
                audio_chunk = await self.audio_queue.get()
                if audio_chunk is None:  # End of stream
                    break
                yield audio_chunk

        except Exception as e:
            logger.error(f"[ElevenLabs] Error getting audio response: {e}")
            raise

    async def is_connected(self) -> bool:
        """Check if provider is connected"""
        return self.connected and self.websocket is not None

    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "provider": "elevenlabs",
            "voice_id": self.voice_id,
            "connected": self.connected,
            "model_id": elevenlabs_settings.model_id,
            "output_format": elevenlabs_settings.output_format,
            "sample_rate": elevenlabs_settings.sample_rate
        }

    async def _stream_audio(self):
        """Background task to handle WebSocket communication and audio streaming"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)

                    if data.get("audio"):
                        # Decode base64 audio and put in queue
                        import base64
                        audio_bytes = base64.b64decode(data["audio"])
                        await self.audio_queue.put(audio_bytes)
                        logger.debug(f"[ElevenLabs] Audio chunk received: {len(audio_bytes)} bytes")

                    elif data.get("error"):
                        logger.error(f"[ElevenLabs] WebSocket error: {data['error']}")
                        break

                except json.JSONDecodeError:
                    logger.warning(f"[ElevenLabs] Received non-JSON message: {message[:100]}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("[ElevenLabs] WebSocket connection closed")
        except Exception as e:
            logger.error(f"[ElevenLabs] Error in streaming task: {e}")
            logger.error(f"[ElevenLabs] Exception details: {traceback.format_exc()}")
        finally:
            # Signal end of stream
            await self.audio_queue.put(None)
            self.connected = False

    async def _send_text(self):
        """Background task to send queued text to ElevenLabs WebSocket"""
        try:
            logger.debug("[ElevenLabs] Text sending task started")
            while self.connected:
                try:
                    # Wait for text from queue
                    logger.debug("[ElevenLabs] Waiting for text from queue...")
                    text = await self.text_queue.get()
                    logger.debug(f"[ElevenLabs] Got text from queue: {text[:50]}...")
                    if text is None:  # End of stream signal
                        break

                    # Send text to ElevenLabs
                    message = {
                        "text": text
                    }
                    await self.websocket.send(json.dumps(message))
                    logger.debug(f"[ElevenLabs] Sent text to TTS: {text[:50]}...")

                    # Send EOS after the text to signal completion
                    eos_message = {
                        "text": ""
                    }
                    await self.websocket.send(json.dumps(eos_message))
                    logger.debug("[ElevenLabs] Sent EOS message")

                except Exception as e:
                    logger.error(f"[ElevenLabs] Error sending text to WebSocket: {e}")
                    break

        except Exception as e:
            logger.error(f"[ElevenLabs] Error in text sending task: {e}")
        finally:
            logger.debug("[ElevenLabs] Text sending task ended")