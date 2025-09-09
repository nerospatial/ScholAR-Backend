# app/llm/gemini/live.py
import asyncio
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from google import genai
from google.genai import types
from google.genai.types import LiveConnectConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig

from app.core.settings import settings
from app.core.log import logger
from app.llm.base import RealtimeLLM, AudioOut, TextOut, TurnComplete, SessionId, GoAway, Interrupted

class GeminiAdapter(RealtimeLLM):
    def __init__(self) -> None:
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        self._client = genai.Client(api_key=settings.google_api_key)
        self._ctx = None          # <-- keep the context manager
        self._session = None      # <-- AsyncSession returned by __aenter__()

        self._config = LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=settings.voice_name)
                )
            ),
            system_instruction=settings.system_instruction,
        )

        logger.info(
            f"Using Gemini model={settings.model}, voice={settings.voice_name} "
            f"key=...{settings.google_api_key[-6:]}"
        )
        logger.info("System instruction (Scholar):\n" + settings.system_instruction)

    async def __aenter__(self):
        # save the context manager so we can call __aexit__ on it later
        self._ctx = self._client.aio.live.connect(model=settings.model, config=self._config)
        self._session = await self._ctx.__aenter__()   # returns AsyncSession
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # close via the context manager, NOT the session
        if self._ctx is not None:
            try:
                await self._ctx.__aexit__(exc_type, exc, tb)
            finally:
                self._ctx = None
                self._session = None

    async def send_audio(self, pcm_16k: bytes) -> None:
        await self._session.send_realtime_input(
            media={"data": pcm_16k, "mime_type": f"audio/pcm;rate={settings.send_sample_rate}"}
        )

    async def send_text(self, text: str) -> None:
        # optional: no-op for now
        pass

    async def events(self):
        try:
            async for r in self._session.receive():
                sc = r.server_content

                if r.session_resumption_update and r.session_resumption_update.new_handle:
                    yield SessionId(id=r.session_resumption_update.new_handle)

                if r.go_away is not None:
                    yield GoAway(time_left=float(r.go_away.time_left))

                if getattr(sc, "interrupted", False):
                    yield Interrupted()

                if sc and sc.model_turn:
                    for part in sc.model_turn.parts:
                        if getattr(part, "inline_data", None):
                            yield AudioOut(pcm=part.inline_data.data)

                ot = getattr(sc, "output_transcription", None)
                if ot and ot.text:
                    yield TextOut(text=ot.text)

                if sc and getattr(sc, "turn_complete", False):
                    yield TurnComplete()

        except (ConnectionClosedOK, ConnectionClosedError) as e:
            # Normal/remote close: end the generator quietly
            logger.info(f"Gemini live session closed: {e}")
        except asyncio.CancelledError:
            # TaskGroup cancellation: propagate
            raise
        except Exception as e:
            # Unexpected error: log and end the stream
            logger.exception(f"Gemini events stream error: {e}")
