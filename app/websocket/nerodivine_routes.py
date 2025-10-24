# app/websocket/nerodivine_routes.py
import asyncio
import json
import base64
import traceback
import uuid
import httpx
import os
import io
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedOK
from app.core.log import logger

# Try to import opuslib for Opus encoding
try:
    import opuslib
    OPUS_AVAILABLE = True
except ImportError:
    OPUS_AVAILABLE = False
    logger.warning("opuslib not available. Install with: pip install opuslib")

NERODIVINE_STORY_TEMPLATE = """
एक बार की बात है, वृंदावन के सुंदर गांव में एक छोटा सा बच्चा रहता था जिसका नाम ${name} था। 
${name} बहुत ही प्यारा और नटखट बच्चा था, बिल्कुल कन्हैया की तरह।

एक दिन ${name} अपनी माँ से कहता है, "माँ, मैं गोपालों के साथ गायों को चराने जाऊंगा।" 
माँ कहती है, "${name}, जल्दी वापस आ जाना और किसी अजनबी से बात नहीं करना।"

जंगल में जाते समय ${name} को एक सुंदर तितली दिखी। वह तितली के पीछे-पीछे भागने लगा। 
अचानक उसे एक जादुई बांसुरी मिली जो पेड़ के नीचे चमक रही थी।

जैसे ही ${name} ने बांसुरी उठाई, उसमें से मधुर संगीत निकलने लगा। 
सभी जानवर - गाय, मोर, हिरण - सब ${name} के पास आ गए और खुशी से नाचने लगे।

${name} ने सीखा कि प्रेम और दया से सभी को खुश किया जा सकता है। 
वह खुशी-खुशी अपने घर वापस गया और माँ को सारी कहानी सुनाई।

इस तरह ${name} का दिन बहुत खुशी से बीता। समाप्त।
"""


