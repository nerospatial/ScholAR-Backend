import asyncio
import base64
import io
from typing import AsyncGenerator, Dict, Any, Optional
import traceback

from google import genai
from app.llm.interfaces.base_llm_provider_interface import BaseLLMProviderInterface
from app.llm.providers.gemini.gemini_settings import gemini_settings
from app.core.log import logger


class GeminiProvider(BaseLLMProviderInterface):
    """
    Gemini Live API provider implementation.
    Based on the minimal Gemini Live API client example.
    """
    
    def __init__(self):
        self.client = None
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self._connected = False
        self._text_response_queue = None
        self._audio_response_queue = None
        self._task_group = None
        self._background_tasks = []
        self.ctx = None

    async def connect(self) -> None:
        """Establish connection to Gemini Live API"""
        try:
            # Initialize Gemini client
            self.client = genai.Client(api_key=gemini_settings.gemini_api_key)

            # Create config based on settings
            config = {"response_modalities": gemini_settings.response_modalities}

            # Initialize queues
            self.audio_in_queue = asyncio.Queue()
            self.out_queue = asyncio.Queue(maxsize=5)
            self._text_response_queue = asyncio.Queue()
            self._audio_response_queue = asyncio.Queue()

            # Properly hold context manager so session doesn’t close immediately
            self._ctx = self.client.aio.live.connect(
                model=gemini_settings.model,
                config=config
            )
            self.session = await self._ctx.__aenter__()

            # Set connected state
            self._connected = True
            logger.info("Connected to Gemini Live API")

        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}")
            logger.error(f"Exception details: {traceback.format_exc()}")
            await self.disconnect()
            raise

    async def start_response_streaming(self) -> None:
        """Start the background tasks for response streaming"""
        if not self._connected or self._background_tasks:
            return
            
        self._background_tasks = [
            asyncio.create_task(self._send_loop()),
            asyncio.create_task(self._receive_loop())
        ]
        logger.info("Response streaming started")

    async def disconnect(self) -> None:
        """Close connection to Gemini Live API"""
        try:
            logger.info("Disconnecting from Gemini Live API...")
            self._connected = False

            # Cancel background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info("Task cancelled successfully")
                    except Exception as e:
                        logger.error(f"Error cancelling task: {e}")
            self._background_tasks.clear()

            # Properly exit context manager
            if self._ctx:
                try:
                    await self._ctx.__aexit__(None, None, None)
                    logger.info("Gemini session closed via context manager")
                except Exception as e:
                    logger.error(f"Error closing session: {e}")
                self._ctx = None
                self.session = None

            # Clean up queues
            self.audio_in_queue = None
            self.out_queue = None
            self._text_response_queue = None
            self._audio_response_queue = None

            logger.info("Disconnected from Gemini Live API")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            logger.error(f"Exception details: {traceback.format_exc()}")

    async def send_text(self, text: str) -> None:
        """Send text input to Gemini"""
        if not self._connected:
            raise RuntimeError("Provider not connected")
            
        # Start response streaming on first input if not already started
        await self.start_response_streaming()
        
        # For Gemini Live API, text is typically sent as part of the conversation flow
        # This could be implemented as a text message in the queue
        await self.out_queue.put({
            "type": "text",
            "data": text
        })
        
    async def send_audio(self, audio_data: bytes, sample_rate: int = 16000) -> None:
        """Send audio input to Gemini"""
        if not self._connected:
            raise RuntimeError("Provider not connected")
            
        # Start response streaming on first audio input if not already started
        await self.start_response_streaming()
            
        # Format audio data according to Gemini Live API requirements
        audio_msg = {
            "data": audio_data, 
            "mime_type": f"audio/pcm;rate={sample_rate}"
        }
        await self.out_queue.put(audio_msg)
        
    async def send_video(self, video_data: bytes, mime_type: str = "image/jpeg") -> None:
        """Send video/image input to Gemini"""
        if not self._connected:
            raise RuntimeError("Provider not connected")
            
        # Start response streaming on first video input if not already started
        await self.start_response_streaming()
            
        # Convert video data to base64 format as required by Gemini
        video_msg = {
            "mime_type": mime_type,
            "data": base64.b64encode(video_data).decode()
        }
        await self.out_queue.put(video_msg)
        
    async def get_text_response(self) -> AsyncGenerator[str, None]:
        """Get text responses from Gemini as async generator"""
        if not self._connected:
            raise RuntimeError("Provider not connected")
            
        while self._connected:
            try:
                # Wait for text response with timeout
                text_chunk = await asyncio.wait_for(
                    self._text_response_queue.get(), 
                    timeout=1.0
                )
                yield text_chunk
            except asyncio.TimeoutError:
                # Allow checking connection status
                continue
            except Exception as e:
                logger.error(f"Error getting text response: {e}")
                break
                
    async def get_audio_response(self) -> AsyncGenerator[bytes, None]:
        """Get audio responses from Gemini as async generator"""
        if not self._connected:
            raise RuntimeError("Provider not connected")
            
        while self._connected:
            try:
                # Wait for audio response with timeout
                audio_chunk = await asyncio.wait_for(
                    self._audio_response_queue.get(), 
                    timeout=1.0
                )
                yield audio_chunk
            except asyncio.TimeoutError:
                # Allow checking connection status
                continue
            except Exception as e:
                logger.error(f"Error getting audio response: {e}")
                break
                
    async def is_connected(self) -> bool:
        """Check if provider is connected"""
        return self._connected and self.session is not None
        
    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "connected": self._connected,
            "model": gemini_settings.model,
            "response_modalities": gemini_settings.response_modalities,
            "audio_format": gemini_settings.audio_format,
            "sample_rates": {
                "send": gemini_settings.send_sample_rate,
                "receive": gemini_settings.receive_sample_rate
            }
        }
        
    async def _send_loop(self):
        """Background task to send messages to Gemini (based on working SDK example)"""
        logger.info("Send loop started")
        try:
            while self._connected:
                try:
                    # Wait for messages from queue
                    msg = await self.out_queue.get()
                    
                    if not self._connected:
                        break
                    
                    if msg.get("type") == "text":
                        # Handle text messages
                        logger.debug(f"Sending text: {msg['data']}")
                        # For text, we can send as input
                        await self.session.send_realtime_input(text=msg['data'])
                        
                    elif "mime_type" in msg:
                        if msg["mime_type"].startswith("image"):
                            logger.debug(f"Sending image data: {len(msg.get('data', ''))} chars")
                            await self.session.send_realtime_input(media=msg)
                        elif msg["mime_type"].startswith("audio"):
                            logger.debug(f"Sending audio data: {len(msg.get('data', b''))} bytes")
                            await self.session.send_realtime_input(audio=msg)
                    else:
                        logger.warning(f"Unknown message format: {msg}")
                            
                except asyncio.CancelledError:
                    logger.info("Send loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error processing message in send loop: {e}")
                    # Don't continue on connection errors - break the loop
                    if "sent 1000" in str(e) or "received 1000" in str(e):
                        logger.info("Connection closed, exiting send loop")
                        self._connected = False
                        break
                        
        except Exception as e:
            logger.error(f"Fatal error in send loop: {e}")
        finally:
            logger.info("Send loop ended")

    async def _receive_loop(self):
        logger.info("Receive loop started")
        try:
            while self._connected:
                try:
                    async for response in self.session.receive():
                        if not self._connected:
                            break

                        # Handle audio (PCM16 chunks @ 24kHz)
                        if response.data:
                            logger.info(f"Received audio chunk: {len(response.data)} bytes")
                            await self._audio_response_queue.put(response.data)

                        # Handle text (only if Gemini actually sends text parts)
                        if hasattr(response, "output") and response.output:
                            for part in response.output:
                                if getattr(part, "text", None):
                                    logger.info(f"Received text chunk: {part.text[:100]}...")
                                    await self._text_response_queue.put(part.text)

                except asyncio.CancelledError:
                    logger.info("Receive loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in receive loop: {e}")
                    self._connected = False
                    break
        finally:
            logger.info("Receive loop ended")
            self._connected = False