# app/state/session_store.py
"""
Session store with Redis (async) backend and in-memory fallback.

Exports:
 - connect_redis(redis_url)
 - disconnect_redis()
 - set_session(call_id, session: dict)
 - get_session(call_id) -> dict | None
 - update_session(call_id, patch: dict)
 - append_transcript(call_id, transcript_entry: dict)
 - list_sessions() -> List[dict]

Behavior:
 - If REDIS_URL is not provided or Redis can't be imported/connected, falls back to in-memory dicts.
 - Uses JSON to serialize session objects in Redis.
"""
from typing import Optional, Any, Dict, List
import json
import logging
import asyncio

from app.config import get_settings

logger = logging.getLogger("conversational-ivr-poc.state.session_store")
settings = get_settings()

# Try to import redis.asyncio (modern redis-py)
_redis_client = None
_redis_available = False
try:
    import redis.asyncio as redis  # type: ignore

    _redis_module = redis
    _redis_client = None
    _redis_available = True
except Exception as exc:
    _redis_module = None
    _redis_client = None
    _redis_available = False
    logger.debug("redis.asyncio not available; session store will fallback to in-memory. %s", exc)

# In-memory fallback stores (process-local)
_INMEM_SESSIONS: Dict[str, Dict[str, Any]] = {}
_INMEM_TRANSCRIPTS: Dict[str, List[Dict[str, Any]]] = {}


async def connect_redis(redis_url: Optional[str]) -> bool:
    """
    Connect to Redis if available and redis_url provided.
    Returns True if a Redis connection is available, False otherwise.
    """
    global _redis_client, _redis_available
    if not redis_url:
        logger.debug("No redis_url provided; skipping Redis connection.")
        return False
    if not _redis_available:
        logger.debug("Redis library not available; skipping Redis connection.")
        return False

    try:
        _redis_client = _redis_module.from_url(redis_url, decode_responses=True)
        # ping to ensure connection; this may raise if unreachable
        await _redis_client.ping()
        logger.info("Connected to Redis at %s", redis_url)
        return True
    except Exception as exc:
        logger.exception("Failed to connect to Redis at %s: %s", redis_url, exc)
        _redis_client = None
        return False


async def disconnect_redis() -> None:
    """
    Disconnect / close the Redis client if connected.
    """
    global _redis_client
    if _redis_client is None:
        return
    try:
        await _redis_client.close()
    except Exception:
        # some redis versions implement close differently; ignore errors
        pass
    _redis_client = None
    logger.info("Redis client disconnected.")


# Helper keys
def _session_key(call_id: str) -> str:
    return f"session:{call_id}"


def _transcripts_key(call_id: str) -> str:
    return f"transcripts:{call_id}"


async def set_session(call_id: str, session: Dict[str, Any]) -> None:
    """
    Save or replace a session.
    """
    if _redis_client:
        try:
            await _redis_client.set(_session_key(call_id), json.dumps(session))
            return
        except Exception as exc:
            logger.debug("Redis set_session failed; falling back to in-memory: %s", exc)

    # fallback
    _INMEM_SESSIONS[call_id] = session


async def get_session(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a session dict or None.
    """
    if _redis_client:
        try:
            raw = await _redis_client.get(_session_key(call_id))
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug("Redis get_session failed; using in-memory: %s", exc)

    return _INMEM_SESSIONS.get(call_id)


async def update_session(call_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing session with patch dict (shallow merge). Returns updated session.
    If session doesn't exist, creates a new one with patch keys.
    """
    session = None
    if _redis_client:
        try:
            raw = await _redis_client.get(_session_key(call_id))
            session = json.loads(raw) if raw else {}
        except Exception as exc:
            logger.debug("Redis update_session failed; falling back to in-memory: %s", exc)
            session = None

    if session is None:
        session = _INMEM_SESSIONS.get(call_id, {})

    # merge (shallow)
    session.update(patch)
    # persist
    if _redis_client:
        try:
            await _redis_client.set(_session_key(call_id), json.dumps(session))
        except Exception as exc:
            logger.debug("Redis set in update_session failed; falling back to in-memory: %s", exc)
            _INMEM_SESSIONS[call_id] = session
    else:
        _INMEM_SESSIONS[call_id] = session

    return session


async def append_transcript(call_id: str, transcript_entry: Dict[str, Any]) -> None:
    """
    Append transcript entry to transcripts list for a call, and also append to session.transcripts.
    transcript_entry should be a dict (timestamp, text, source, ...).
    """
    # Save to Redis list (LPUSH for newest-first, but we will append normally using RPUSH)
    if _redis_client:
        try:
            await _redis_client.rpush(_transcripts_key(call_id), json.dumps(transcript_entry))
        except Exception as exc:
            logger.debug("Redis rpush failed in append_transcript; fallback to in-memory: %s", exc)
            _INMEM_TRANSCRIPTS.setdefault(call_id, []).append(transcript_entry)
    else:
        _INMEM_TRANSCRIPTS.setdefault(call_id, []).append(transcript_entry)

    # Also update the session object if present
    try:
        session = await get_session(call_id)
        if session is None:
            session = {"call_id": call_id, "transcripts": [transcript_entry]}
        else:
            transcripts = session.get("transcripts") or []
            transcripts.append(transcript_entry)
            session["transcripts"] = transcripts
        await set_session(call_id, session)
    except Exception as exc:
        logger.debug("Failed to append transcript into session store: %s", exc)


async def list_sessions() -> List[Dict[str, Any]]:
    """
    Return list of all sessions.
    Note: With Redis this scans keys `session:*`; might be expensive if large sets — okay for POC.
    """
    results: List[Dict[str, Any]] = []
    if _redis_client:
        try:
            keys = await _redis_client.keys("session:*")
            if not keys:
                return []
            # MGET - redis async supports mget
            raw_vals = await _redis_client.mget(*keys)
            for raw in raw_vals:
                if not raw:
                    continue
                try:
                    results.append(json.loads(raw))
                except Exception:
                    continue
            return results
        except Exception as exc:
            logger.debug("Redis list_sessions failed; falling back to in-memory: %s", exc)

    # fallback to in-memory
    return list(_INMEM_SESSIONS.values())


# Export convenience synchronous wrappers (for code that may call set_session without await)
def sync_loop() -> Optional[asyncio.AbstractEventLoop]:
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        return None
