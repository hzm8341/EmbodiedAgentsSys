"""ACTION protocol - pending action commands."""

from dataclasses import dataclass
from typing import Optional
from embodiedagentsys.state.types import ProtocolType


@dataclass
class ActionEntry:
    """Single action in ACTION protocol."""
    action_type: str
    params: dict
    status: str = "pending"
    receipt_id: Optional[str] = None


def parse_action_protocol(content: dict) -> list[ActionEntry]:
    """Parse action protocol content into ActionEntry list."""
    actions = content.get("actions", [])
    return [ActionEntry(**a) for a in actions]


def format_action_protocol(actions: list[ActionEntry]) -> dict:
    """Format ActionEntry list into action protocol dict."""
    return {
        "schema_version": "EmbodiedAgentsSys.action.v1",
        "actions": [
            {
                "action_type": a.action_type,
                "params": a.params,
                "status": a.status,
                "receipt_id": a.receipt_id,
            }
            for a in actions
        ]
    }
