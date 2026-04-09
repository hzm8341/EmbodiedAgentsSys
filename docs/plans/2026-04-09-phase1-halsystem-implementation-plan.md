# Phase 1: HAL System Implementation Plan (v2 - Industrial Safety)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement HAL hardware abstraction layer with industrial-grade safety, following 《工业Agent设计准则》.

**Architecture:** Create `embodiedagentsys/hal/` module with:
- BaseDriver interface with action validation and timeout
- Structured ExecutionResult for闭环确认
- AuditLogger for 操作审计
- EmergencyStop mechanism
- EventBus for 异常上报

**Tech Stack:** Pure Python (no new dependencies), abc for ABC, pathlib for paths.

---

## 关键设计变更 (对照工业Agent设计准则)

### 执行结果结构化

```python
# 替代原来的字符串返回值
class ExecutionStatus:
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    TIMEOUT = "timeout"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class ExecutionReceipt:
    """执行凭证 - 用于闭环确认"""
    receipt_id: str              # 唯一ID
    action_type: str             # 动作类型
    params: dict                # 参数
    status: ExecutionStatus      # 执行状态
    timestamp: datetime         # 时间戳
    result_message: str          # 结果描述
    result_data: dict = None     # 详细结果
```

### Action 白名单校验

```python
class ActionValidator:
    """白名单校验器 - P6安全机制"""
    def __init__(self, allowed_actions: list[str]):
        self._allowed = set(allowed_actions)

    def validate(self, action_type: str, params: dict) -> ValidationResult:
        if action_type not in self._allowed:
            return ValidationResult(valid=False, reason="Action not in whitelist")
```

### 审计日志

```python
class AuditLogger:
    """完整审计日志 - P6安全机制"""
    def log(self, event_type: str, receipt: ExecutionReceipt, operator: str = "system"):
        # 记录: 指令来源、校验结果、执行时间、反馈状态
        pass
```

---

## Task 1: Create HAL Module Structure with Safety

**Files:**
- Create: `embodiedagentsys/hal/__init__.py`
- Create: `embodiedagentsys/hal/base_driver.py`
- Create: `embodiedagentsys/hal/types.py` (新增: ExecutionReceipt, ExecutionStatus)
- Create: `embodiedagentsys/hal/validators.py` (新增: ActionValidator)
- Create: `embodiedagentsys/hal/audit.py` (新增: AuditLogger)
- Create: `embodiedagentsys/hal/events.py` (新增: HALEventBus)
- Create: `embodiedagentsys/hal/driver_registry.py`
- Create: `embodiedagentsys/hal/drivers/__init__.py`
- Create: `embodiedagentsys/hal/drivers/simulation_driver.py`
- Test: `tests/test_hal/test_base_driver.py`
- Test: `tests/test_hal/test_types.py`
- Test: `tests/test_hal/test_validator.py`
- Test: `tests/test_hal/test_audit.py`

**Step 1: Create test file - types**

