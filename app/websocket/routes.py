# app/websocket/routes.py (inside register_ws_routes)
import asyncio
import json
import base64
import traceback
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedOK
from app.core.log import logger
from app.llm.providers.llm_provider_factory import get_llm_provider, LLMProviderType
from app.websocket.helpers.messages import (
    get_ready_message,
    get_start_query_session_message,
    get_stop_query_session_message,
    get_query_responder_speaking_message,
    get_query_responder_done_message,
    get_error_message,
    get_user_interrupted_message,
    get_session_ended_message
)


class WebSocketSession:
    """Manages a single WebSocket session with LLM provider"""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.llm_provider = None
        self.active = False
        self.background_tasks = []
        self.response_streaming_started = False
        
    async def start_llm_session(self):
        """Start LLM provider connection"""
        try:
            if self.llm_provider and self.active:
                logger.warning(f"Session already active for {self.session_id}")
                return

            self.llm_provider = get_llm_provider(LLMProviderType.GEMINI)
            await self.llm_provider.connect()
            self.active = True

            # Don't start response streaming tasks immediately
            # They will be started when we receive first user input

            await self._send_message(get_start_query_session_message())
            logger.info(f"LLM session started for WebSocket {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to start LLM session: {e}")
            logger.error(f"Exception details: {traceback.format_exc()}")
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
        """Stop LLM provider connection and cleanup"""
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
                
            await self._send_message(get_session_ended_message())
            logger.info(f"LLM session stopped for WebSocket {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error stopping LLM session: {e}")
            
    async def _start_response_streaming(self):
        """Start response streaming tasks on first user input"""
        if not self.response_streaming_started and self.llm_provider and self.active:
            # Start LLM provider response streaming
            await self.llm_provider.start_response_streaming()
            
            # Start WebSocket response streaming tasks
            self.background_tasks = [
                asyncio.create_task(self._stream_text_responses()),
                asyncio.create_task(self._stream_audio_responses())
            ]
            self.response_streaming_started = True
            logger.info(f"Response streaming started for session {self.session_id}")
            
    async def handle_message(self, message: Dict[str, Any]):
        """Process incoming WebSocket message"""
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
                logger.warning(f"Unknown message type: {message_type}")
                await self._send_error(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(f"Error processing message: {str(e)}")
            
    async def _handle_text_message(self, message: Dict[str, Any]):
        """Handle text input from client"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return
            
        text = message.get("data", "")
        if text:
            await self.llm_provider.send_text(text)
            
    async def _handle_audio_message(self, message: Dict[str, Any]):
        """Handle audio input from client"""
        if not self.llm_provider or not self.active:
            await self._send_error("Session not active")
            return
            
        audio_data = message.get("data", "")
        sample_rate = message.get("sample_rate", 16000)
        
        if audio_data:
            # Decode base64 audio data
            try:
                audio_bytes = base64.b64decode(audio_data)
                await self.llm_provider.send_audio(audio_bytes, sample_rate)
            except Exception as e:
                await self._send_error(f"Invalid audio data: {str(e)}")
                
    async def _handle_video_message(self, message: Dict[str, Any]):
        """Handle video/image input from client"""
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
            # Could implement interrupt handling in provider
            logger.info(f"User interrupted session {self.session_id}")
            
    async def _stream_text_responses(self):
        """Stream text responses from LLM to WebSocket"""
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
            logger.error(f"Error streaming text responses: {e}")

    async def _stream_audio_responses(self):
        try:
            if not self.llm_provider:
                return

            await self._send_message(get_query_responder_speaking_message())

            async for audio_chunk in self.llm_provider.get_audio_response():
                if not self.active:
                    break

                audio_b64 = base64.b64encode(audio_chunk).decode()
                await self._send_message({
                    "type": "audio_response",
                    "data": audio_b64,
                    "sample_rate": 24000,  # Gemini default
                    "encoding": "pcm_s16le",
                    "channels": 1
                })

            await self._send_message(get_query_responder_done_message())

        except Exception as e:
            logger.error(f"Error streaming audio responses: {e}")
            await self._send_message(get_query_responder_done_message())

    async def _send_message(self, message: Any):
        """Send message to WebSocket client"""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            if isinstance(message, str):
                await self.websocket.send_text(message)
            else:
                await self.websocket.send_json(message)
                
    async def _send_error(self, error_msg: str):
        """Send error message to client"""
        await self._send_message({
            "type": get_error_message(),
            "message": error_msg
        })


def register_ws_routes(app: FastAPI) -> None:
    # Store active sessions
    active_sessions: Dict[str, WebSocketSession] = {}

    @app.websocket("/ws/queries")
    async def queries_websocket_endpoint(ws: WebSocket):
        await ws.accept()
        session_id = str(id(ws))
        
        # Create session
        session = WebSocketSession(ws, session_id)
        active_sessions[session_id] = session
        
        # Send ready message
        await session._send_message(get_ready_message())
        logger.info(f"WebSocket connection established: {session_id}")
        
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
            logger.info(f"WebSocket disconnected: {session_id}")
        except ConnectionClosedOK:
            logger.info(f"WebSocket connection closed normally: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup session
            if session_id in active_sessions:
                await active_sessions[session_id].stop_llm_session()
                del active_sessions[session_id]