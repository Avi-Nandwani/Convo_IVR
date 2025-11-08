# app/core/tts_client.py
"""
TTS client wrapper.

Provides async `synthesize(text, call_id=None)` which should return a local file path
to the generated audio (e.g., demo/recordings/<call_id>_reply.wav).

Modes:
 - stub: no audio produced, returns None
 - local: tries to use pyttsx3 to produce a .wav file (offline)
 - cloud: placeholder for cloud TTS (not implemented here)
"""
import logging
import asyncio
from typing import Optional
from app.config import get_settings
from pathlib import Path
import uuid

logger = logging.getLogger("conversational-ivr-poc.core.tts")
settings = get_settings()


class TTSClient:
    def __init__(self, settings):
        self.mode = (settings.TTS_MODE or "stub").lower()
        self.settings = settings
        self._pyttsx3 = None
        if self.mode == "local":
            try:
                import pyttsx3  # type: ignore

                self._pyttsx3 = pyttsx3
                logger.info("pyttsx3 available for local TTS")
            except Exception as exc:
                logger.warning("pyttsx3 not available; local TTS will fallback to stub: %s", exc)
                self._pyttsx3 = None

        # ensure demo/recordings directory exists
        self.recordings_dir = Path(__file__).resolve().parents[1].joinpath("demo", "recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize(self, text: str, call_id: Optional[str] = None) -> Optional[str]:
        """
        Synthesize text to an audio file asynchronously. Returns file path or None.
        """
        if not text:
            return None

        if self.mode == "stub":
            logger.debug("TTS stub mode - not producing audio")
            return None

        # choose filename
        if not call_id:
            fname = f"reply_{uuid.uuid4().hex[:8]}.wav"
        else:
            fname = f"{call_id}_reply.wav"
        out_path = self.recordings_dir.joinpath(fname)

        if self.mode == "local" and self._pyttsx3:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._blocking_pyttsx3_save, text, str(out_path))

        # cloud mode placeholder - not implemented (would call cloud TTS SDK)
        logger.warning("TTS cloud mode not implemented; falling back to stub")
        return None

    def _blocking_pyttsx3_save(self, text: str, out_file: str) -> Optional[str]:
        """
        Use pyttsx3 to save audio synchronously. Returns file path or None.
        """
        try:
            engine = self._pyttsx3.init()
            # pyttsx3 supports save_to_file
            engine.save_to_file(text, out_file)
            engine.runAndWait()
            logger.debug("Saved TTS audio to %s", out_file)
            return out_file
        except Exception as exc:
            logger.exception("pyttsx3 TTS failed: %s", exc)
            return None