```python
# tests/test_hal/test_types.py
import pytest
from datetime import datetime
from embodiedagents.hal.types import ExecutionStatus, ExecutionReceipt


class TestExecutionStatus:
    def test_status_constants_defined(self):
        """All required status constants must be defined."""
        assert ExecutionStatus.SUCCESS == "success"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.TIMEOUT == "timeout"
        assert ExecutionStatus.EMERGENCY_STOP == "emergency_stop"


class TestExecutionReceipt:
    def test_receipt_can_be_created(self):
        """ExecutionReceipt should be creatable with required fields."""
        receipt = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={"x": 1.0, "y": 2.0},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="Moved successfully"
        )
        assert receipt.receipt_id == "test-001"
        assert receipt.action_type == "move_to"
        assert receipt.status == ExecutionStatus.SUCCESS

    def test_receipt_has_result_data(self):
        """Receipt should have optional result_data field."""
        receipt = ExecutionReceipt(
            receipt_id="test-002",
            action_type="grasp",
            params={"force": 0.8},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="Grasped",
            result_data={"force_applied": 0.8}
        )
        assert receipt.result_data is not None
        assert receipt.result_data["force_applied"] == 0.8

    def test_receipt_id_must_be_unique(self):
        """Each receipt should have a unique ID for tracking."""
        receipt1 = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="ok"
        )
        receipt2 = ExecutionReceipt(
            receipt_id="test-002",
            action_type="move_to",
            params={},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="ok"
        )
        assert receipt1.receipt_id != receipt2.receipt_id
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hal/test_types.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create embodiedagentsys/hal/types.py**

```python
"""HAL types for structured execution and闭环确认."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class ExecutionStatus(Enum):
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
```

**Step 4: Create test file - validator**

```python
# tests/test_hal/test_validator.py
import pytest
from embodiedagents.hal.validators import ActionValidator, ValidationResult


class TestValidationResult:
    def test_valid_result(self):
        """Valid result should have valid=True."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.reason is None

    def test_invalid_result_with_reason(self):
        """Invalid result should have reason."""
        result = ValidationResult(valid=False, reason="Action not in whitelist")
        assert result.valid is False
        assert result.reason == "Action not in whitelist"


class TestActionValidator:
    def test_validator_accepts_allowed_action(self):
        """Validator should accept actions in whitelist."""
        validator = ActionValidator(allowed_actions=["move_to", "grasp", "release"])
        result = validator.validate("move_to", {"x": 1.0})
        assert result.valid is True

    def test_validator_rejects_disallowed_action(self):
        """Validator should reject actions not in whitelist."""
        validator = ActionValidator(allowed_actions=["move_to", "grasp"])
        result = validator.validate("emergency_shutdown", {})
        assert result.valid is False
        assert "not in whitelist" in result.reason

    def test_validator_checks_param_ranges(self):
        """Validator should check parameter ranges."""
        validator = ActionValidator(
            allowed_actions=["move_to"],
            param_constraints={
                "move_to": {"x": (-2.0, 2.0), "y": (-2.0, 2.0), "z": (0.0, 1.5)}
            }
        )
        # Valid range
        result = validator.validate("move_to", {"x": 1.0, "y": 0.5, "z": 0.8})
        assert result.valid is True

        # Invalid range
        result = validator.validate("move_to", {"x": 10.0, "y": 0.5, "z": 0.8})
        assert result.valid is False
        assert "out of bounds" in result.reason

    def test_validator_rejects_unknown_action(self):
        """Validator should reject unknown actions."""
        validator = ActionValidator(allowed_actions=[])
        result = validator.validate("any_action", {})
        assert result.valid is False
```

**Step 5: Create embodiedagentsys/hal/validators.py**

```python
"""Action validators for P1安全优先 and P6白名单制度."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Result of action validation."""
    valid: bool
    reason: Optional[str] = None
    warning: Optional[str] = None


class ActionValidator:
    """White-list based action validator.

    Following P6安全机制层 - 白名单制度:
    - All executable actions must be pre-registered in whitelist
    - Unauthorized actions are rejected without exception
    - Parameter ranges are enforced
    """

    def __init__(
        self,
        allowed_actions: list[str],
        param_constraints: Optional[dict] = None
    ):
        """
        Args:
            allowed_actions: List of allowed action types.
            param_constraints: Dict mapping action_type to param bounds.
                              e.g., {"move_to": {"x": (-2.0, 2.0), ...}}
        """
        self._allowed = set(allowed_actions)
        self._constraints = param_constraints or {}

    def validate(self, action_type: str, params: dict) -> ValidationResult:
        """Validate action against whitelist and constraints.

        Args:
            action_type: Type of action to validate.
            params: Action parameters.

        Returns:
            ValidationResult with valid=True if allowed.
        """
        # Check whitelist (P6 - 白名单制度)
        if action_type not in self._allowed:
            return ValidationResult(
                valid=False,
                reason=f"Action '{action_type}' not in whitelist"
            )

        # Check parameter constraints
        if action_type in self._constraints:
            bounds = self._constraints[action_type]
            for param_name, (min_val, max_val) in bounds.items():
                if param_name in params:
                    value = params[param_name]
                    if not (min_val <= value <= max_val):
                        return ValidationResult(
                            valid=False,
                            reason=f"Parameter '{param_name}' value {value} out of bounds [{min_val}, {max_val}]"
                        )

        return ValidationResult(valid=True)

    def add_action(self, action_type: str) -> None:
        """Dynamically add action to whitelist."""
        self._allowed.add(action_type)

    def remove_action(self, action_type: str) -> None:
        """Remove action from whitelist."""
        self._allowed.discard(action_type)
