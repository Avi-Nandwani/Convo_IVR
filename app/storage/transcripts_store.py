# app/storage/transcripts_store.py
"""
Simple transcripts storage backed by databases/SQLAlchemy (async).

Exposes:
 - save_transcript(entry: dict)
 - query_transcripts(call_id=None, from_ts=None, to_ts=None, limit=50)
"""
import logging
from typing import Optional, List, Dict, Any
from app.db.db import get_database
from app.models.db_models import transcripts
import datetime
import json

logger = logging.getLogger("conversational-ivr-poc.storage.transcripts")


async def save_transcript(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a transcript entry dict. Returns the saved row dict (including id).
    Expected keys: call_id, timestamp, text, source
    """
    db = get_database()
    # ensure minimal timestamps
    if not entry.get("timestamp"):
        entry["timestamp"] = datetime.datetime.utcnow().isoformat()
    if not entry.get("created_at"):
        entry["created_at"] = datetime.datetime.utcnow().isoformat()

    query = transcripts.insert().values(
        call_id=entry.get("call_id"),
        timestamp=entry.get("timestamp"),
        text=entry.get("text"),
        source=entry.get("source"),
        created_at=entry.get("created_at"),
    )
    row_id = await db.execute(query)
    # read back the row (SQLite: last_insert_rowid)
    select_q = transcripts.select().where(transcripts.c.id == row_id)
    row = await db.fetch_one(select_q)
    result = dict(row) if row else {}
    logger.debug("Saved transcript row: %s", result)
    return result


async def query_transcripts(call_id: Optional[str] = None, from_ts: Optional[str] = None, to_ts: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Query transcripts. All timestamps are ISO strings; filtering is lexicographic (works with ISO).
    """
    db = get_database()
    q = transcripts.select()
    if call_id:
        q = q.where(transcripts.c.call_id == call_id)
    if from_ts:
        q = q.where(transcripts.c.timestamp >= from_ts)
    if to_ts:
        q = q.where(transcripts.c.timestamp <= to_ts)
    q = q.order_by(transcripts.c.timestamp.desc()).limit(limit)
    rows = await db.fetch_all(q)
    return [dict(r) for r in rows]
