from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.trace_store import trace_store


router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("/{trace_id}")
def get_trace(trace_id: str):
    trace = trace_store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Unknown trace_id: {trace_id}")
    return trace


@router.get("/{trace_id}/replay")
def replay_trace(trace_id: str):
    events = trace_store.replay(trace_id)
    if events is None:
        raise HTTPException(status_code=404, detail=f"Unknown trace_id: {trace_id}")
    return {"trace_id": trace_id, "events": events}

