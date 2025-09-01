from typing import Optional
from fastapi import WebSocket
from app.websocket.connection import manager
from app.models.audio import AudioSession

class AudioWSService:
    """Thin wrapper over ConnectionManager; keeps room for future logic."""
    @staticmethod
    def start(
        ws: WebSocket,
        *,
        sample_rate: int,
        channels: int,
        sample_width: int,
        filename: Optional[str] = None,
    ) -> AudioSession:
        return manager.begin(
            ws,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            filename=filename,
        )

    @staticmethod
    def write(ws: WebSocket, chunk: bytes) -> None:
        manager.write(ws, chunk)

    @staticmethod
    def end(ws: WebSocket) -> Optional[AudioSession]:
        return manager.end(ws)