class NerodivineSession:
    """Manages a nerodivine WebSocket session for personalized story telling"""
    
    def __init__(self, websocket: WebSocket, session_id: Optional[str]):
        self.websocket = websocket
        self.session_id = session_id  # Can be None initially
        self.name = None
        self.story_sent = False
        
        # Initialize Opus encoder if available
        if OPUS_AVAILABLE:
            self.opus_encoder = opuslib.Encoder(
                fs=22050,  # Sample rate
                channels=1,  # Mono
                application=opuslib.APPLICATION_AUDIO  # For general audio
            )
        else:
            self.opus_encoder = None
        
    async def handle_message(self, message: Dict[str, Any]):
        """Process incoming WebSocket message"""
        try:
            message_type = message.get("type")
            
            if message_type == "ready":
                await self._handle_ready_message(message)
            else:
                logger.warning(f"Unknown message type for nerodivine: {message_type}")
                await self._send_error(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling nerodivine message: {e}")
            await self._send_error(f"Error processing message: {str(e)}")
            
    async def _handle_ready_message(self, message: Dict[str, Any]):
        """Handle ready message with name parameter and send session_id"""
        name = message.get("name", "").strip()
        
        if not name:
            await self._send_error("Name is required in ready message")
            return
            
        if not self.session_id:
            await self._send_error("Session not properly initialized")
            return
            
        self.name = name
        logger.info(f"Received ready message for nerodivine session {self.session_id} with name: {name}")
        
        # Send session ID to client now that we have the name
        await self._send_json_message({
            "type": "session_initialized",
            "session_id": self.session_id,
           })
        
        # Personalize and send story to Eleven Labs
        await self._generate_and_stream_story()
        
    async def _generate_and_stream_story(self):
        """Personalize story and stream audio from Eleven Labs"""
        if not self.name:
            await self._send_error("Name not set")
            return
            
        # Personalize the story
        personalized_story = NERODIVINE_STORY_TEMPLATE.replace("${name}", self.name)
        
        try:
            # Call Eleven Labs API and stream response
            await self._stream_audio_from_elevenlabs(personalized_story)
            self.story_sent = True
            
        except Exception as e:
            logger.error(f"Error generating story audio: {e}")
            await self._send_error(f"Failed to generate story audio: {str(e)}")
            
    async def _stream_audio_from_elevenlabs(self, text: str):
        """Stream audio from Eleven Labs API, convert PCM to Opus, and stream binary"""
        # Get environment variables
        ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
        VOICE_ID = os.getenv("ELEVEN_LABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice ID
        
        if not ELEVEN_LABS_API_KEY:
            raise Exception("ELEVEN_LABS_API_KEY environment variable not set")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
        
        headers = {
            "Accept": "audio/wav",  # Request PCM format
            "Content-Type": "application/json",
            "xi-api-key": ELEVEN_LABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            },
            "output_format": "pcm_22050"  # PCM format, 22.05kHz
        }
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream('POST', url, headers=headers, json=data) as response:
                    if response.status_code != 200:
                        raise Exception(f"Eleven Labs API error: {response.status_code}")
                        
                    # Send audio start message as JSON
                    await self._send_json_message({
                        "type": "audio_start",
                        "message": f"Starting story for {self.name}",
                        "encoding": "opus" if OPUS_AVAILABLE else "pcm",
                        "sample_rate": 22050,
                        "channels": 1
                    })
                    
                    # Skip WAV header (first 44 bytes) to get raw PCM data
                    header_skipped = False
                    pcm_buffer = b""
                    
                    async for chunk in response.aiter_bytes(1024):
                        if chunk:
                            if not header_skipped:
                                # Skip WAV header
                                if len(pcm_buffer + chunk) >= 44:
                                    combined = pcm_buffer + chunk
                                    raw_pcm = combined[44:]  # Skip 44-byte WAV header
                                    header_skipped = True
                                    if raw_pcm:
                                        await self._process_and_send_audio(raw_pcm)
                                else:
                                    pcm_buffer += chunk
                            else:
                                # Process raw PCM data
                                await self._process_and_send_audio(chunk)
                    
                    # Send audio end message as JSON
                    await self._send_json_message({
                        "type": "end",
                        "message": "Story completed"
                    })
                    
        except Exception as e:
            logger.error(f"Error streaming from Eleven Labs: {e}")
            raise
    
    async def _process_and_send_audio(self, pcm_data: bytes):
        """Process PCM data: encode to Opus if available, otherwise send raw PCM"""
        if OPUS_AVAILABLE and self.opus_encoder:
            try:
                # Encode PCM to Opus (frame size: 960 samples for 22.05kHz)
                frame_size = 960 * 2  # 960 samples * 2 bytes per sample (16-bit)
                
                # Process in chunks
                for i in range(0, len(pcm_data), frame_size):
                    frame = pcm_data[i:i + frame_size]
                    
                    # Pad last frame if necessary
                    if len(frame) < frame_size:
                        frame += b'\x00' * (frame_size - len(frame))
                    
                    # Encode to Opus
                    opus_data = self.opus_encoder.encode(frame, frame_size // 2)
                    
                    # Send binary Opus data directly
                    await self.websocket.send_bytes(opus_data)
                    
            except Exception as e:
                logger.error(f"Error encoding to Opus: {e}")
                # Fallback to raw PCM
                await self.websocket.send_bytes(pcm_data)
        else:
            # Send raw PCM data if Opus not available
            await self.websocket.send_bytes(pcm_data)
            
    async def _send_message(self, message: Any):
        """Send message to WebSocket client"""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            if isinstance(message, str):
                await self.websocket.send_text(message)
            else:
                await self.websocket.send_json(message)
    
    async def _send_json_message(self, message: Dict[str, Any]):
        """Send JSON message to WebSocket client"""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_json(message)
                
    async def _send_error(self, error_msg: str):
        """Send error message to client"""
        await self._send_message({
            "type": "error",
            "message": error_msg
        })


def register_nerodivine_ws_routes(app: FastAPI) -> None:
    """Register nerodivine WebSocket routes"""
    # Store active nerodivine sessions
    nerodivine_sessions: Dict[str, NerodivineSession] = {}

    @app.websocket("/nerodivine/ws/queries")
    async def nerodivine_websocket_endpoint(ws: WebSocket):
        await ws.accept()
        
        # Create temporary session without session_id yet
        session = NerodivineSession(ws, None)  # No session_id initially
        
        # Send welcome message (no session_id)
        await session._send_message({
            "type": "connected",
            "message": "Connected to Nerodivine. Send a 'ready' message with your name to begin."
        })
        
        logger.info(f"Nerodivine WebSocket connection established")
        
        session_id = None  # Will be set when ready message received
        
        try:
            while True:
                # Wait for messages from client
                try:
                    message = await ws.receive_json()
                    # Handle ready message specially to generate session_id
                    if message.get("type") == "ready" and not session_id:
                        # Generate session_id only now
                        session_id = str(uuid.uuid4())
                        session.session_id = session_id
                        
                        # Add to memory map only now
                        nerodivine_sessions[session_id] = session
                        logger.info(f"Session {session_id} added to memory map after ready message")
                    
                    await session.handle_message(message)
                except ValueError:
                    # Try to receive as text
                    text_message = await ws.receive_text()
                    await session.handle_message({"type": "text", "data": text_message})
                    
        except WebSocketDisconnect:
            logger.info(f"Nerodivine WebSocket disconnected: {session_id or 'no session'}")
        except ConnectionClosedOK:
            logger.info(f"Nerodivine WebSocket connection closed normally: {session_id or 'no session'}")
        except Exception as e:
            logger.error(f"Nerodivine WebSocket error: {e}")
        finally:
            # Cleanup session only if session_id exists and is in memory map
            if session_id and session_id in nerodivine_sessions:
                del nerodivine_sessions[session_id]
                logger.info(f"Nerodivine session cleaned up: {session_id}")
            elif not session_id:
                logger.info("Connection closed before session was created")