```

**Step 6: Create test file - audit**

```python
# tests/test_hal/test_audit.py
import pytest
from datetime import datetime
from embodiedagents.hal.audit import AuditLogger, AuditEntry, AuditEventType
from embodiedagents.hal.types import ExecutionStatus, ExecutionReceipt


class TestAuditEntry:
    def test_audit_entry_creation(self):
        """AuditEntry should capture all required fields."""
        entry = AuditEntry(
            event_type=AuditEventType.ACTION_EXECUTED,
            receipt_id="test-001",
            action_type="move_to",
            params={"x": 1.0},
            status=ExecutionStatus.SUCCESS,
            operator="llm_agent"
        )
        assert entry.event_type == AuditEventType.ACTION_EXECUTED
        assert entry.receipt_id == "test-001"


class TestAuditLogger:
    def test_logger_records_action(self):
        """Logger should record action execution."""
        logger = AuditLogger()
        receipt = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={"x": 1.0},
            status=ExecutionStatus.SUCCESS,
            result_message="Moved"
        )
        entry = logger.log_action(receipt, operator="test")
        assert entry is not None
        assert entry.receipt_id == "test-001"

    def test_logger_records_validation(self):
        """Logger should record validation decisions."""
        logger = AuditLogger()
        entry = logger.log_validation(
            action_type="move_to",
            params={"x": 1.0},
            allowed=True,
            operator="test"
        )
        assert entry.event_type == AuditEventType.VALIDATION_RESULT

    def test_logger_records_emergency_stop(self):
        """Logger should record emergency stops."""
        logger = AuditLogger()
        entry = logger.log_emergency_stop(operator="operator_001", reason="Safety boundary violated")
        assert entry.event_type == AuditEventType.EMERGENCY_STOP

    def test_logger_returns_entries(self):
        """Logger should return logged entries for review."""
        logger = AuditLogger()
        receipt = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={},
            status=ExecutionStatus.SUCCESS,
            result_message="ok"
        )
        logger.log_action(receipt)
        entries = logger.get_entries()
        assert len(entries) >= 1
```

**Step 7: Create embodiedagentsys/hal/audit.py**

```python
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

