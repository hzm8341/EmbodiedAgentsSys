import pytest

from agents.core.types import RobotObservation
from backend.models.task_protocol import TaskRequest
from backend.services.task_execution_service import TaskExecutionService


@pytest.mark.asyncio
async def test_task_execution_service_replans_once(monkeypatch):
    service = TaskExecutionService()

    class _FakeBridge:
        def __init__(self):
            self.stream_manager = None
            self.calls = 0

        async def run_with_telemetry(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                await self.stream_manager.broadcast({"type": "result", "timestamp": 1.0, "payload": {"task_success": False, "steps_executed": 1}})
                return {"task_success": False, "steps_executed": 1}
            await self.stream_manager.broadcast({"type": "result", "timestamp": 2.0, "payload": {"task_success": True, "steps_executed": 1}})
            return {"task_success": True, "steps_executed": 1}

    fake_bridge = _FakeBridge()
    monkeypatch.setattr("backend.services.task_execution_service.agent_bridge", fake_bridge)
    monkeypatch.setattr(
        "backend.services.task_execution_service.SCENARIOS",
        {},
    )
    monkeypatch.setattr(
        TaskExecutionService,
        "_simulation_service",
        staticmethod(lambda: type("S", (), {"get_scene": lambda self: {}})()),
    )

    req = TaskRequest(task="pick", observation_state={"gripper_open": 1.0})
    result = await service.execute_task(req)
    assert result.success is True
    assert result.steps_executed == 2

