# app/core/asr_client.py
"""
ASR client wrapper.

Provides async `transcribe(media_url)` which returns a string transcript.

Supports modes:
 - stub: returns a canned transcript (fast)
 - local: tries to use `whisper` (or `faster_whisper`) if installed (may be blocking)
 - cloud: placeholder for cloud ASR (e.g., OpenAI / Google) — not implemented here but shows structure.

The implementation tries to be safe during early dev (falls back to stub if dependencies missing).
"""
import logging
import asyncio
from typing import Optional
from app.config import get_settings
from pathlib import Path
import concurrent.futures

logger = logging.getLogger("conversational-ivr-poc.core.asr")

settings = get_settings()


class ASRClient:
    def __init__(self, settings):
        self.mode = (settings.ASR_MODE or "stub").lower()
        self.settings = settings
        self._whisper = None
        # Try to import whisper-like library lazily
        if self.mode == "local":
            try:
                import whisper  # type: ignore

                self._whisper = whisper
                logger.info("Whisper library available for ASR (local mode).")
            except Exception as exc:
                logger.warning("Whisper not available — local ASR won't work: %s", exc)
                self._whisper = None

    async def transcribe(self, media_url: Optional[str]) -> str:
        """
        Async transcription entry. Accepts a local path (file:// or relative) or None (then stub).
        """
        if self.mode == "stub" or not media_url:
            logger.debug("ASR stub mode or no media_url; returning canned transcript.")
            return "stubbed transcript: hello I want my account balance"

        # If media_url starts with file:// -> strip it
        local_path = media_url
        if isinstance(media_url, str) and media_url.startswith("file://"):
            local_path = media_url[len("file://") :]

        # if whsiper is available and mode local: run in threadpool because whisper is blocking
        if self.mode == "local" and self._whisper:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._blocking_whisper_transcribe, local_path)

        # cloud mode placeholder: try openai speech-to-text if openai installed and key present
        if self.mode == "cloud":
            try:
                import openai  # type: ignore

                if not self.settings.LLM_API_KEY:
                    logger.warning("No LLM_API_KEY / OpenAI key set; cloud ASR cannot be used")
                    return "stubbed transcript (no cloud key)"
                openai.api_key = self.settings.LLM_API_KEY
                # Use OpenAI's speech-to-text (whisper) API if user has audio file path
                # Note: this requires file access and internet; leave as example
                audio_file = open(local_path, "rb")
                resp = openai.Audio.transcribe("gpt-4o-mini-transcribe", audio_file)  # example; adapt as needed
                return resp["text"]
            except Exception as exc:
                logger.warning("Cloud ASR failed or not available: %s", exc)
                return "stubbed transcript (cloud asr failed)"

        # fallback: try to read paired .txt file with same name as wav (dev convenience)
        try:
            p = Path(local_path)
            txt_candidate = p.with_suffix(".txt")
            if txt_candidate.exists():
                text = txt_candidate.read_text(encoding="utf-8")
                logger.debug("Loaded fallback transcript from %s", txt_candidate)
                return text.strip()
        except Exception:
            pass

        logger.debug("No ASR path matched; returning canned fallback transcript.")
        return "stubbed transcript: unable to transcribe (fallback)"
    
    def _blocking_whisper_transcribe(self, path: str) -> str:
        """Blocking whisper transcription (runs in threadpool)."""
        try:
            if self._whisper is None:
                return "stubbed transcript (whisper not available)"
            model = self._whisper.load_model("base")
            result = model.transcribe(path)
            return result.get("text", "")
        except Exception as exc:
            logger.exception("Whisper transcription failed: %s", exc)
            return "stubbed transcript (whisper failed)"
