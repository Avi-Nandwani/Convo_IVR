# app/storage/flows_store.py
"""
Simple flows store backed by the database.

Exposes:
 - save_flow(flow_obj: dict)
 - list_flows()
 - get_flow(flow_id)
"""
import logging
from typing import List, Dict, Any, Optional
from app.db.db import get_database
from app.models.db_models import flows
import datetime
import json

logger = logging.getLogger("conversational-ivr-poc.storage.flows")


async def save_flow(flow_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert a flow object (dict). Stores nodes as JSON string.
    """
    db = get_database()
    flow_id = flow_obj.get("flow_id")
    if not flow_id:
        raise ValueError("flow_obj must contain flow_id")

    now = flow_obj.get("updated_at") or datetime.datetime.utcnow().isoformat()
    nodes_json = json.dumps(flow_obj.get("nodes", []))
    # Try to update first; if no row updated then insert
    update_q = flows.update().where(flows.c.flow_id == flow_id).values(
        name=flow_obj.get("name"),
        description=flow_obj.get("description"),
        nodes_json=nodes_json,
        updated_at=now,
    )
    res = await db.execute(update_q)
    # Note: databases.execute for update returns number of rows affected for some backends, but SQLite may behave differently.
    # To be safe, check if a row exists; if not insert.
    select_q = flows.select().where(flows.c.flow_id == flow_id)
    existing = await db.fetch_one(select_q)
    if not existing:
        insert_q = flows.insert().values(
            flow_id=flow_id,
            name=flow_obj.get("name"),
            description=flow_obj.get("description"),
            nodes_json=nodes_json,
            updated_at=now,
        )
        await db.execute(insert_q)
        existing = await db.fetch_one(select_q)

    result = dict(existing) if existing else {}
    # parse nodes_json before returning
    if result.get("nodes_json"):
        try:
            result["nodes"] = json.loads(result["nodes_json"])
            del result["nodes_json"]
        except Exception:
            result["nodes"] = []
    return result


async def list_flows() -> List[Dict[str, Any]]:
    db = get_database()
    q = flows.select().order_by(flows.c.updated_at.desc())
    rows = await db.fetch_all(q)
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["nodes"] = json.loads(d.get("nodes_json", "[]"))
        except Exception:
            d["nodes"] = []
        d.pop("nodes_json", None)
        results.append(d)
    return results


async def get_flow(flow_id: str) -> Optional[Dict[str, Any]]:
    db = get_database()
    q = flows.select().where(flows.c.flow_id == flow_id)
    row = await db.fetch_one(q)
    if not row:
        return None
    d = dict(row)
    try:
        d["nodes"] = json.loads(d.get("nodes_json", "[]"))
    except Exception:
        d["nodes"] = []
    d.pop("nodes_json", None)
    return d
