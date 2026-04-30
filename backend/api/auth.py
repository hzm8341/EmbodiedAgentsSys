from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


ROLE_LEVEL = {
    "viewer": 1,
    "operator": 2,
    "approver": 3,
    "admin": 4,
}


def _tokens() -> dict[str, str]:
    return {
        "viewer-token": "viewer",
        "operator-token": "operator",
        "approver-token": "approver",
        "admin-token": "admin",
        os.getenv("REAL_MODE_OPERATOR_TOKEN", ""): "operator",
    }


def resolve_role(token: str | None) -> str | None:
    if not token:
        return None
    return _tokens().get(token)


def ensure_role(token: str | None, required: str) -> str:
    role = resolve_role(token)
    if role is None:
        raise HTTPException(status_code=401, detail="invalid or missing auth token")
    if ROLE_LEVEL[role] < ROLE_LEVEL[required]:
        raise HTTPException(status_code=403, detail=f"{required} role required")
    return role


router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    token: str


@router.post("/validate")
def validate_token(req: AuthRequest):
    role = resolve_role(req.token)
    if role is None:
        raise HTTPException(status_code=401, detail="invalid token")
    return {"valid": True, "role": role}

