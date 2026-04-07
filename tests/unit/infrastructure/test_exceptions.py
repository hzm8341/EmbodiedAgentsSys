import asyncio
import pytest
from agents.exceptions import (
    AgentError, AbortError, OperationCancelledError,
    VLAActionError, HardwareError, PlanningError,
    ConfigParseError, TelemetrySafeError,
    ErrorKind, is_abort_error, classify_error, short_error_stack,
)


class TestErrorHierarchy:
    def test_agent_error_is_exception(self):
        e = AgentError("base")
        assert isinstance(e, Exception)

    def test_abort_error_is_agent_error(self):
        e = AbortError("cancelled")
        assert isinstance(e, AgentError)

    def test_vla_action_error_is_agent_error(self):
        assert isinstance(VLAActionError("timeout"), AgentError)

    def test_hardware_error_is_agent_error(self):
        assert isinstance(HardwareError("arm down"), AgentError)

    def test_planning_error_is_agent_error(self):
        assert isinstance(PlanningError("no plan"), AgentError)

    def test_config_parse_error_has_file_path(self):
        e = ConfigParseError("bad yaml", file_path="/config.yaml")
        assert e.file_path == "/config.yaml"

    def test_telemetry_safe_error_is_agent_error(self):
        assert isinstance(TelemetrySafeError("safe msg"), AgentError)

    def test_operation_cancelled_is_abort(self):
        e = OperationCancelledError()
        assert isinstance(e, AbortError)


class TestIsAbortError:
    def test_true_for_abort_error(self):
        assert is_abort_error(AbortError("cancelled"))

    def test_true_for_operation_cancelled(self):
        assert is_abort_error(OperationCancelledError())

    def test_true_for_asyncio_cancelled(self):
        assert is_abort_error(asyncio.CancelledError())

    def test_false_for_value_error(self):
        assert not is_abort_error(ValueError("bad input"))

    def test_false_for_none(self):
        assert not is_abort_error(None)

    def test_false_for_string(self):
        assert not is_abort_error("not an error")


class TestClassifyError:
    def test_abort_error(self):
        assert classify_error(AbortError()) == ErrorKind.ABORT

    def test_vla_action_error(self):
        assert classify_error(VLAActionError("fail")) == ErrorKind.VLA_ACTION

    def test_hardware_error(self):
        assert classify_error(HardwareError("arm")) == ErrorKind.HARDWARE

    def test_planning_error(self):
        assert classify_error(PlanningError("no plan")) == ErrorKind.PLANNING

    def test_config_error(self):
        assert classify_error(ConfigParseError("bad", file_path="x")) == ErrorKind.CONFIG

    def test_unknown_error(self):
        assert classify_error(RuntimeError("unexpected")) == ErrorKind.UNKNOWN


class TestShortErrorStack:
    def test_non_exception_returns_str(self):
        assert short_error_stack("not an error") == "not an error"

    def test_none_returns_str(self):
        assert short_error_stack(None) == "None"

    def test_exception_returns_type_and_message(self):
        result = short_error_stack(ValueError("bad input"))
        assert "ValueError" in result
        assert "bad input" in result

    def test_truncates_to_max_frames(self):
        def deep():
            def a():
                def b():
                    def c():
                        raise RuntimeError("deep")
                    c()
                b()
            a()
        try:
            deep()
        except RuntimeError as e:
            result = short_error_stack(e, max_frames=2)
            assert "RuntimeError" in result
