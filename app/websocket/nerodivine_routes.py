# app/websocket/nerodivine_routes.py
# NERODIVINE WS BACKEND — FIXED FOR RELIABLE ESP32/EMBEDDED PLAYBACK
# - 24 kHz mono voice pipeline
# - ElevenLabs -> PCM 24k → (server) Opus encode → single-frame WS packets @20ms
# - Fallback: raw PCM 24k if opuslib unavailable

import asyncio
import json
import os
import uuid
import traceback
import time
from typing import Dict, Any, Optional

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedOK

from app.core.log import logger

# Optional deps
try:
    from elevenlabs.client import AsyncElevenLabs
    ELEVENLABS_AVAILABLE = True
except Exception:
    ELEVENLABS_AVAILABLE = False
    logger.warning("elevenlabs not installed. `pip install elevenlabs`")

try:
    import opuslib
    OPUS_AVAILABLE = True
except Exception:
    OPUS_AVAILABLE = False
    logger.warning("opuslib not installed. `pip install opuslib`")

# ---------- CONSTANTS ----------
SR = 24000
CHANNELS = 1
FRAME_MS = 20
FRAME_SAMPLES = SR * FRAME_MS // 1000  # 480 for 24k / 20ms
SAMPLE_WIDTH_BYTES = 2                 # S16_LE coming from ElevenLabs PCM
FRAME_BYTES = FRAME_SAMPLES * SAMPLE_WIDTH_BYTES * CHANNELS

# Voice text template (simple)
NERODIVINE_STORY_TEMPLATE = (

    """
    
    हarii, मेरी छोटी सी गोपिका,
    आज आँगन में बैठो, मैं तुम्हें अपनी बचपन की एक शरारत सुनाऊँ।
    
    एक दिन मैं यमुना किनारे बैठा था।
    हवा में माखन की खुशबू थी,
    और मेरे चारों तरफ़ नीली-पीली तितलियाँ उड़ रही थीं।
    मैंने सोचा — “अरे, ये तितलियाँ तो मुझसे ज़्यादा आज़ाद हैं!”
    
    मैंने एक तितली को धीरे से पकड़ा,
    और बोला — “ज़रा रुक जाओ, तुम्हारे पंखों से खेलूँ।”
    पर जैसे ही मैंने पकड़ा, वो काँपने लगी, डर गई।
    मुझे बुरा लगा, बहुत बुरा।
    
    """

)

