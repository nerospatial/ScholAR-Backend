# app/llm/interfaces/base_tts_provider_interface.py
"""
Base TTS Provider Interface
Specialized interface for Text-to-Speech providers
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any
from app.llm.interfaces.base_llm_provider_interface import BaseLLMProviderInterface


class BaseTTSProviderInterface(BaseLLMProviderInterface):
    """
    Base interface for TTS providers that convert text to speech.
    Extends BaseLLMProviderInterface but specializes for TTS use cases.
    """
    """
    Base interface for TTS providers that convert text to speech.
    More specialized than the general LLM provider interface.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the TTS service"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the TTS service"""
        pass

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Send text to be converted to speech"""
        pass

    @abstractmethod
    async def get_audio_response(self) -> AsyncGenerator[bytes, None]:
        """Get audio chunks as they become available"""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if provider is connected"""
        pass

    @abstractmethod
    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        pass

    # TTS-specific methods that ElevenLabs supports
    @abstractmethod
    async def set_voice(self, voice_id: str) -> None:
        """Set the voice to use for TTS"""
        pass

