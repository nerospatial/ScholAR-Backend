from dataclasses import dataclass
from pathlib import Path
import wave

@dataclass
class AudioSession:
    """Transport-agnostic domain model for an active WAV write session."""
    id: str
    path: Path
    wf: wave.Wave_write
    sample_rate: int
    channels: int
    sample_width: int  # bytes per sample (2 for 16-bit)