class NerodivineSession:
    def __init__(self, websocket: WebSocket, session_id: Optional[str]):
        self.websocket = websocket
        self.session_id = session_id
        self.name: Optional[str] = None
        self.story_sent = False

        self.opus_encoder = None
        if OPUS_AVAILABLE:
            enc = opuslib.Encoder(fs=SR, channels=CHANNELS, application=opuslib.APPLICATION_VOIP)
            # Stable packet sizes & good voice quality
            enc.bitrate = 48000          # 48 kbps CBR
            enc.vbr = 0                  # CBR
            enc.complexity = 10
            enc.signal = opuslib.SIGNAL_VOICE
            # Disable FEC/DTX (avoid size variance / gaps)
            try:
                enc.inband_fec = 0
                enc.dtx = 0
            except Exception:
                pass
            self.opus_encoder = enc

    async def handle_message(self, message: Dict[str, Any]):
        try:
            t = message.get("type")
            if t == "ready":
                await self._handle_ready(message)
            else:
                await self._send_error(f"Unknown message type: {t}")
        except Exception as e:
            logger.error("handle_message error: %s", e)
            await self._send_error(f"Error: {e}")

    async def _handle_ready(self, message: Dict[str, Any]):
        name = (message.get("name") or "").strip()
        if not name:
            await self._send_error("Name is required in ready message")
            return
        if not self.session_id:
            await self._send_error("Session not properly initialized")
            return

        self.name = name
        logger.info("Nerodivine ready: session=%s name=%s", self.session_id, self.name)

        await self._send_json({"type": "session_initialized", "session_id": self.session_id})

        # personalize + stream
        text = NERODIVINE_STORY_TEMPLATE.replace("${name}", self.name)
        try:
            await self._stream_story_from_elevenlabs(text)
            self.story_sent = True
        except Exception as e:
            logger.error("Story stream error: %s", e)
            await self._send_error(f"Failed to generate story audio: {e}")

    async def _stream_story_from_elevenlabs(self, text: str):
        if not ELEVENLABS_AVAILABLE:
            raise RuntimeError("ElevenLabs SDK not available")

        api_key = os.getenv("ELEVEN_LABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVEN_LABS_API_KEY not set")

        voice_id = os.getenv("ELEVEN_LABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # default voice

        client = AsyncElevenLabs(api_key=api_key)

        # Tell client what’s coming
        await self._send_json({
            "type": "audio_start",
            "message": f"Starting story for {self.name}",
            "encoding": "opus" if self.opus_encoder else "pcm",
            "sample_rate": SR,
            "channels": CHANNELS,
            "frame_ms": FRAME_MS
        })

        # Request PCM 24k from ElevenLabs; we control Opus encoding & pacing
        # (Alternative: use 'opus_48000_64' and forward frames; we keep PCM for predictable framing.)
        stream = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="pcm_24000",
            voice_settings={"stability": 0.5, "similarity_boost": 0.5, "speed": 0.7}
        )

        # Consume async stream of raw PCM bytes; reframe to 20ms(480) slices
        pcm_acc = bytearray()
        pace_next = time.monotonic()

        async for chunk in stream:
            if not chunk:
                continue
            pcm_acc.extend(chunk)

            while len(pcm_acc) >= FRAME_BYTES:
                frame = pcm_acc[:FRAME_BYTES]
                del pcm_acc[:FRAME_BYTES]

                if self.opus_encoder:
                    try:
                        payload = self.opus_encoder.encode(bytes(frame), FRAME_SAMPLES)
                    except Exception as e:
                        logger.error("Opus encode error: %s", e)
                        continue
                    # real-time pacing (20ms per frame)
                    pace_next = self._pace_20ms(pace_next)
                    if self._ws_connected():
                        await self.websocket.send_bytes(payload)
                    else:
                        logger.warning("WS disconnected during Opus send")
                        return
                else:
                    # Fallback: send raw PCM S16LE @ 24k
                    pace_next = self._pace_20ms(pace_next)
                    if self._ws_connected():
                        await self.websocket.send_bytes(bytes(frame))
                    else:
                        logger.warning("WS disconnected during PCM send")
                        return

        # Flush tail (pad to full frame if any)
        if pcm_acc:
            pad = FRAME_BYTES - len(pcm_acc)
            frame = bytes(pcm_acc) + (b"\x00" * pad)
            if self.opus_encoder:
                try:
                    payload = self.opus_encoder.encode(frame, FRAME_SAMPLES)
                    pace_next = self._pace_20ms(pace_next)
                    if self._ws_connected():
                        await self.websocket.send_bytes(payload)
                except Exception as e:
                    logger.error("Opus encode tail error: %s", e)
            else:
                pace_next = self._pace_20ms(pace_next)
                if self._ws_connected():
                    await self.websocket.send_bytes(frame)

        # End marker
        await self._send_json({"type": "end", "message": "Story completed"})

    # ---------- helpers ----------
    def _pace_20ms(self, next_deadline: float) -> float:
        period = FRAME_MS / 1000.0
        now = time.monotonic()
        if now < next_deadline:
            time.sleep(next_deadline - now)
            next_deadline += period
        else:
            # drift correction
            next_deadline = now + period
        return next_deadline

    def _ws_connected(self) -> bool:
        return self.websocket.client_state == WebSocketState.CONNECTED

    async def _send_json(self, obj: Dict[str, Any]):
        if self._ws_connected():
            await self.websocket.send_json(obj)

    async def _send_error(self, msg: str):
        await self._send_json({"type": "error", "message": msg})

def register_nerodivine_ws_routes(app: FastAPI) -> None:
    sessions: Dict[str, NerodivineSession] = {}

    @app.websocket("/nerodivine/ws/queries")
    async def nerodivine_ws(ws: WebSocket):
        await ws.accept()
        session = NerodivineSession(ws, None)
        await session._send_json({
            "type": "connected",
            "message": "Connected to Nerodivine. Send a 'ready' message with your name to begin."
        })
        logger.info("Nerodivine WS connection established")
        sid: Optional[str] = None

        try:
            while True:
                try:
                    msg = await ws.receive_text()
                    data = json.loads(msg)
                except ValueError:
                    # if binary/text mix arrives unexpectedly, ignore
                    continue

                if data.get("type") == "ready" and not sid:
                    sid = str(uuid.uuid4())
                    session.session_id = sid
                    sessions[sid] = session
                    logger.info("Session %s created", sid)

                await session.handle_message(data)

        except ConnectionClosedOK:
            logger.info("WS normal close: %s", sid or "no-session")
        except Exception as e:
            logger.error("WS error: %s", e)
            logger.debug("Trace: %s", traceback.format_exc())
        finally:
            if sid and sid in sessions:
                del sessions[sid]
                logger.info("Session cleaned up: %s", sid)
            elif not sid:
                logger.info("Connection closed before session created")
