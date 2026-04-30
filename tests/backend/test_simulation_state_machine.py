from __future__ import annotations

from types import SimpleNamespace

from backend.services.simulation import SimulationService


class _FakeDriver:
    def execute_action(self, action: str, params: dict):
        return SimpleNamespace(status=SimpleNamespace(value="success"), result_message="ok", result_data={})

    def get_joint_positions(self):
        return {}

    def reset_to_home(self):
        return None

    def reset(self):
        return None


def test_simulation_state_transitions_pause_resume_abort():
    service = SimulationService()
    service._driver = _FakeDriver()
    service._execution_state = "running"

    service.pause_execution()
    assert service.execution_state == "paused"

    service.resume_execution()
    assert service.execution_state == "running"

    service.abort_execution()
    assert service.execution_state == "aborted"

