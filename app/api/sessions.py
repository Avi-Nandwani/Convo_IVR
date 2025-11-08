# app/api/sessions.py
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from app.config import get_settings

logger = logging.getLogger("conversational-ivr-poc.api.sessions")
router = APIRouter()

settings = get_settings()

# In-memory fallback
_INMEM_SESSIONS = {}


@router.get("/", summary="List active sessions")
async def list_sessions():
    """
    Returns a list of known sessions (in-memory or via session_store).
    """
    try:
        from app.state.session_store import list_sessions as _list  # type: ignore

        sessions = await _list()
    except Exception:
        sessions = list(_INMEM_SESSIONS.values())

    return {"sessions": sessions}


@router.get("/{call_id}", summary="Get session by call_id")
async def get_session(call_id: str):
    """
    Returns session state including transcripts (if available).
    """
    # Try to use session_store if implemented
    try:
        from app.state.session_store import get_session as _get  # type: ignore

        session = await _get(call_id)
    except Exception:
        session = _INMEM_SESSIONS.get(call_id)

    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session
