"""HAL (Hardware Abstraction Layer) module with industrial safety.

Following 《工业Agent设计准则》:
- P1: 安全优先 - 零错误容忍
- P2: 可控接管 - 人工随时可介入
- P4: 闭环设计 - Execute → Confirm
- P6: 安全机制 - 白名单 + 审计日志
"""

from embodiedagentsys.hal.base_driver import BaseDriver
from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus
from embodiedagentsys.hal.validators import ActionValidator, ValidationResult
from embodiedagentsys.hal.audit import AuditLogger, AuditEntry, AuditEventType
from embodiedagentsys.hal.events import HALEventBus, HALEvent, HALEventData
from embodiedagentsys.hal.driver_registry import DriverRegistry

__all__ = [
    "BaseDriver",
    "ExecutionReceipt",
    "ExecutionStatus",
    "ActionValidator",
    "ValidationResult",
    "AuditLogger",
    "AuditEntry",
    "AuditEventType",
    "HALEventBus",
    "HALEvent",
    "HALEventData",
    "DriverRegistry",
]
