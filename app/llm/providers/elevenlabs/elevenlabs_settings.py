# app/llm/providers/elevenlabs/elevenlabs_settings.py
"""
ElevenLabs TTS Provider Configuration
"""
import os
from typing import List, Optional
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()
class ElevenLabsSettings:
    """ElevenLabs TTS configuration settings"""
    # API Configuration
    api_key: str = os.getenv("ELEVEN_LABS_API_KEY", "")
    base_url: str = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
    
    # WebSocket Configuration
    ws_base_url: str = os.getenv("ELEVENLABS_WS_BASE_URL", "wss://api.elevenlabs.io")
    
    # Voice Configuration
    voice_id: str = os.getenv("ELEVEN_LABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    # Model Configuration - Updated for Flash model
    model_id: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
    
    # Audio Configuration
    output_format: str = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "pcm_16000")
    sample_rate: int = int(os.getenv("ELEVENLABS_SAMPLE_RATE", "16000"))
    # Voice Settings
    stability: float = float(os.getenv("ELEVENLABS_STABILITY", "0.5"))
    similarity_boost: float = float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.8"))
    style: float = float(os.getenv("ELEVENLABS_STYLE", "0.0"))
    use_speaker_boost: bool = os.getenv("ELEVENLABS_USE_SPEAKER_BOOST", "true").lower() == "true"
    speed: float = float(os.getenv("ELEVENLABS_SPEED", "1.0"))
    # Streaming Configuration
    optimize_streaming_latency: int = int(os.getenv("ELEVENLABS_OPTIMIZE_STREAMING_LATENCY", "0"))
    chunk_size: int = int(os.getenv("ELEVENLABS_CHUNK_SIZE", "1024"))
    
    # WebSocket Streaming Configuration
    chunk_length_schedule: List[int] = [
        int(x.strip()) for x in os.getenv("ELEVENLABS_CHUNK_LENGTH_SCHEDULE", "120,160,250,290").split(",")
    ]
    
    # Connection Configuration
    connection_timeout: int = int(os.getenv("ELEVENLABS_CONNECTION_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("ELEVENLABS_MAX_RETRIES", "3"))
    retry_delay: float = float(os.getenv("ELEVENLABS_RETRY_DELAY", "1.0"))
    @property
    def ws_url(self) -> str:
        """Generate WebSocket URL for streaming TTS"""
        return f"{self.ws_base_url}/v1/text-to-speech/{self.voice_id}/stream-input"
    
    @property
    def ws_headers(self) -> dict:
        """Generate headers for WebSocket connection"""
        return {
            "xi-api-key": self.api_key
        }
    
    @property
    def voice_settings(self) -> dict:
        """Generate voice settings dictionary"""
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
            "speed": self.speed
        }
    
    @property
    def generation_config(self) -> dict:
        """Generate generation configuration dictionary"""
        return {
            "chunk_length_schedule": self.chunk_length_schedule
        }
    
    @property
    def initial_config_message(self) -> dict:
        """Generate initial WebSocket configuration message"""
        return {
            "text": " ",
            "voice_settings": self.voice_settings,
            "generation_config": self.generation_config,
            "model_id": self.model_id
        }
    def validate_settings(self) -> bool:
        """Validate that required settings are present"""
        if not self.api_key:
            raise ValueError("ELEVEN_LABS_API_KEY is required")
        
        if not self.voice_id:
            raise ValueError("ELEVEN_LABS_VOICE_ID is required")
        
        return True
# Global settings instance
elevenlabs_settings = ElevenLabsSettings()
# Validate settings on import
elevenlabs_settings.validate_settings()

