from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import uuid
import wave

from fastapi import WebSocket
from app.models.audio import AudioSession  # ⬅️ domain model

AUDIO_DIR = Path("storage/audio_sessions")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class ConnectionManager:
    """
    Holds per-connection WAV writers. One AudioSession per WebSocket.
    """
    def __init__(self) -> None:
        self.sessions: Dict[WebSocket, AudioSession] = {}

    async def accept(self, ws: WebSocket) -> None:
        await ws.accept()

    def _allocate_path(self, filename: Optional[str]) -> Path:
        if filename:
            if not filename.endswith(".wav"):
                filename = f"{filename}.wav"
            return AUDIO_DIR / filename
        return AUDIO_DIR / f"{uuid.uuid4().hex}.wav"

    def begin(
        self,
        ws: WebSocket,
        *,
        sample_rate: int,
        channels: int,
        sample_width: int,
        filename: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AudioSession:
        sid = session_id or uuid.uuid4().hex
        path = self._allocate_path(filename or sid)
        wf = wave.open(str(path), "wb")
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        sess = AudioSession(
            id=sid,
            path=path,
            wf=wf,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
        )
        self.sessions[ws] = sess
        return sess

    def write(self, ws: WebSocket, chunk: bytes) -> None:
        sess = self.sessions.get(ws)
        if not sess:
            raise RuntimeError("No active audio session. Call begin() first.")
        sess.wf.writeframes(chunk)  # raw s16le bytes

    def end(self, ws: WebSocket) -> Optional[AudioSession]:
        sess = self.sessions.pop(ws, None)
        if sess:
            try:
                sess.wf.close()  # finalize WAV header
            except Exception:
                pass
        return sess

    def disconnect(self, ws: WebSocket) -> None:
        self.end(ws)

manager = ConnectionManager()
