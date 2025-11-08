# app/models/schemas.py
"""
Pydantic schemas for API inputs/outputs.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TranscriptEntry(BaseModel):
    id: Optional[int] = None
    call_id: str
    timestamp: Optional[str] = None
    text: str
    source: Optional[str] = "asr"


class FlowNode(BaseModel):
    id: str
    type: str
    text: Optional[str] = None
    intent: Optional[str] = None
    reply: Optional[str] = None
    escalate: Optional[bool] = False


class FlowIn(BaseModel):
    flow_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: List[FlowNode]


class FlowOut(FlowIn):
    updated_at: Optional[str] = None


class SessionData(BaseModel):
    call_id: str
    from_number: Optional[str] = Field(None, alias="from")
    to_number: Optional[str] = Field(None, alias="to")
    status: Optional[str] = "received"
    last_intent: Optional[str] = None
    last_reply: Optional[str] = None
    media_out: Optional[str] = None
    created_at: Optional[str] = None
    last_update: Optional[str] = None
    transcripts: Optional[List[TranscriptEntry]] = []