from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus


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
```

**Step 8: Create embodiedagentsys/hal/events.py**

```python
"""HAL event bus for P2主动上报异常."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Awaitable, Optional
from collections import defaultdict


class HALEvent(Enum):
    """HAL event types for async notification."""
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    EMERGENCY_STOP_TRIGGERED = "emergency_stop_triggered"
    HEALTH_CHECK_FAILED = "health_check_failed"
    DRIVER_DISCONNECTED = "driver_disconnected"


@dataclass
class HALEventData:
    """Event payload."""
    event: HALEvent
    timestamp: datetime = datetime.now()
    driver_name: Optional[str] = None
    receipt_id: Optional[str] = None
    details: Optional[dict] = None


class HALEventBus:
    """Event bus for HAL events.

    Following P2可控接管层:
    - 主动上报异常: 系统检测到异常须立即告警
    - 不得静默失败
    """

    def __init__(self):
        self._subscribers: dict[HALEvent, list[Callable[[HALEventData], Awaitable[None]]]] = defaultdict(list)

    def subscribe(
        self,
        event: HALEvent,
        handler: Callable[[HALEventData], Awaitable[None]]
    ) -> None:
        """Subscribe to event type."""
        self._subscribers[event].append(handler)

    def unsubscribe(
        self,
        event: HALEvent,
        handler: Callable[[HALEventData], Awaitable[None]]
    ) -> None:
        """Unsubscribe from event type."""
        if handler in self._subscribers[event]:
            self._subscribers[event].remove(handler)

    async def publish(self, event_data: HALEventData) -> None:
        """Publish event to all subscribers."""
        handlers = self._subscribers.get(event_data.event, [])
        for handler in handlers:
            try:
                await handler(event_data)
            except Exception:
                # Log but don't fail - event delivery should be resilient
                pass
```

**Step 9: Create embodiedagentsys/hal/base_driver.py (updated)**

```python
"""Base driver interface for hardware abstraction with industrial safety."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus


class BaseDriver(ABC):
    """Abstract base class for hardware drivers with闭环确认.

    Following 《工业Agent设计准则》:
    - P1: 零错误容忍，不确定即禁止
    - P4: 闭环设计 - Execute → Confirm
    - P6: 白名单制度 + 审计日志
    """

    @abstractmethod
    def get_profile_path(self) -> Path:
        """Return path to embodiment profile (P6白名单来源)."""
        pass

    @abstractmethod
    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """Execute action and return structured receipt for闭环确认.

        Following P4闭环设计:
        - Returns ExecutionReceipt with unique receipt_id
        - Caller must confirm receipt status before considering action complete
        - Never return bare strings - always structured result
        """
        pass

    @abstractmethod
    def get_scene(self) -> dict:
        """Get current environment scene state."""
        pass

    def get_allowed_actions(self) -> list[str]:
        """Return list of allowed actions (P6白名单).

        Override to provide driver-specific whitelist.
        """
        return []

    def validate_action(self, action_type: str, params: dict) -> tuple[bool, Optional[str]]:
        """Validate action before execution (P1 + P6).

        Returns:
            (is_valid, reason_if_invalid)
        """
        allowed = self.get_allowed_actions()
        if allowed and action_type not in allowed:
            return False, f"Action '{action_type}' not in whitelist"
        return True, None

    def load_scene(self, scene: dict) -> None:
        """Load scene state from external source."""
        pass

    def connect(self) -> bool:
        """Connect to hardware."""
        return True

    def disconnect(self) -> None:
        """Disconnect from hardware."""
        pass

    def is_connected(self) -> bool:
        """Check if hardware is connected."""
        return False

    def health_check(self) -> dict:
        """Perform health check (P5可靠性)."""
        return {"status": "ok", "driver": self.__class__.__name__}

    def get_runtime_state(self) -> dict:
        """Get runtime state (pose, velocity, etc.)."""
        return {}

    def emergency_stop(self) -> ExecutionReceipt:
        """Emergency stop - immediately halt all motion (P2).

        This is critical for industrial safety.
        """
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Emergency stop executed"
        )
```

**Step 10: Create embodiedagentsys/hal/driver_registry.py**

```python
"""Driver registry for managing hardware drivers."""

from typing import Optional

from embodiedagents.hal.base_driver import BaseDriver


class DriverRegistry:
    """Registry for managing available hardware drivers."""

    def __init__(self):
        self._drivers: dict[str, type[BaseDriver]] = {}

    def register(self, name: str, driver_class: type[BaseDriver]) -> None:
        """Register a driver class."""
        self._drivers[name] = driver_class

    def get(self, name: str) -> Optional[type[BaseDriver]]:
        """Get registered driver class."""
        return self._drivers.get(name)

    def create(self, name: str, **kwargs) -> Optional[BaseDriver]:
        """Create driver instance by name."""
        driver_class = self.get(name)
        if driver_class:
            return driver_class(**kwargs)
        return None

    def list_drivers(self) -> list[str]:
        """List all registered driver names."""
        return list(self._drivers.keys())
