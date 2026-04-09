"""HAL types for structured execution and闭环确认."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class ExecutionStatus(str, Enum):
    """Execution status codes following P4闭环设计."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    TIMEOUT = "timeout"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class ExecutionReceipt:
    """Execution receipt for闭环确认.

    Every execute_action returns a receipt with unique ID.
    Caller must confirm receipt status before considering action complete.
    """
    action_type: str
    params: dict
    status: ExecutionStatus
    result_message: str
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    result_data: Optional[dict] = None

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.SUCCESS

    def is_terminal(self) -> bool:
        """Check if receipt represents terminal state (not pending)."""
        return self.status != ExecutionStatus.PENDING
