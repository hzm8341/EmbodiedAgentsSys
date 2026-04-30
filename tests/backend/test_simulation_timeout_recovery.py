from __future__ import annotations

import time

import pytest

from backend.services.simulation import SimulationService


class _SlowDriver:
    def execute_action(self, action: str, params: dict):
        time.sleep(0.2)
        return None

    def get_joint_positions(self):
        return {}

    def reset_to_home(self):
        return None

    def reset(self):
        return None


def test_simulation_timeout_sets_error_and_recovers(monkeypatch):
    monkeypatch.setenv("SIM_ACTION_TIMEOUT_SEC", "0.01")
    service = SimulationService()
    service._driver = _SlowDriver()

    with pytest.raises(TimeoutError):
        service.execute_action("move_to", {"x": 0.1, "y": 0.0, "z": 0.2})

    assert service.execution_state == "idle"

