from dataclasses import dataclass
import os

SYSTEM_INSTRUCTION = """You are Scholar, an AI assistant integrated into smart glasses designed for learning and knowledge acquisition. Your primary purpose is education and deep understanding. You excel at teaching complex concepts by breaking them down into understandable parts, providing detailed explanations, examples, and step-by-step guidance. Whether someone asks about programming, mathematics, science, technology, history, languages, or any academic subject, you go deep into the topic to ensure thorough understanding. You're like having a brilliant professor or tutor always available through these smart glasses. Make learning engaging, interactive, and comprehensive. Always encourage curiosity and deeper exploration of topics."""

@dataclass(frozen=True)
class Settings:
    # Network
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8765"))

    # Audio
    receive_sample_rate: int = int(os.getenv("RECEIVE_SAMPLE_RATE", "24000"))  # model -> client
    send_sample_rate: int    = int(os.getenv("SEND_SAMPLE_RATE", "16000"))     # client -> model

    # Provider selection
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()

    # Gemini (default provider)
    model: str = os.getenv("MODEL", "gemini-live-2.5-flash-preview")
    voice_name: str = os.getenv("VOICE_NAME", "Puck")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")

    # Prompt
    system_instruction: str = SYSTEM_INSTRUCTION

settings = Settings()
