# app/api/transcripts.py
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from app.config import get_settings
from datetime import datetime

logger = logging.getLogger("conversational-ivr-poc.api.transcripts")
router = APIRouter()

settings = get_settings()

# In-memory fallback transcripts: dict mapping call_id -> list(entries)
_INMEM_TRANSCRIPTS = {}


@router.get("/", summary="Search transcripts")
async def search_transcripts(
    call_id: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None, description="ISO timestamp to filter from"),
    to_ts: Optional[str] = Query(None, description="ISO timestamp to filter to"),
    limit: int = Query(50, ge=1, le=1000),
):
    """
    Search transcripts by call_id and optional time range. Uses transcripts_store if implemented,
    otherwise an in-memory store.
    """
    # If a transcripts_store exists prefer it
    try:
        from app.storage.transcripts_store import query_transcripts  # type: ignore

        results = await query_transcripts(call_id=call_id, from_ts=from_ts, to_ts=to_ts, limit=limit)
        return {"transcripts": results}
    except Exception:
        # fallback to in-memory simple filter
        results = []
        if call_id:
            entries = _INMEM_TRANSCRIPTS.get(call_id, [])
            results = entries[-limit:]
        else:
            # flatten
            all_entries = []
            for entries in _INMEM_TRANSCRIPTS.values():
                all_entries.extend(entries)
            # optional time filtering
            def in_range(e):
                ts = e.get("timestamp")
                if not ts:
                    return True
                if from_ts and ts < from_ts:
                    return False
                if to_ts and ts > to_ts:
                    return False
                return True

            filtered = [e for e in all_entries if in_range(e)]
            # sort by timestamp desc and limit
            filtered_sorted = sorted(filtered, key=lambda e: e.get("timestamp", ""), reverse=True)
            results = filtered_sorted[:limit]

        return {"transcripts": results}
