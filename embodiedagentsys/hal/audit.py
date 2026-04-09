"""Audit logging for P6安全机制层 - 完整审计日志.

Every action must be logged with:
- 指令来源
- 校验结果
- 执行时间
- 反馈状态
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus


class AuditEventType(Enum):
    """Types of auditable events."""
    VALIDATION_RESULT = "validation_result"
    ACTION_EXECUTED = "action_executed"
    ACTION_CONFIRMED = "action_confirmed"
    ACTION_FAILED = "action_failed"
    EMERGENCY_STOP = "emergency_stop"
    SYSTEM_ERROR = "system_error"


@dataclass
class AuditEntry:
    """Single audit log entry."""
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=datetime.now)
    receipt_id: Optional[str] = None
    action_type: Optional[str] = None
    params: Optional[dict] = None
    status: Optional[str] = None
    operator: str = "system"
    reason: Optional[str] = None
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "receipt_id": self.receipt_id,
            "action_type": self.action_type,
            "params": self.params,
            "status": self.status,
            "operator": self.operator,
            "reason": self.reason,
            "details": self.details,
        }


class AuditLogger:
    """Audit logger for operation tracking.

    Following P6安全机制层:
    - 全链路操作记录
    - 日志不可篡改 (append-only)
    - 支持事后追溯
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []

    def log_action(
        self,
        receipt: ExecutionReceipt,
        operator: str = "system"
    ) -> AuditEntry:
        """Log action execution result."""
        entry = AuditEntry(
            event_type=AuditEventType.ACTION_EXECUTED,
            receipt_id=receipt.receipt_id,
            action_type=receipt.action_type,
            params=receipt.params,
            status=receipt.status.value,
            operator=operator,
            details=receipt.result_data,
        )
        self._entries.append(entry)
        return entry

    def log_validation(
        self,
        action_type: str,
        params: dict,
        allowed: bool,
        operator: str = "system",
        reason: Optional[str] = None
    ) -> AuditEntry:
        """Log validation decision."""
        entry = AuditEntry(
            event_type=AuditEventType.VALIDATION_RESULT,
            action_type=action_type,
            params=params,
            status="allowed" if allowed else "rejected",
            operator=operator,
            reason=reason,
        )
        self._entries.append(entry)
        return entry

    def log_emergency_stop(
        self,
        operator: str = "system",
        reason: Optional[str] = None
    ) -> AuditEntry:
        """Log emergency stop event."""
        entry = AuditEntry(
            event_type=AuditEventType.EMERGENCY_STOP,
            operator=operator,
            reason=reason,
        )
        self._entries.append(entry)
        return entry

    def log_confirmation(
        self,
        receipt_id: str,
        confirmed: bool,
        operator: str = "system"
    ) -> AuditEntry:
        """Log execution confirmation (闭环确认)."""
        entry = AuditEntry(
            event_type=AuditEventType.ACTION_CONFIRMED if confirmed else AuditEventType.ACTION_FAILED,
            receipt_id=receipt_id,
            status="confirmed" if confirmed else "unconfirmed",
            operator=operator,
        )
        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        limit: Optional[int] = None,
        event_type: Optional[AuditEventType] = None
    ) -> list[AuditEntry]:
        """Get audit entries, optionally filtered."""
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if limit:
            entries = entries[-limit:]
        return entries
