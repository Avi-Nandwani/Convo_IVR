# app/api/webhooks.py
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field
from app.config import get_settings
from datetime import datetime
import asyncio

logger = logging.getLogger("conversational-ivr-poc.api.webhooks")
router = APIRouter()

settings = get_settings()

# Try to import orchestrator if implemented; otherwise None
try:
    from app.core.orchestrator import process_call  # type: ignore
except Exception:
    process_call = None  # will use stub


# Simple in-memory session/trancript fallback (used only if no store implemented)
_INMEM_SESSIONS = {}
_INMEM_TRANSCRIPTS = {}


class CallWebhook(BaseModel):
    call_id: str = Field(..., description="Unique call identifier")
    from_number: Optional[str] = Field(None, alias="from")
    to_number: Optional[str] = Field(None, alias="to")
    media_url: Optional[str] = Field(None, description="URL or local path to audio")
    direction: Optional[str] = Field("inbound")


@router.post("/call")
async def inbound_call(
    payload: CallWebhook,
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(None),
    request: Request = None,
):
    """
    Receive an inbound call webhook. This will:
      - verify optional webhook secret header
      - create a session entry (in redis/session store or in-memory)
      - dispatch processing to orchestrator.process_call() if present,
        otherwise run a light-weight stub flow in background.
    """
    # verify optional secret
    if settings.WEBHOOK_SECRET and x_webhook_secret is not None:
        if x_webhook_secret != settings.WEBHOOK_SECRET:
            logger.warning("Webhook secret mismatch for call %s", payload.call_id)
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    call_id = payload.call_id
    logger.info("Received call webhook: %s from=%s to=%s media=%s", call_id, payload.from_number, payload.to_number, payload.media_url)

    # create basic session
    session = {
        "call_id": call_id,
        "from": payload.from_number,
        "to": payload.to_number,
        "status": "received",
        "created_at": datetime.utcnow().isoformat(),
        "last_update": datetime.utcnow().isoformat(),
        "transcripts": [],
        "last_intent": None,
    }

    # Try to save session using session_store if available
    try:
        from app.state.session_store import set_session  # type: ignore

        await set_session(call_id, session)
        logger.debug("Saved session via session_store for %s", call_id)
    except Exception:
        _INMEM_SESSIONS[call_id] = session
        logger.debug("Saved session in-memory for %s", call_id)

    # If an orchestrator exists call it; otherwise run a stub processor in background
    if process_call:
        logger.info("Dispatching to orchestrator.process_call for %s", call_id)
        # process_call is expected to be async
        background_tasks.add_task(process_call, payload.dict(by_alias=True))
    else:
        logger.info("No orchestrator found — running stub processing for %s", call_id)
        background_tasks.add_task(_stub_process_call, payload.dict(by_alias=True))

    return {"status": "accepted", "call_id": call_id}


async def _stub_process_call(payload: dict):
    """
    A tiny stub that mimics simple ASR -> LLM -> TTS steps so you can develop without full stack.
    It writes a transcript entry and updates session state.
    """
    call_id = payload.get("call_id")
    media_url = payload.get("media_url")
    logger.info("Running stub process for call %s (media=%s)", call_id, media_url)

    # simulate ASR latency
    await asyncio.sleep(0.5)
    # stub transcript
    transcript_text = "stubbed transcript: hello, I want account balance"
    logger.debug("Stub ASR transcript: %s", transcript_text)

    # simulate LLM processing
    await asyncio.sleep(0.3)
    intent = "account_balance"
    reply_text = "Your balance is $42 (stubbed)"

    # save transcript via transcripts_store if available
    transcript_entry = {
        "call_id": call_id,
        "timestamp": datetime.utcnow().isoformat(),
        "text": transcript_text,
        "source": "asr_stub",
    }
    try:
        from app.storage.transcripts_store import save_transcript  # type: ignore

        await save_transcript(transcript_entry)
        logger.debug("Saved transcript via transcripts_store for %s", call_id)
    except Exception:
        _INMEM_TRANSCRIPTS.setdefault(call_id, []).append(transcript_entry)
        logger.debug("Saved transcript in-memory for %s", call_id)

    # update session
    try:
        from app.state.session_store import update_session  # type: ignore

        await update_session(call_id, {"status": "answered", "last_intent": intent, "last_reply": reply_text, "last_update": datetime.utcnow().isoformat()})
    except Exception:
        s = _INMEM_SESSIONS.get(call_id, {})
        s.update({"status": "answered", "last_intent": intent, "last_reply": reply_text, "last_update": datetime.utcnow().isoformat()})
        _INMEM_SESSIONS[call_id] = s

    logger.info("Stub processing finished for %s", call_id)
