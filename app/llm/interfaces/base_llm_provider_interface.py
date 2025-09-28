from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional
import asyncio


class BaseLLMProviderInterface(ABC):
    """
    Base interface for LLM providers that support real-time audio/video/text interactions.
    All LLM provider implementations must inherit from this interface.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the LLM service"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the LLM service"""
        pass

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Send text input to the LLM"""
        pass

    @abstractmethod
    async def send_audio(self, audio_data: bytes, sample_rate: int = 16000) -> None:
        """Send audio input to the LLM"""
        pass

    @abstractmethod
    async def send_video(self, video_data: bytes, mime_type: str = "image/jpeg") -> None:
        """Send video/image input to the LLM"""
        pass

    @abstractmethod
    async def get_text_response(self) -> AsyncGenerator[str, None]:
        """Get text responses from the LLM as an async generator"""
        pass

    @abstractmethod
    async def get_audio_response(self) -> AsyncGenerator[bytes, None]:
        """Get audio responses from the LLM as an async generator of audio chunks"""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the provider is currently connected"""
        pass

    @abstractmethod
    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        pass