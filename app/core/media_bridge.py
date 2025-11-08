# app/core/media_bridge.py
"""
Minimal media_bridge helper.

In production you would integrate with a media server (Janus, mediasoup), or return
an SDP offer and bridge RTP between SIP and WebRTC. For a POC we provide:

 - async escalate_to_agent(call_id): returns a dict with a webrtc_url or placeholder
"""
import logging
from typing import Dict, Any
from app.config import get_settings

logger = logging.getLogger("conversational-ivr-poc.core.media_bridge")
settings = get_settings()


async def escalate_to_agent(call_id: str) -> Dict[str, Any]:
    """
    Simplest possible escalate: return a URL the agent UI can open to handle the call.
    The dev can later implement SDP offer/answer exchange here.
    """
    logger.info("escalation requested for call %s", call_id)
    # produce a simple relative URL to an agent UI (you can implement dashboard/agent page later)
    webrtc_url = f"/agent?call_id={call_id}"
    return {"webrtc_url": webrtc_url, "note": "placeholder (implement real WebRTC bridge)"}