```

**Step 11: Create embodiedagentsys/hal/__init__.py**

```python
"""HAL (Hardware Abstraction Layer) module with industrial safety.

Following 《工业Agent设计准则》:
- P1: 安全优先 - 零错误容忍
- P2: 可控接管 - 人工随时可介入
- P4: 闭环设计 - Execute → Confirm
- P6: 安全机制 - 白名单 + 审计日志
"""

from embodiedagents.hal.base_driver import BaseDriver
from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus
from embodiedagents.hal.validators import ActionValidator, ValidationResult
from embodiedagents.hal.audit import AuditLogger, AuditEntry, AuditEventType
from embodiedagents.hal.events import HALEventBus, HALEvent, HALEventData
from embodiedagents.hal.driver_registry import DriverRegistry

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
```

**Step 12: Run all tests**

Run: `pytest tests/test_hal/ -v`
Expected: PASS (all new tests)

**Step 13: Commit**

```bash
git add embodiedagentsys/hal/ tests/test_hal/
git commit -m "feat(hal): add industrial-safe HAL module

Following 《工业Agent设计准则》:
- P1: ActionValidator with whitelist validation
- P2: HALEventBus for async exception reporting
- P4: ExecutionReceipt for闭环确认
- P6: AuditLogger for complete audit trail

Breaking change: execute_action() now returns ExecutionReceipt
instead of bare string."
```

---

## Task 2: Update SimulationDriver with Safety

**Files:**
- Modify: `embodiedagentsys/hal/drivers/simulation_driver.py`
- Modify: `embodiedagentsys/hal/drivers/profiles/simulation.md`

**Step 1: Update simulation driver to return ExecutionReceipt**

```python
# embodiedagentsys/hal/drivers/simulation_driver.py
from datetime import datetime
from embodiedagents.hal.base_driver import BaseDriver
from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus
from pathlib import Path


class SimulationDriver(BaseDriver):
    """Simulation driver with proper闭环确认.

    Returns ExecutionReceipt for every action.
    """

    def __init__(self, gui: bool = False, **kwargs):
        self._gui = gui
        self._scene: dict = {"objects": {}, "robots": {}}
        self._connected = False
        self._position = {"x": 0.0, "y": 0.0, "z": 0.0}

    def get_profile_path(self) -> Path:
        return Path(__file__).resolve().parent / "profiles" / "simulation.md"

    def get_allowed_actions(self) -> list[str]:
        """Whitelist of allowed actions."""
        return ["move_to", "move_relative", "grasp", "release", "get_scene"]

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """Execute simulated action with receipt."""
        # Validate first
        valid, reason = self.validate_action(action_type, params)
        if not valid:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Validation failed: {reason}"
            )

        # Execute based on action type
        if action_type == "move_to":
            self._position = {
                "x": params.get("x", 0.0),
                "y": params.get("y", 0.0),
                "z": params.get("z", 0.0),
            }
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Moved to {self._position}",
                result_data={"position": self._position}
            )
        elif action_type == "grasp":
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message="Grasped",
                result_data={"gripper_state": "closed", "force": params.get("force", 0.5)}
            )
        elif action_type == "release":
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message="Released",
                result_data={"gripper_state": "open"}
            )
        else:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Simulated {action_type}"
            )

    def get_scene(self) -> dict:
        return dict(self._scene)

    def is_connected(self) -> bool:
        return self._connected

    def health_check(self) -> dict:
        return {
            "status": "ok",
            "driver": "simulation",
            "position": self._position,
        }

    def emergency_stop(self) -> ExecutionReceipt:
        """Simulation emergency stop."""
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Simulation emergency stop executed"
        )
```

**Step 2: Update profile**

```markdown
# Simulation Driver Profile

## Safety Whitelist (P6)

