# app/core/llm_client.py
"""
LLM client wrapper.

Provides async `generate_response(text, context)` that returns a dict:
    {"intent": "<intent>", "reply": "<reply text>", ...}

Supports:
 - openai (API) if LLM_MODE=openai and api key present
 - local / rule-based fallback otherwise
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from app.config import get_settings

logger = logging.getLogger("conversational-ivr-poc.core.llm")
settings = get_settings()


class LLMClient:
    def __init__(self, settings):
        self.mode = (settings.LLM_MODE or "openai").lower()
        self.settings = settings
        self._openai = None
        if self.mode == "openai":
            try:
                import openai  # type: ignore

                self._openai = openai
                if settings.LLM_API_KEY:
                    self._openai.api_key = settings.LLM_API_KEY
            except Exception as exc:
                logger.warning("openai package not available: %s", exc)
                self._openai = None

    async def generate_response(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"intent": "none", "reply": "I didn't hear anything."}

        if self.mode == "openai" and self._openai:
            try:
                # Use ChatCompletion if available
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, self._blocking_openai_chat, text, context)
            except Exception as exc:
                logger.exception("OpenAI call failed: %s", exc)
                # fall through to fallback
        # fallback simple rule-based response
        return _rule_based_response(text, context)


    def _blocking_openai_chat(self, text: str, context: Optional[Dict[str, Any]]):
        """
        Blocking call to OpenAI ChatCompletion. Uses a simple prompt wrapper.
        Note: exact API may differ based on openai package version; adapt if needed.
        """
        if not self._openai:
            return _rule_based_response(text, context)

        try:
            system_prompt = "You are an assistant that maps spoken queries to intents and short replies."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User utterance: {text}\n\nReturn JSON with keys intent and reply. Keep reply short."},
            ]
            # Try ChatCompletion (gpt-3.5/4 style)
            resp = self._openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, max_tokens=150)
            content = resp["choices"][0]["message"]["content"]
            # Very simple parse: attempt to find lines "intent: ..." and "reply: ..."
            parsed = _parse_simple_intent_reply(content)
            if parsed:
                return parsed
            # fallback: return raw content as reply
            return {"intent": "unknown", "reply": content}
        except Exception as exc:
            logger.exception("OpenAI request failed: %s", exc)
            return _rule_based_response(text, context)


def _rule_based_response(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t = text.lower()
    if "balance" in t or "account" in t:
        return {"intent": "account_balance", "reply": "Your account balance is ₹3,420."}
    if "payment" in t or "bill" in t:
        return {"intent": "payments", "reply": "You can make payments via the web portal. Would you like a link?"}
    if "agent" in t or "human" in t or "representative" in t:
        return {"intent": "connect_agent", "reply": "Connecting you to an agent.", "escalate": True}
    if "hello" in t or "hi" in t:
        return {"intent": "greeting", "reply": "Hello! How can I help you today?"}
    return {"intent": "unknown", "reply": "Sorry, I didn't understand that. Could you repeat?"}


def _parse_simple_intent_reply(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse simple "intent: X\nreply: Y" style text into dict.
    """
    try:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        intent = None
        reply_lines = []
        for line in lines:
            if line.lower().startswith("intent:"):
                intent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("reply:"):
                reply_lines.append(line.split(":", 1)[1].strip())
            else:
                # treat as part of reply
                reply_lines.append(line)
        reply = " ".join(reply_lines).strip()
        if intent or reply:
            return {"intent": intent or "unknown", "reply": reply or " "}
    except Exception:
        pass
    return None
