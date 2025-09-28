from typing import Dict, Type
from enum import Enum
from app.llm.interfaces.base_llm_provider_interface import BaseLLMProviderInterface
from app.llm.providers.gemini.gemini_provider import GeminiProvider


class LLMProviderType(Enum):
    """Enumeration of supported LLM providers"""
    GEMINI = "gemini"
    # Future providers can be added here
    # OPENAI = "openai"
    # CLAUDE = "claude"


class LLMProviderFactory:
    """
    Factory class for creating LLM provider instances.
    Supports multiple LLM providers through a common interface.
    """
    
    # Registry of available providers
    _providers: Dict[LLMProviderType, Type[BaseLLMProviderInterface]] = {
        LLMProviderType.GEMINI: GeminiProvider,
        # Future providers can be registered here
        # LLMProviderType.OPENAI: OpenAIProvider,
        # LLMProviderType.CLAUDE: ClaudeProvider,
    }
    
    @classmethod
    def create_provider(
        self, 
        provider_type: LLMProviderType
    ) -> BaseLLMProviderInterface:
        """
        Create an LLM provider instance.
        
        Args:
            provider_type: The type of provider to create
            
        Returns:
            An instance of the requested provider
            
        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type not in self._providers:
            available_types = list(self._providers.keys())
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Available types: {available_types}"
            )
            
        provider_class = self._providers[provider_type]
        return provider_class()
    
    @classmethod
    def create_gemini_provider(cls) -> GeminiProvider:
        """Convenience method to create Gemini provider"""
        return cls.create_provider(LLMProviderType.GEMINI)
    
    @classmethod
    def get_available_providers(cls) -> list[LLMProviderType]:
        """Get list of all available provider types"""
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(
        cls,
        provider_type: LLMProviderType,
        provider_class: Type[BaseLLMProviderInterface]
    ) -> None:
        """
        Register a new provider type.
        
        Args:
            provider_type: The provider type enum
            provider_class: The provider class to register
        """
        if not issubclass(provider_class, BaseLLMProviderInterface):
            raise TypeError(
                f"Provider class must implement BaseLLMProviderInterface"
            )
            
        cls._providers[provider_type] = provider_class


# Convenience function for easy import
def get_llm_provider(provider_type: LLMProviderType = LLMProviderType.GEMINI) -> BaseLLMProviderInterface:
    """
    Get an LLM provider instance.
    
    Args:
        provider_type: The type of provider (defaults to Gemini)
        
    Returns:
        An instance of the requested provider
    """
    return LLMProviderFactory.create_provider(provider_type)