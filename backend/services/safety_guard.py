from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SafetyDecision:
    allowed: bool
    reason: str = ""


class SafetyGuard:
    def __init__(self, limits: dict[str, Any] | None = None) -> None:
        cfg = limits or {}
        self.max_abs_x = float(cfg.get("max_abs_x", 0.6))
        self.max_abs_y = float(cfg.get("max_abs_y", 0.6))
        self.max_z = float(cfg.get("max_z", 1.2))
        self.max_speed = float(cfg.get("max_speed", 1.0))
        self.estop_engaged = False

    def trigger_estop(self) -> None:
        self.estop_engaged = True

    def clear_estop(self) -> None:
        self.estop_engaged = False

    def validate(self, action: str, params: dict[str, Any]) -> SafetyDecision:
        if action in {"estop", "emergency_stop"}:
            self.trigger_estop()
            return SafetyDecision(allowed=False, reason="emergency stop engaged")
        if self.estop_engaged:
            return SafetyDecision(allowed=False, reason="estop active")

        x = params.get("x")
        y = params.get("y")
        z = params.get("z")
        speed = params.get("speed")
        if isinstance(x, (int, float)) and abs(float(x)) > self.max_abs_x:
            return SafetyDecision(allowed=False, reason="x out of workspace")
        if isinstance(y, (int, float)) and abs(float(y)) > self.max_abs_y:
            return SafetyDecision(allowed=False, reason="y out of workspace")
        if isinstance(z, (int, float)) and float(z) > self.max_z:
            return SafetyDecision(allowed=False, reason="z out of workspace")
        if isinstance(speed, (int, float)) and float(speed) > self.max_speed:
            return SafetyDecision(allowed=False, reason="speed exceeds limit")
        return SafetyDecision(allowed=True, reason="ok")

