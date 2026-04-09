"""Integration tests for HAL module with existing codebase."""

import pytest


class TestHALIntegration:
    """Test HAL integrates with existing codebase patterns."""

    def test_driver_registry_singleton_pattern(self):
        """DriverRegistry can be used as singleton."""
        from embodiedagentsys.hal import DriverRegistry
        registry = DriverRegistry()
        assert registry is not None
        assert hasattr(registry, 'register')
        assert hasattr(registry, 'create')

    def test_simulation_driver_compatible_with_base(self):
        """SimulationDriver is a valid BaseDriver subclass."""
        from embodiedagentsys.hal.drivers import SimulationDriver
        from embodiedagentsys.hal.base_driver import BaseDriver
        driver = SimulationDriver()
        assert isinstance(driver, BaseDriver)

    def test_driver_registration_flow(self):
        """Test complete registration and creation flow."""
        from embodiedagentsys.hal import DriverRegistry
        from embodiedagentsys.hal.drivers import SimulationDriver

        registry = DriverRegistry()
        registry.register("sim", SimulationDriver)
        assert "sim" in registry.list_drivers()

        driver = registry.create("sim")
        assert driver is not None
        assert isinstance(driver, SimulationDriver)

        receipt = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
        assert hasattr(receipt, 'receipt_id')

    def test_backward_compatibility_existing_imports(self):
        """Existing code should continue to work."""
        # These imports should not break
        from agents.simple_agent import SimpleAgent
        from agents.execution.tools.gripper_tool import GripperTool
        assert SimpleAgent is not None
        assert GripperTool is not None

    def test_validator_with_constraints(self):
        """ActionValidator should enforce param ranges."""
        from embodiedagentsys.hal.validators import ActionValidator

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

    def test_audit_logger_records_all(self):
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
        assert entries[0].action_type == "move_to"

    def test_hal_event_bus_subscribe(self):
        """HALEventBus should support subscribe/publish."""
        from embodiedagentsys.hal.events import HALEventBus, HALEvent, HALEventData

        bus = HALEventBus()
        events_received = []

        async def handler(event_data):
            events_received.append(event_data)

        bus.subscribe(HALEvent.EXECUTION_COMPLETED, handler)
        # Note: publish is async, so we just verify subscription works
        assert len(bus._subscribers[HALEvent.EXECUTION_COMPLETED]) == 1
