# app/core/orchestrator.py
"""
Orchestrator: high-level call flow runner.

Entry point expected by webhooks router: `process_call(payload: dict)`.

Behavior (best-effort stub-first):
 - ensure session exists (session_store)
 - fetch audio/media (currently accepts a local file path or media_url)
 - call ASR -> get transcript
 - persist transcript
 - ask LLM for intent + reply
 - optionally consult flow engine to get canonical reply/escalate
 - synthesize reply to audio (TTS) and provide media URL
 - update session metadata and return summary

This file avoids hard failures if optional pieces are missing — useful during early dev.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from app.config import get_settings
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("conversational-ivr-poc.core.orchestrator")
settings = get_settings()

# Import clients with safe fallbacks
try:
    from app.core.asr_client import ASRClient
except Exception:
    ASRClient = None

try:
    from app.core.llm_client import LLMClient
except Exception:
    LLMClient = None

try:
    from app.core.tts_client import TTSClient
except Exception:
    TTSClient = None

try:
    from app.core.flow_engine import FlowEngine
except Exception:
    FlowEngine = None


# Instantiate default clients (use settings)
_asr = ASRClient(settings) if ASRClient else None
_llm = LLMClient(settings) if LLMClient else None
_tts = TTSClient(settings) if TTSClient else None
_flow_engine = FlowEngine(settings) if FlowEngine else None


async def _save_transcript_entry(call_id: str, text: str, source: str = "asr"):
    """Persist transcript if a transcripts_store exists; otherwise log/fall back to session update."""
    entry = {
        "call_id": call_id,
        "timestamp": datetime.utcnow().isoformat(),
        "text": text,
        "source": source,
    }
    try:
        from app.storage.transcripts_store import save_transcript  # type: ignore

        await save_transcript(entry)
        logger.debug("Saved transcript via transcripts_store for %s", call_id)
    except Exception:
        # fallback to session_store or in-memory
        try:
            from app.state.session_store import append_transcript  # type: ignore

            await append_transcript(call_id, entry)
            logger.debug("Appended transcript via session_store for %s", call_id)
        except Exception:
            logger.debug("No transcript storage available - transcript: %s", entry)


async def _update_session(call_id: str, patch: Dict[str, Any]):
    try:
        from app.state.session_store import update_session  # type: ignore

        await update_session(call_id, patch)
    except Exception:
        # fallback: if in-memory session exists update it
        try:
            from app.api.webhooks import _INMEM_SESSIONS  # type: ignore

            s = _INMEM_SESSIONS.get(call_id, {})
            s.update(patch)
            _INMEM_SESSIONS[call_id] = s
        except Exception:
            logger.debug("No session store available to persist session update for %s", call_id)


async def _maybe_get_flow_for_call():
    """
    Try to return the most relevant flow object. Prefers storage.flows_store; otherwise returns None.
    """
    try:
        from app.storage.flows_store import list_flows  # type: ignore

        flows = await list_flows()
        if flows:
            # assume flows is a list of flow dicts
            first = flows[0]
            return first
    except Exception:
        # try in-memory flows from API module
        try:
            from app.api.flows import _FLOW_STORE  # type: ignore

            if _FLOW_STORE:
                # return arbitrary flow
                return list(_FLOW_STORE.values())[0]
        except Exception:
            return None
    return None


async def process_call(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main async entry invoked by the webhook background task.

    payload example:
    {
      "call_id": "call-123",
      "from": "+1555...",
      "to": "+1555...",
      "media_url": "file://demo/recordings/inbound.wav",
      "direction": "inbound"
    }
    """
    call_id = payload.get("call_id")
    media_url = payload.get("media_url")
    logger.info("Orchestrator started for call %s media=%s", call_id, media_url)

    # 1) Transcribe (ASR)
    asr_text = ""
    if _asr:
        try:
            asr_text = await _asr.transcribe(media_url)
        except Exception as exc:
            logger.exception("ASR client failed; falling back to stub transcript: %s", exc)
            asr_text = "stubbed transcript: could not run ASR"
    else:
        asr_text = "stubbed transcript (no ASR client available)"

    await _save_transcript_entry(call_id, asr_text, source="asr")

    # 2) LLM: get intent + reply
    llm_result: Dict[str, Any] = {}
    if _llm:
        try:
            llm_result = await _llm.generate_response(asr_text, context={"call_id": call_id})
        except Exception as exc:
            logger.exception("LLM client failed; using fallback rules: %s", exc)
            llm_result = {"intent": "unknown", "reply": "Sorry, I couldn't process that right now."}
    else:
        # simple rule-based fallback
        text = (asr_text or "").lower()
        if "balance" in text:
            llm_result = {"intent": "account_balance", "reply": "Your balance is $42 (fallback)."}
        elif "agent" in text or "human" in text or "representative" in text:
            llm_result = {"intent": "connect_agent", "reply": "Connecting you to an agent.", "escalate": True}
        else:
            llm_result = {"intent": "unknown", "reply": "I didn't get that. Can you repeat?"}

    intent = llm_result.get("intent")
    reply_text = llm_result.get("reply", "")

    # persist LLM reply as transcript
    await _save_transcript_entry(call_id, reply_text, source="llm")

    # 3) Optionally consult flow engine to refine reply / escalate decision
    escalate = bool(llm_result.get("escalate", False))
    if _flow_engine:
        try:
            flow = await _maybe_get_flow_for_call()
            if flow:
                fe_result = await _flow_engine.run_flow(flow, intent= intent, text=asr_text)
                # flow engine may override reply/escalate
                reply_text = fe_result.get("reply", reply_text)
                escalate = fe_result.get("escalate", escalate)
        except Exception:
            logger.debug("Flow engine not usable for call %s", call_id)

    # 4) Synthesize reply (TTS) -> produce media URL
    media_out: Optional[str] = None
    if _tts:
        try:
            media_path = await _tts.synthesize(reply_text, call_id=call_id)
            # Make a media URL relative to MEDIA_BASE_URL if possible
            if media_path:
                # if media_path is a path under demo/recordings that main.py serves under /media,
                # produce a URL like {MEDIA_BASE_URL}/{filename}
                p = Path(media_path)
                filename = p.name
                media_out = f"{settings.MEDIA_BASE_URL.rstrip('/')}/{filename}"
        except Exception as exc:
            logger.exception("TTS synthesis failed for %s: %s", call_id, exc)
            media_out = None
    else:
        # fallback: no TTS client; store reply text in session
        media_out = None

    # 5) If escalate: ask media_bridge to create agent URL / offer
    agent_payload = None
    if escalate:
        try:
            from app.core.media_bridge import escalate_to_agent  # type: ignore

            agent_payload = await escalate_to_agent(call_id)
        except Exception:
            logger.debug("No media bridge available to escalate for %s", call_id)
            agent_payload = {"note": "escalation_requested_but_no_bridge"}

    # 6) Update session state with results
    await _update_session(
        call_id,
        {
            "status": "completed" if not escalate else "escalated",
            "last_intent": intent,
            "last_reply": reply_text,
            "media_out": media_out,
            "agent": agent_payload,
            "last_update": datetime.utcnow().isoformat(),
        },
    )

    result_summary = {
        "call_id": call_id,
        "intent": intent,
        "reply": reply_text,
        "media_out": media_out,
        "escalated": escalate,
        "agent": agent_payload,
    }

    logger.info("Orchestration complete for %s: intent=%s escalate=%s", call_id, intent, escalate)
    return result_summary
