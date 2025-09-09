from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

@dataclass
class Event: ...

@dataclass
class AudioOut(Event):
    pcm: bytes  # 16-bit PCM @ 16kHz

@dataclass
class TextOut(Event):
    text: str

@dataclass
class TurnComplete(Event): ...

@dataclass
class SessionId(Event):
    id: str

@dataclass
class GoAway(Event):
    time_left: float  # seconds

@dataclass
class Interrupted(Event): ...

class RealtimeLLM(Protocol):
    """Adapter contract for any realtime LLM provider."""
    async def __aenter__(self) -> "RealtimeLLM": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def send_audio(self, pcm_16k: bytes) -> None: ...
    async def send_text(self, text: str) -> None: ...

    def events(self) -> AsyncIterator[Event]:
        """Yields AudioOut/TextOut/TurnComplete/SessionId/GoAway/Interrupted."""
        ...
