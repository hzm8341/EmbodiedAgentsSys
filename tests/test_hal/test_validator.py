import pytest
from embodiedagentsys.hal.validators import ActionValidator, ValidationResult


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
