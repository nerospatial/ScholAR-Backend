import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GeminiSettings:
    """
    Configuration settings for Gemini Live API provider.
    Based on the minimal Gemini Live API client example.
    """
    
    # API Key (required)
    gemini_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Audio Configuration
    audio_format: int = 1  # pyaudio.paInt16
    audio_channels: int = 1
    send_sample_rate: int = 16000
    receive_sample_rate: int = 24000
    chunk_size: int = 1024
    
    # Model Configuration
    model: str = "models/gemini-live-2.5-flash-preview"
    default_mode: str = "camera"
    response_modalities: List[str] = ["AUDIO"]
    
    def __init__(self):
        """Validate required settings"""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")


# Global settings instance
gemini_settings = GeminiSettings()