"""Unit tests for ExecutionFeedback data structure.

Tests cover property behavior (is_terminal, is_recoverable) and
serialization (to_dict) for execution feedback tracking.
"""

import pytest
from datetime import datetime

from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage


class TestExecutionFeedbackTerminal:
    """Tests for ExecutionFeedback.is_terminal property."""

    def test_completed_is_terminal(self) -> None:
        """Test that COMPLETED stage is terminal."""
        feedback = ExecutionFeedback(stage=FeedbackStage.COMPLETED, progress=1.0)
        assert feedback.is_terminal is True

    def test_failed_is_terminal(self) -> None:
        """Test that FAILED stage is terminal."""
        feedback = ExecutionFeedback(
            stage=FeedbackStage.FAILED,
            progress=0.5,
            has_error=True,
            error_message="Execution failed",
        )
        assert feedback.is_terminal is True

    def test_in_progress_not_terminal(self) -> None:
        """Test that IN_PROGRESS stage is not terminal."""
        feedback = ExecutionFeedback(stage=FeedbackStage.IN_PROGRESS, progress=0.5)
        assert feedback.is_terminal is False


class TestExecutionFeedbackRecoverable:
    """Tests for ExecutionFeedback.is_recoverable property."""

    def test_paused_is_recoverable(self) -> None:
        """Test that PAUSED stage is recoverable."""
        feedback = ExecutionFeedback(stage=FeedbackStage.PAUSED, progress=0.5)
        assert feedback.is_recoverable is True

    def test_failed_not_recoverable(self) -> None:
        """Test that FAILED stage is not recoverable."""
        feedback = ExecutionFeedback(stage=FeedbackStage.FAILED, progress=0.5)
        assert feedback.is_recoverable is False


class TestExecutionFeedbackToDict:
    """Tests for ExecutionFeedback.to_dict method."""

    def test_to_dict_keys(self) -> None:
        """Test that to_dict includes all required keys."""
        feedback = ExecutionFeedback(
            stage=FeedbackStage.IN_PROGRESS,
            progress=0.75,
            current_state={"position": [1.0, 2.0, 3.0]},
            message="Moving to target",
            has_error=False,
        )
        result = feedback.to_dict()

        # Verify all expected keys are present
        expected_keys = {
            "stage",
            "progress",
            "current_state",
            "message",
            "has_error",
            "error_message",
            "error_type",
            "timestamp",
        }
        assert set(result.keys()) == expected_keys

        # Verify values
        assert result["stage"] == "in_progress"
        assert result["progress"] == 0.75
        assert result["current_state"] == {"position": [1.0, 2.0, 3.0]}
        assert result["message"] == "Moving to target"
        assert result["has_error"] is False
        assert result["error_message"] == ""
        assert result["error_type"] == ""
        assert isinstance(result["timestamp"], str)
