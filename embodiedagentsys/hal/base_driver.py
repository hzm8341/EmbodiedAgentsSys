"""Base driver interface for hardware abstraction with industrial safety."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus


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