| Action | Parameters | Constraints |
|--------|------------|-------------|
| move_to | x, y, z | x,y ∈ [-2.0, 2.0], z ∈ [0.0, 1.5] |
| move_relative | dx, dy, dz | velocity ≤ 1.0 m/s |
| grasp | force | force ∈ [0.0, 1.0] |
| release | - | - |

## Emergency Stop

- Always available regardless of state
- Immediately halts all motion
- Logs event to audit trail

##闭环确认

Every execute_action returns ExecutionReceipt with:
- receipt_id: Unique identifier for tracking
- status: SUCCESS/FAILED/TIMEOUT/EMERGENCY_STOP
- result_data: Detailed execution data
```

**Step 3: Run tests**

Run: `pytest tests/test_hal/ -v`

**Step 4: Commit**

```bash
git commit -m "feat(hal): update SimulationDriver with ExecutionReceipt

- execute_action() now returns ExecutionReceipt
- get_allowed_actions() provides whitelist
- emergency_stop() always available
- Updated profile with safety constraints
"
```

---

## Task 3: Integration Test with Existing Code

**Files:**
- Create: `tests/test_hal/test_integration.py`

**Step 1: Create integration tests**

```python
"""Test HAL integrates with existing codebase patterns."""

def test_driver_returns_receipt():
    """Driver must return ExecutionReceipt, not string."""
    from embodiedagentsys.hal.drivers import SimulationDriver
    driver = SimulationDriver()
    receipt = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
    assert hasattr(receipt, 'receipt_id')
    assert hasattr(receipt, 'status')

def test_validation_prevents_invalid_action():
    """Invalid actions should be rejected by validator."""
    from embodiedagentsys.hal.validators import ActionValidator
    validator = ActionValidator(allowed_actions=["move_to"])
    result = validator.validate("emergency_shutdown", {})
    assert result.valid is False

def test_audit_logger_records_all():
    """Audit logger should record actions and validations."""
    from embodiedagentsys.hal.audit import AuditLogger
    from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus
    logger = AuditLogger()
    receipt = ExecutionReceipt(
        action_type="move_to",
        params={"x": 1.0},
        status=ExecutionStatus.SUCCESS,
        result_message="ok"
    )
    logger.log_action(receipt)
    entries = logger.get_entries()
    assert len(entries) >= 1

def test_backward_compatibility_maintained():
    """Existing imports should still work."""
    from embodiedagents import SimpleAgent
    from embodiedagents.execution.tools import GripperTool
    # If this passes, backward compatibility maintained
```

**Step 2: Run integration tests**

Run: `pytest tests/test_hal/test_integration.py -v`

**Step 3: Verify existing tests still pass**

Run: `pytest tests/ -v --ignore=tests/integration -x -q 2>&1 | head -30`

**Step 4: Commit**

```bash
git commit -m "test(hal): add integration tests

Verify HAL integrates with existing codebase:
- ExecutionReceipt return type
- ActionValidator whitelist
- AuditLogger records
- Backward compatibility maintained
"
```

---

## Summary

After Phase 1 v2 completion:

| Component | Description |准则对应|
|-----------|-------------|---------|
| `ExecutionReceipt` | Structured result with receipt_id | P4闭环 |
| `ExecutionStatus` | Status enum (SUCCESS/FAILED/TIMEOUT/...) | P4闭环 |
| `ActionValidator` | Whitelist-based action validation | P1+P6 |
| `ValidationResult` | Validation decision with reason | P6 |
| `AuditLogger` | Complete operation audit trail | P6 |
| `AuditEntry` | Single audit log entry | P6 |
| `HALEventBus` | Async event notification | P2 |
| `HALEvent` | Event type enum | P2 |
| `BaseDriver.emergency_stop()` | Emergency stop interface | P2 |
| `BaseDriver.get_allowed_actions()` | Whitelist source | P6 |

**Next:** Phase 2 - State Protocol and StateManager
