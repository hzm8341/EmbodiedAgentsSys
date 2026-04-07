"""Domain-specific assertion helpers for robot agent tests."""
from typing import Any


def assert_skill_called(trace: Any, skill_id: str) -> None:
    """Assert that a specific skill was called during execution.

    Args:
        trace: Execution trace object with skill_calls attribute.
        skill_id: ID of the skill that should have been called.

    Raises:
        AssertionError: If the skill was not called.
    """
    assert skill_id in trace.skill_calls, (
        f"Expected skill '{skill_id}' to be called, but skill_calls was: {trace.skill_calls}"
    )


def assert_no_abort(trace: Any) -> None:
    """Assert that execution did not abort.

    Args:
        trace: Execution trace object with final_status and failure_reason.

    Raises:
        AssertionError: If execution was aborted.
    """
    assert trace.final_status != "aborted", (
        f"Expected no abort but trace was aborted: {trace.failure_reason}"
    )
    assert not trace.failure_reason or "abort" not in str(trace.failure_reason).lower(), (
        f"Unexpected abort reason: {trace.failure_reason}"
    )


def assert_error_kind(exc: Exception, kind: Any) -> None:
    """Assert that an exception is of a specific error kind.

    Args:
        exc: Exception to check.
        kind: Expected ErrorKind enum value.

    Raises:
        AssertionError: If exception is not of the expected kind.
    """
    from agents.exceptions import classify_error
    actual = classify_error(exc)
    assert actual == kind, f"Expected ErrorKind.{kind.value}, got ErrorKind.{actual.value}"
