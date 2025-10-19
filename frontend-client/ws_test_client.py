# -*- coding: utf-8 -*-
# Frontend Testing Client for ScholAR Backend WebSocket
#
# Requires:
#   pip install websockets pyaudio opencv-python pillow asyncio
#
# Usage:
#   python ws_test_client.py --mode audio
#   python ws_test_client.py --mode video
#   python ws_test_client.py --mode text

import asyncio
import base64
import io
import json
import sys
import traceback
import argparse
from typing import Optional

import cv2
import pyaudio
import PIL.Image
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

# Configuration matching backend settings
WEBSOCKET_URL = "ws://localhost:8000/ws/queries"
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# PyAudio instance
pya = pyaudio.PyAudio()


class ScholARTestClient:
    def __init__(self, mode="audio"):
        self.mode = mode
        self.websocket = None
        self.audio_stream_in = None
        self.audio_stream_out = None
        self.video_capture = None
        self.running = False
        self.session_active = False
        
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(WEBSOCKET_URL)
            print(f"Connected to {WEBSOCKET_URL}")
            
            # Wait for READY message
            ready_msg = await self.websocket.recv()
            print(f"Server says: {ready_msg}")
            
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from WebSocket and cleanup resources"""
        self.running = False
        
        if self.session_active:
            await self.stop_session()
            
        if self.audio_stream_in:
            self.audio_stream_in.close()
        if self.audio_stream_out:
            self.audio_stream_out.close()
        if self.video_capture:
            self.video_capture.release()
            
        if self.websocket:
            await self.websocket.close()
            
        print("Disconnected and cleaned up resources")
        
    async def start_session(self):
        """Start a query session"""
        if not self.websocket:
            print("Not connected to server")
            return False
            
        try:
            await self.websocket.send(json.dumps({"type": "START_QUERY_SESSION"}))
            self.session_active = True
            print("Session started")
            return True
        except Exception as e:
            print(f"Failed to start session: {e}")
            return False
            
    async def stop_session(self):
        """Stop the query session"""
        if not self.websocket or not self.session_active:
            return
            
        try:
            await self.websocket.send(json.dumps({"type": "STOP_QUERY_SESSION"}))
            self.session_active = False
            print("Session stopped")
        except Exception as e:
            print(f"Error stopping session: {e}")
            
    async def send_text(self, text: str):
        """Send text message to server"""
        if not self.websocket or not self.session_active:
            print("Session not active")
            return
            
        message = {
            "type": "text",
            "data": text
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"Sent text: {text}")
        except Exception as e:
            print(f"Failed to send text: {e}")
            
    async def send_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to server"""
        if not self.websocket or not self.session_active:
            return
            
        audio_b64 = base64.b64encode(audio_data).decode()
        message = {
            "type": "audio",
            "data": audio_b64,
            "sample_rate": SEND_SAMPLE_RATE
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            print(f"Failed to send audio: {e}")
            
    async def send_video_frame(self, frame):
        """Send video frame to server"""
        if not self.websocket or not self.session_active:
            return
            
        try:
            # Convert frame to RGB and resize
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(frame_rgb)
            img.thumbnail([1024, 1024])
            
            # Convert to JPEG bytes
            buf = io.BytesIO()
            img.save(buf, format="jpeg")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            
            message = {
                "type": "video",
                "data": img_b64,
                "mime_type": "image/jpeg"
            }
            
            await self.websocket.send(json.dumps(message))
            
        except Exception as e:
            print(f"Failed to send video frame: {e}")
            
    async def capture_audio(self):
        """Capture audio from microphone and stream to server"""
        try:
            # Setup microphone
            mic_info = pya.get_default_input_device_info()
            self.audio_stream_in = pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            
            print("🎤 Audio capture started. Speak into your microphone...")
            
            while self.running and self.session_active:
                try:
                    # Read audio chunk
                    audio_data = self.audio_stream_in.read(CHUNK_SIZE, exception_on_overflow=False)
                    await self.send_audio_chunk(audio_data)
                    await asyncio.sleep(0.01)  # Small delay
                    
                except Exception as e:
                    print(f"Audio capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to setup audio capture: {e}")
        finally:
            if self.audio_stream_in:
                self.audio_stream_in.close()
                
    async def capture_video(self):
        """Capture video from camera and stream to server"""
        try:
            self.video_capture = cv2.VideoCapture(0)
            if not self.video_capture.isOpened():
                print("Failed to open camera")
                return
                
            print("📹 Video capture started...")
            
            while self.running and self.session_active:
                ret, frame = self.video_capture.read()
                if ret:
                    await self.send_video_frame(frame)
                    
                await asyncio.sleep(1.0)  # Send frame every second
                
        except Exception as e:
            print(f"Video capture error: {e}")
        finally:
            if self.video_capture:
                self.video_capture.release()
                
    async def play_audio_chunk(self, audio_data: bytes):
        """Play received audio chunk"""
        if not self.audio_stream_out:
            # Setup audio output
            self.audio_stream_out = pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
            )
            
        try:
            self.audio_stream_out.write(audio_data)
        except Exception as e:
            print(f"Audio playback error: {e}")
            
    async def handle_responses(self):
        """Handle incoming messages from server"""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=0.1)
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(message)
                        await self.process_response(data)
                    except json.JSONDecodeError:
                        # Handle plain text messages
                        print(f"📨 Server: {message}")
                        
                except asyncio.TimeoutError:
                    continue
                except (ConnectionClosedError, ConnectionClosedOK):
                    print("Server disconnected")
                    break
                    
        except Exception as e:
            print(f"Response handler error: {e}")
            
    async def process_response(self, data: dict):
        """Process structured responses from server"""
        msg_type = data.get("type", "")
        
        if msg_type == "text_response":
            print(f"🤖 AI: {data.get('data', '')}")
            
        elif msg_type == "audio_response":
            # Decode and play audio
            try:
                audio_b64 = data.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)
                await self.play_audio_chunk(audio_bytes)
            except Exception as e:
                print(f"Failed to play audio: {e}")
                
        elif msg_type == "ERROR":
            print(f"❌ Error: {data.get('message', 'Unknown error')}")
            
        elif data.get("type") in ["QUERY_RESPONDER_SPEAKING", "QUERY_RESPONDER_DONE", "SESSION_ENDED"]:
            print(f"📡 Status: {data.get('type')}")
            
        else:
            print(f"📨 Unknown response: {data}")
            
    async def text_mode(self):
        """Interactive text chat mode"""
        print("\n💬 Text chat mode. Type 'quit' to exit, 'start' to begin session.")
        
        while self.running:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'start':
                    await self.start_session()
                elif user_input.lower() == 'stop':
                    await self.stop_session()
                elif user_input and self.session_active:
                    await self.send_text(user_input)
                elif user_input and not self.session_active:
                    print("Start session first with 'start'")
                    
            except KeyboardInterrupt:
                break
                
    async def audio_mode(self):
        """Audio streaming mode"""
        print("\n🎤 Audio mode. Press Enter to start session, Ctrl+C to exit.")
        input("Press Enter to start...")
        
        await self.start_session()
        
        # Start audio capture and response handling
        audio_task = asyncio.create_task(self.capture_audio())
        
        try:
            # Wait for user to stop
            await asyncio.get_event_loop().run_in_executor(None, input, "\nPress Enter to stop...\n")
        except KeyboardInterrupt:
            pass
            
        audio_task.cancel()
        
    async def video_mode(self):
        """Video streaming mode"""
        print("\n📹 Video mode. Press Enter to start session, Ctrl+C to exit.")
        input("Press Enter to start...")
        
        await self.start_session()
        
        # Start video capture
        video_task = asyncio.create_task(self.capture_video())
        
        try:
            await asyncio.get_event_loop().run_in_executor(None, input, "\nPress Enter to stop...\n")
        except KeyboardInterrupt:
            pass
            
        video_task.cancel()
        
    async def run(self):
        """Main run loop"""
        if not await self.connect():
            return
            
        self.running = True
        
        # Start response handler
        response_task = asyncio.create_task(self.handle_responses())
        
        try:
            if self.mode == "text":
                await self.text_mode()
            elif self.mode == "audio":
                await self.audio_mode()
            elif self.mode == "video":
                await self.video_mode()
            else:
                print(f"Unknown mode: {self.mode}")
                
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.running = False
            response_task.cancel()
            await self.disconnect()


async def main():
    parser = argparse.ArgumentParser(description="ScholAR WebSocket Test Client")
    parser.add_argument(
        "--mode",
        type=str,
        default="text",
        choices=["text", "audio", "video"],
        help="Test mode: text chat, audio streaming, or video streaming"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=WEBSOCKET_URL,
        help="WebSocket server URL"
    )
    
    args = parser.parse_args()
    
    # Update URL if provided
    global WEBSOCKET_URL
    WEBSOCKET_URL = args.url
    
    print(f"🚀 Starting ScholAR Test Client in {args.mode} mode")
    print(f"🔗 Connecting to: {WEBSOCKET_URL}")
    
    client = ScholARTestClient(mode=args.mode)
    
    try:
        await client.run()
    except Exception as e:
        print(f"Client error: {e}")
        traceback.print_exc()
    finally:
        pya.terminate()


if __name__ == "__main__":
    asyncio.run(main())