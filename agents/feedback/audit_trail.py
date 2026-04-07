"""Tamper-proof audit logging for execution trace."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List
import hashlib
import json


@dataclass
class ExecutionLog:
    """Single audit log entry."""
    event_type: str  # "validation_passed", "validation_failed", "execution_started", etc.
    action_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""  # hash of previous event (chain)
    event_hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash for tamper detection."""
        payload = {
            "event_type": self.event_type,
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "previous_hash": self.previous_hash,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def __post_init__(self):
        """Compute hash on creation."""
        self.event_hash = self.compute_hash()


class AuditTrail:
    """In-memory audit trail with chain integrity verification."""

    def __init__(self):
        self.events: List[ExecutionLog] = []

    def log_event(self, event: ExecutionLog) -> None:
        """Log an event (with hash chain)."""
        if self.events:
            event.previous_hash = self.events[-1].event_hash
            event.event_hash = event.compute_hash()
        self.events.append(event)

    def verify_chain_integrity(self) -> bool:
        """Verify no events were tampered with."""
        for i, event in enumerate(self.events):
            expected_hash = event.compute_hash()
            if event.event_hash != expected_hash:
                return False
            if i > 0 and event.previous_hash != self.events[i-1].event_hash:
                return False
        return True

    def export_json(self) -> str:
        """Export audit trail as JSON."""
        return json.dumps(
            [asdict(e) for e in self.events],
            default=str,
            indent=2
        )
