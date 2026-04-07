"""WhitelistValidator implementation for policy validation layer."""

import os
from typing import Any, Dict, Optional
import yaml

from agents.policy.action_proposal import Action, ValidationResult
from agents.policy.validators.base import Validator


class WhitelistValidator(Validator):
    """Validator that checks actions against a whitelist of allowed actions.

    This is a high-priority validator (priority 1) that ensures only explicitly
    allowed actions can proceed through the validation pipeline. It also validates
    that required parameters are present and within specified ranges.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize WhitelistValidator with configuration.

        Args:
            config_path: Path to whitelist.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default to config/whitelist.yaml relative to project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            config_path = os.path.join(project_root, "config", "whitelist.yaml")

        self.config_path = config_path
        self.whitelist = self._load_whitelist()

    def _load_whitelist(self) -> Dict[str, Any]:
        """Load whitelist configuration from YAML file.

        Returns:
            Dictionary containing whitelist configuration.

        Raises:
            FileNotFoundError: If whitelist.yaml is not found.
            yaml.YAMLError: If YAML parsing fails.
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Whitelist config not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ValueError(f"Whitelist config is empty: {self.config_path}")

        return config.get("allowed_actions", {})

    def priority(self) -> int:
        """Return priority 1 (highest priority for whitelist validation).

        Returns:
            Priority level 1 (earliest execution).
        """
        return 1

    async def validate_action_type(self, action_type: str) -> ValidationResult:
        """Validate that action type is in the whitelist.

        Args:
            action_type: The action type to validate (as string).

        Returns:
            ValidationResult indicating if action type is whitelisted.
        """
        if action_type not in self.whitelist:
            return ValidationResult(
                valid=False,
                reason=f"Action '{action_type}' is not in whitelist. "
                f"Allowed actions: {', '.join(self.whitelist.keys())}",
                validator="WhitelistValidator",
            )

        return ValidationResult(
            valid=True,
            reason=f"Action '{action_type}' is whitelisted",
            validator="WhitelistValidator",
        )

    async def validate_action(self, action: Action) -> ValidationResult:
        """Validate a complete action including type and parameters.

        Args:
            action: The Action object to validate.

        Returns:
            ValidationResult with validation outcome and reason.
        """
        action_type = action.action_type.value

        # Step 1: Check if action type is whitelisted
        type_result = await self.validate_action_type(action_type)
        if not type_result.valid:
            return type_result

        # Step 2: Validate parameters
        action_spec = self.whitelist[action_type]
        required_params = action_spec.get("required_params", {})

        # Check all required parameters are present
        for param_name in required_params.keys():
            if param_name not in action.params:
                return ValidationResult(
                    valid=False,
                    reason=f"Required parameter '{param_name}' is missing for action '{action_type}'",
                    validator="WhitelistValidator",
                )

        # Step 3: Validate each parameter against constraints
        for param_name, param_value in action.params.items():
            param_result = self._check_param(
                param_name, param_value, action_spec, action_type
            )
            if not param_result.valid:
                return param_result

        return ValidationResult(
            valid=True,
            reason=f"Action '{action_type}' with parameters validated successfully",
            validator="WhitelistValidator",
        )

    def _check_param(
        self, param_name: str, param_value: Any, action_spec: Dict[str, Any], action_type: str
    ) -> ValidationResult:
        """Validate a single parameter against its constraints.

        Args:
            param_name: Name of the parameter.
            param_value: Value of the parameter.
            action_spec: Action specification from whitelist.
            action_type: The action type being validated.

        Returns:
            ValidationResult for this parameter.
        """
        # Check if parameter is defined in spec
        required_params = action_spec.get("required_params", {})
        optional_params = action_spec.get("optional_params", {})

        if param_name in required_params:
            constraints = required_params[param_name]
        elif param_name in optional_params:
            constraints = optional_params[param_name]
        else:
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' is not defined for action '{action_type}'",
                validator="WhitelistValidator",
            )

        # Validate based on type
        param_type = constraints.get("type")

        if param_type == "float":
            return self._validate_float_param(param_name, param_value, constraints)
        elif param_type == "list":
            return self._validate_list_param(param_name, param_value, constraints)
        elif param_type == "enum":
            return self._validate_enum_param(param_name, param_value, constraints)
        else:
            return ValidationResult(
                valid=False,
                reason=f"Unknown parameter type '{param_type}' for '{param_name}'",
                validator="WhitelistValidator",
            )

    def _validate_float_param(
        self, param_name: str, param_value: Any, constraints: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a float parameter against min/max constraints.

        Args:
            param_name: Parameter name.
            param_value: Parameter value.
            constraints: Constraint specification.

        Returns:
            ValidationResult.
        """
        if not isinstance(param_value, (int, float)):
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' must be a float, got {type(param_value).__name__}",
                validator="WhitelistValidator",
            )

        min_val = constraints.get("min")
        max_val = constraints.get("max")

        if min_val is not None and param_value < min_val:
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' value {param_value} is below minimum {min_val}",
                validator="WhitelistValidator",
            )

        if max_val is not None and param_value > max_val:
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' value {param_value} exceeds maximum {max_val}",
                validator="WhitelistValidator",
            )

        return ValidationResult(
            valid=True,
            reason=f"Parameter '{param_name}' is valid",
            validator="WhitelistValidator",
        )

    def _validate_list_param(
        self, param_name: str, param_value: Any, constraints: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a list parameter against length constraints.

        Args:
            param_name: Parameter name.
            param_value: Parameter value.
            constraints: Constraint specification.

        Returns:
            ValidationResult.
        """
        if not isinstance(param_value, list):
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' must be a list, got {type(param_value).__name__}",
                validator="WhitelistValidator",
            )

        expected_length = constraints.get("length")
        if expected_length is not None and len(param_value) != expected_length:
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' list length {len(param_value)} "
                f"does not match expected length {expected_length}",
                validator="WhitelistValidator",
            )

        return ValidationResult(
            valid=True,
            reason=f"Parameter '{param_name}' is valid",
            validator="WhitelistValidator",
        )

    def _validate_enum_param(
        self, param_name: str, param_value: Any, constraints: Dict[str, Any]
    ) -> ValidationResult:
        """Validate an enum parameter against allowed values.

        Args:
            param_name: Parameter name.
            param_value: Parameter value.
            constraints: Constraint specification.

        Returns:
            ValidationResult.
        """
        allowed_values = constraints.get("values", [])

        if param_value not in allowed_values:
            return ValidationResult(
                valid=False,
                reason=f"Parameter '{param_name}' value '{param_value}' is not in "
                f"allowed values: {', '.join(allowed_values)}",
                validator="WhitelistValidator",
            )

        return ValidationResult(
            valid=True,
            reason=f"Parameter '{param_name}' is valid",
            validator="WhitelistValidator",
        )
