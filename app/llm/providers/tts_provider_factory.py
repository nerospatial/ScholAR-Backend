from typing import Dict, Type, Optional
from enum import Enum
from app.llm.interfaces.base_tts_provider_interface import BaseTTSProviderInterface
from app.llm.providers.elevenlabs.elevenlabs_provider import ElevenLabsProvider


class TTSProviderType(Enum):
    """Enumeration of supported TTS providers"""
    ELEVENLABS = "elevenlabs"
    # Future providers can be added here
    # OPENAI_TTS = "openai_tts"
    # CUSTOM_TTS = "custom_tts"
    # AZURE_TTS = "azure_tts"
    # GOOGLE_TTS = "google_tts"


class TTSProviderFactory:
    """
    Factory class for creating TTS provider instances.
    Supports multiple TTS providers through a common interface.
    """
    
    # Registry of available TTS providers
    _providers: Dict[TTSProviderType, Type[BaseTTSProviderInterface]] = {
        TTSProviderType.ELEVENLABS: ElevenLabsProvider,
        # Future providers can be registered here
        # TTSProviderType.OPENAI_TTS: OpenAITTSProvider,
        # TTSProviderType.CUSTOM_TTS: CustomTTSProvider,
        # TTSProviderType.AZURE_TTS: AzureTTSProvider,
        # TTSProviderType.GOOGLE_TTS: GoogleTTSProvider,
    }
    
    @classmethod
    def create_provider(
        cls, 
        provider_type: TTSProviderType,
        **kwargs
    ) -> BaseTTSProviderInterface:
        """
        Create a TTS provider instance.
        
        Args:
            provider_type: The type of TTS provider to create
            **kwargs: Additional provider-specific parameters
            
        Returns:
            An instance of the requested TTS provider
            
        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type not in cls._providers:
            available_types = list(cls._providers.keys())
            raise ValueError(
                f"Unsupported TTS provider type: {provider_type}. "
                f"Available types: {available_types}"
            )
            
        provider_class = cls._providers[provider_type]
        
        # ElevenLabs provider gets voice_id from its own settings
        if provider_type == TTSProviderType.ELEVENLABS:
            return provider_class()  # No parameters needed - uses elevenlabs_settings
        
        # Default case - instantiate with all kwargs
        return provider_class(**kwargs)
    
    @classmethod
    def create_elevenlabs_provider(cls) -> ElevenLabsProvider:
        """Convenience method to create ElevenLabs TTS provider"""
        return cls.create_provider(TTSProviderType.ELEVENLABS)
    
    @classmethod
    def get_available_providers(cls) -> list[TTSProviderType]:
        """Get list of all available TTS provider types"""
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(
        cls,
        provider_type: TTSProviderType,
        provider_class: Type[BaseTTSProviderInterface]
    ) -> None:
        """
        Register a new TTS provider type.
        
        Args:
            provider_type: The TTS provider type enum
            provider_class: The TTS provider class to register
            
        Raises:
            TypeError: If provider class doesn't implement BaseTTSProviderInterface
        """
        if not issubclass(provider_class, BaseTTSProviderInterface):
            raise TypeError(
                f"Provider class must implement BaseTTSProviderInterface"
            )
            
        cls._providers[provider_type] = provider_class
    
    @classmethod
    def is_provider_available(cls, provider_type: TTSProviderType) -> bool:
        """Check if a specific provider type is available"""
        return provider_type in cls._providers


# Convenience function for easy import
def get_tts_provider(
    provider_type: TTSProviderType = TTSProviderType.ELEVENLABS,
    **kwargs
) -> BaseTTSProviderInterface:
    """
    Get a TTS provider instance.
    
    Args:
        provider_type: The type of TTS provider (defaults to ElevenLabs)
        **kwargs: Additional provider-specific parameters
        
    Returns:
        An instance of the requested TTS provider
    """
    return TTSProviderFactory.create_provider(
        provider_type,
        **kwargs
    )


# Default provider configuration
def get_default_tts_provider() -> BaseTTSProviderInterface:
    """Get the default TTS provider (ElevenLabs)"""
    return get_tts_provider(TTSProviderType.ELEVENLABS)
