# app/core/flow_engine.py
"""
Simple flow engine.

`run_flow(flow, intent=None, text=None)` returns a dict:
    {"reply": "<text>", "escalate": bool}

Flow format (accepted by flows.py):
{
  "flow_id": "faq-v1",
  "nodes": [
     {"id":"start","type":"ask","text":"..."},
     {"id":"account","type":"action","intent":"account_balance","reply":"Your balance is $42"},
     {"id":"support","type":"action","intent":"connect_agent","reply":"Connecting to agent","escalate":true}
  ]
}

This is intentionally minimal — it tries to match intent to node.intent and return node.reply.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("conversational-ivr-poc.core.flow_engine")


class FlowEngine:
    def __init__(self, settings):
        self.settings = settings

    async def run_flow(self, flow: Dict[str, Any], intent: Optional[str] = None, text: Optional[str] = None) -> Dict[str, Any]:
        logger.debug("Running flow engine for intent=%s", intent)
        nodes = flow.get("nodes", []) or []
        # find node by matching intent
        if intent:
            for n in nodes:
                if n.get("intent") and n.get("intent") == intent:
                    return {"reply": n.get("reply"), "escalate": bool(n.get("escalate", False))}
        # fallback: if there is a start node, return its text
        for n in nodes:
            if n.get("id") == "start" and n.get("type") in ("ask", "say"):
                return {"reply": n.get("text"), "escalate": False}
        # default fallback
        return {"reply": None, "escalate": False}
