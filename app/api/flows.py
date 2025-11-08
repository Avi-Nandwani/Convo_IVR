# app/api/flows.py
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.config import get_settings
from datetime import datetime

logger = logging.getLogger("conversational-ivr-poc.api.flows")
router = APIRouter()

settings = get_settings()

# In-memory flow store fallback
_FLOW_STORE: Dict[str, Dict[str, Any]] = {}


class FlowNode(BaseModel):
    id: str
    type: str
    text: Optional[str] = None
    intent: Optional[str] = None
    reply: Optional[str] = None
    escalate: Optional[bool] = False


class Flow(BaseModel):
    flow_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: List[FlowNode]


@router.post("/", summary="Create or update a flow")
async def upsert_flow(flow: Flow):
    """
    Create or update a flow. This stores a simple DSL in-memory or via a flow store if you implement one.
    """
    flow_obj = flow.dict()
    flow_obj["updated_at"] = datetime.utcnow().isoformat()

    # try to persist via storage if present
    try:
        from app.storage.flows_store import save_flow  # type: ignore

        await save_flow(flow_obj)  # if implemented as async
        logger.info("Saved flow via flows_store: %s", flow.flow_id)
    except Exception:
        _FLOW_STORE[flow.flow_id] = flow_obj
        logger.info("Saved flow in-memory: %s", flow.flow_id)

    return {"status": "ok", "flow_id": flow.flow_id}


@router.get("/", summary="List flows")
async def list_flows():
    """
    Return all registered flows.
    """
    try:
        from app.storage.flows_store import list_flows as _list  # type: ignore

        flows = await _list()
    except Exception:
        flows = list(_FLOW_STORE.values())

    return {"flows": flows}


@router.get("/{flow_id}", summary="Get flow by id")
async def get_flow(flow_id: str):
    try:
        from app.storage.flows_store import get_flow as _get  # type: ignore

        flow = await _get(flow_id)
    except Exception:
        flow = _FLOW_STORE.get(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="flow not found")
    return flow
