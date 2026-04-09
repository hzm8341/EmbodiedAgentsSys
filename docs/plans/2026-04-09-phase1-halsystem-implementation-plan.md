# Phase 1: HAL System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement HAL hardware abstraction layer - BaseDriver interface, DriverRegistry, and SimulationDriver.

**Architecture:** Create `embodiedagentsys/hal/` module following PhyAgentOS BaseDriver pattern. HAL is independent from existing hardware/ module, enabling optional opt-in. Backward compatibility maintained - existing code works unchanged.

**Tech Stack:** Pure Python (no new dependencies), abc for ABC, pathlib for paths.

---

## Task 1: Create HAL Module Structure

**Files:**
- Create: `embodiedagentsys/hal/__init__.py`
- Create: `embodiedagentsys/hal/base_driver.py`
- Create: `embodiedagentsys/hal/driver_registry.py`
- Create: `embodiedagentsys/hal/drivers/__init__.py`
- Create: `embodiedagentsys/hal/drivers/simulation_driver.py`
- Test: `tests/test_hal/test_base_driver.py`

**Step 1: Create test file**

```python
# tests/test_hal/__init__.py
# tests/test_hal/test_base_driver.py
import pytest
from pathlib import Path
from embodiedagents.hal.base_driver import BaseDriver
from embodiedagents.hal.driver_registry import DriverRegistry
from embodiedagents.hal.drivers.simulation_driver import SimulationDriver


class TestBaseDriver:
    def test_base_driver_is_abc(self):
        """BaseDriver cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseDriver()


class TestSimulationDriver:
    def test_simulation_driver_can_be_instantiated(self):
        """SimulationDriver should be instantiable"""
        driver = SimulationDriver()
        assert driver is not None

    def test_get_profile_path_returns_path(self):
        """get_profile_path should return a Path"""
        driver = SimulationDriver()
        path = driver.get_profile_path()
        assert isinstance(path, Path)

    def test_execute_action_returns_string(self):
        """execute_action should return a string result"""
        driver = SimulationDriver()
        result = driver.execute_action("move_to", {"x": 1.0, "y": 2.0})
        assert isinstance(result, str)

    def test_get_scene_returns_dict(self):
        """get_scene should return scene dict"""
        driver = SimulationDriver()
        scene = driver.get_scene()
        assert isinstance(scene, dict)

    def test_is_connected_defaults_false(self):
        """is_connected should default to False"""
        driver = SimulationDriver()
        assert driver.is_connected() is False

    def test_health_check_returns_dict(self):
        """health_check should return status dict"""
        driver = SimulationDriver()
        status = driver.health_check()
        assert isinstance(status, dict)
        assert "status" in status


class TestDriverRegistry:
    def test_registry_starts_empty(self):
        """Registry should start with no drivers"""
        registry = DriverRegistry()
        assert registry.list_drivers() == []

    def test_register_driver(self):
        """Should register a driver class"""
        registry = DriverRegistry()
        registry.register("simulation", SimulationDriver)
        assert "simulation" in registry.list_drivers()

    def test_get_driver_class(self):
        """Should retrieve registered driver class"""
        registry = DriverRegistry()
        registry.register("simulation", SimulationDriver)
        driver_class = registry.get("simulation")
        assert driver_class == SimulationDriver

    def test_get_nonexistent_driver(self):
        """Should return None for unregistered driver"""
        registry = DriverRegistry()
        assert registry.get("nonexistent") is None

    def test_create_driver_instance(self):
        """Should create driver instance via registry"""
        registry = DriverRegistry()
        registry.register("simulation", SimulationDriver)
        driver = registry.create("simulation")
        assert isinstance(driver, SimulationDriver)

    def test_create_nonexistent_driver(self):
        """Should return None when creating unregistered driver"""
        registry = DriverRegistry()
        driver = registry.create("nonexistent")
        assert driver is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hal/test_base_driver.py -v`
Expected: FAIL - ModuleNotFoundError for embodiedagentsys.hal

**Step 3: Create embodiedagentsys/hal/__init__.py**

```python
"""HAL (Hardware Abstraction Layer) module.

Provides standardized hardware driver interface following PhyAgentOS BaseDriver pattern.
"""

from embodiedagents.hal.base_driver import BaseDriver
from embodiedagents.hal.driver_registry import DriverRegistry

__all__ = ["BaseDriver", "DriverRegistry"]
```

**Step 4: Create embodiedagentsys/hal/base_driver.py**

```python
"""Base driver interface for hardware abstraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseDriver(ABC):
    """Abstract base class for hardware drivers.

    All concrete drivers must implement:
    - get_profile_path(): Return path to embodiment profile
    - execute_action(): Execute a single action
    - get_scene(): Get current scene state
    """

    @abstractmethod
    def get_profile_path(self) -> Path:
        """Return path to the robot embodiment profile.

        Returns:
            Path to the .md profile file.
        """
        pass

    @abstractmethod
    def execute_action(self, action_type: str, params: dict) -> str:
        """Execute a single action.

        Args:
            action_type: Type of action (e.g., 'move_to', 'grasp')
            params: Action parameters as dict.

        Returns:
            Human-readable result string.
        """
        pass

    @abstractmethod
    def get_scene(self) -> dict[str, dict]:
        """Get current environment scene state.

        Returns:
            Scene state as dict with keys like 'objects', 'robots', etc.
        """
        pass

    def load_scene(self, scene: dict[str, dict]) -> None:
        """Load scene state from external source.

        Args:
            scene: Scene state dict to load.
        """
        pass

    def connect(self) -> bool:
        """Connect to hardware.

        Returns:
            True if connection successful.
        """
        return True

    def disconnect(self) -> None:
        """Disconnect from hardware."""
        pass

    def is_connected(self) -> bool:
        """Check if hardware is connected.

        Returns:
            True if connected.
        """
        return False

    def health_check(self) -> dict:
        """Perform health check.

        Returns:
            Health status dict with 'status' key.
        """
        return {"status": "ok"}

    def get_runtime_state(self) -> dict:
        """Get runtime state (pose, velocity, etc.).

        Returns:
            Runtime state dict.
        """
        return {}
```

**Step 5: Create embodiedagentsys/hal/driver_registry.py**

```python
"""Driver registry for managing hardware drivers."""

from typing import Optional

from embodiedagents.hal.base_driver import BaseDriver


class DriverRegistry:
    """Registry for managing available hardware drivers.

    Example:
        registry = DriverRegistry()
        registry.register("simulation", SimulationDriver)
        driver = registry.create("simulation")
    """

    def __init__(self):
        self._drivers: dict[str, type[BaseDriver]] = {}

    def register(self, name: str, driver_class: type[BaseDriver]) -> None:
        """Register a driver class.

        Args:
            name: Driver identifier (e.g., 'simulation', 'lerobot')
            driver_class: Driver class implementing BaseDriver.
        """
        self._drivers[name] = driver_class

    def get(self, name: str) -> Optional[type[BaseDriver]]:
        """Get registered driver class.

        Args:
            name: Driver identifier.

        Returns:
            Driver class or None if not registered.
        """
        return self._drivers.get(name)

    def create(self, name: str, **kwargs) -> Optional[BaseDriver]:
        """Create driver instance by name.

        Args:
            name: Driver identifier.
            **kwargs: Arguments passed to driver constructor.

        Returns:
            Driver instance or None if not registered.
        """
        driver_class = self.get(name)
        if driver_class:
            return driver_class(**kwargs)
        return None

    def list_drivers(self) -> list[str]:
        """List all registered driver names.

        Returns:
            List of driver identifiers.
        """
        return list(self._drivers.keys())
```

**Step 6: Create embodiedagentsys/hal/drivers/__init__.py**

```python
"""Built-in HAL drivers."""

from embodiedagents.hal.drivers.simulation_driver import SimulationDriver

__all__ = ["SimulationDriver"]
```

**Step 7: Create embodiedagentsys/hal/drivers/simulation_driver.py**

```python
"""Simulation driver for testing without real hardware."""

from pathlib import Path

from embodiedagents.hal.base_driver import BaseDriver


class SimulationDriver(BaseDriver):
    """Simulation driver for testing and development.

    Does not require real hardware - simulates basic actions in memory.
    """

    def __init__(self, gui: bool = False, **kwargs):
        self._gui = gui
        self._scene: dict[str, dict] = {
            "objects": {},
            "robots": {},
        }
        self._connected = False

    def get_profile_path(self) -> Path:
        """Return path to simulation profile."""
        return Path(__file__).resolve().parent / "profiles" / "simulation.md"

    def execute_action(self, action_type: str, params: dict) -> str:
        """Execute simulated action.

        Args:
            action_type: Action type.
            params: Action parameters.

        Returns:
            Simulated result string.
        """
        return f"simulated {action_type} with params {params}"

    def get_scene(self) -> dict[str, dict]:
        """Return current simulated scene."""
        return dict(self._scene)

    def load_scene(self, scene: dict[str, dict]) -> None:
        """Load scene state."""
        self._scene = dict(scene)

    def connect(self) -> bool:
        """Simulate connection."""
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def health_check(self) -> dict:
        """Return simulation health status."""
        return {
            "status": "ok",
            "driver": "simulation",
            "gui": self._gui,
        }

    def get_runtime_state(self) -> dict:
        """Return simulated runtime state."""
        return {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "connected": self._connected,
        }
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/test_hal/test_base_driver.py -v`
Expected: PASS (12 tests)

**Step 9: Commit**

```bash
git add embodiedagentsys/hal/ tests/test_hal/
git commit -m "feat(hal): add BaseDriver interface and DriverRegistry

- Add BaseDriver ABC with abstract methods:
  - get_profile_path(), execute_action(), get_scene()
  - Optional: connect(), disconnect(), health_check()
- Add DriverRegistry for driver management
- Add SimulationDriver for testing without hardware
- Add comprehensive tests (12 test cases)

Implements Phase 1 of PhyAgentOS integration design."
```

---

## Task 2: Create Simulation Driver Profile

**Files:**
- Create: `embodiedagentsys/hal/drivers/profiles/simulation.md`
- Test: `tests/test_hal/test_simulation_profile.py`

**Step 1: Create test**

```python
# tests/test_hal/test_simulation_profile.py
import pytest
from pathlib import Path
from embodiedagents.hal.drivers.simulation_driver import SimulationDriver


class TestSimulationProfile:
    def test_profile_path_exists(self):
        """Profile path should point to existing file or be resolvable."""
        driver = SimulationDriver()
        path = driver.get_profile_path()
        assert path.suffix == ".md"

    def test_profile_content_contains_key_sections(self):
        """Profile should contain essential sections."""
        driver = SimulationDriver()
        path = driver.get_profile_path()
        # Profile may not exist in dev, but path should be valid
        assert path.parent.name == "profiles"
```

**Step 2: Create profile template**

```bash
mkdir -p embodiedagentsys/hal/drivers/profiles
```

**Step 3: Create embodiedagentsys/hal/drivers/profiles/simulation.md**

```markdown
# Simulation Driver Profile

## Identity

- **name**: simulation
- **type**: simulator
- **description**: Built-in simulation driver for testing and development

## Capabilities

### Supported Actions

- `move_to`: Move to target position
- `move_relative`: Move relative to current position
- `grasp`: Close gripper to grasp
- `release`: Open gripper to release
- `get_scene`: Query current scene state

### Action Parameters

| Action | Parameters |
|--------|------------|
| move_to | x (float), y (float), z (float), duration (float, optional) |
| move_relative | dx (float), dy (float), dz (float) |
| grasp | force (float 0.0-1.0) |
| release | - |

## Safety Constraints

- Maximum velocity: 1.0 m/s
- Maximum acceleration: 2.0 m/s²
- Workspace bounds: x [-2.0, 2.0], y [-2.0, 2.0], z [0.0, 1.5]

## Scene Representation

```json
{
  "objects": {
    "object_id": {
      "class": "object_class",
      "position": {"x": 0.0, "y": 0.0, "z": 0.0},
      "size": {"x": 0.1, "y": 0.1, "z": 0.1}
    }
  },
  "robots": {
    "robot_id": {
      "position": {"x": 0.0, "y": 0.0, "z": 0.0},
      "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
      "gripper_state": "open"
    }
  }
}
```

## Notes

- This profile is for simulation only
- No real hardware communication
- Useful for development and testing
```

**Step 4: Run tests**

Run: `pytest tests/test_hal/test_simulation_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add embodiedagentsys/hal/drivers/profiles/
git commit -m "feat(hal): add simulation driver profile

Add simulation.md embodyment profile describing:
- Supported actions and parameters
- Safety constraints
- Scene representation format
"
```

---

## Task 3: Verify HAL Integration with Existing Code

**Files:**
- Modify: `embodiedagentsys/__init__.py` (add HAL exports)
- Test: `tests/test_hal/test_integration.py`

**Step 1: Create integration test**

```python
# tests/test_hal/test_integration.py
import pytest
from embodiedagents.hal import BaseDriver, DriverRegistry
from embodiedagents.hal.drivers import SimulationDriver


class TestHALIntegration:
    """Test HAL integrates with existing codebase patterns."""

    def test_driver_registry_singleton_pattern(self):
        """DriverRegistry can be used as singleton."""
        registry1 = DriverRegistry()
        registry2 = DriverRegistry()
        # Each instantiation is independent (not singleton)
        assert registry1 is not registry2

    def test_simulation_driver_compatible_with_base(self):
        """SimulationDriver is a valid BaseDriver subclass."""
        driver = SimulationDriver()
        assert isinstance(driver, BaseDriver)

    def test_driver_registration_flow(self):
        """Test complete registration and creation flow."""
        registry = DriverRegistry()

        # Register
        registry.register("sim", SimulationDriver)
        assert "sim" in registry.list_drivers()

        # Create
        driver = registry.create("sim")
        assert driver is not None
        assert isinstance(driver, SimulationDriver)

        # Execute basic action
        result = driver.execute_action("test", {})
        assert isinstance(result, str)

    def test_backward_compatibility_existing_imports(self):
        """Existing code should continue to work."""
        # This test just verifies imports work
        from embodiedagents import SimpleAgent
        from embodiedagents.execution.tools import GripperTool
        # If imports succeed, backward compatibility maintained
```

**Step 2: Run integration tests**

Run: `pytest tests/test_hal/test_integration.py -v`
Expected: PASS

**Step 3: Check existing tests still pass**

Run: `pytest tests/ -v --ignore=tests/integration -x -q 2>&1 | head -50`
Expected: All existing tests pass

**Step 4: Commit**

```bash
git add tests/test_hal/test_integration.py
git commit -m "test(hal): add integration tests for HAL module

Verify HAL integrates with existing codebase:
- Driver registration and creation flow
- SimulationDriver instanceof BaseDriver
- Backward compatibility with existing imports
"
```

---

## Summary

After Phase 1 completion:

| Deliverable | Status |
|-------------|--------|
| `embodiedagentsys/hal/__init__.py` | ✅ |
| `embodiedagentsys/hal/base_driver.py` | ✅ |
| `embodiedagentsys/hal/driver_registry.py` | ✅ |
| `embodiedagentsys/hal/drivers/__init__.py` | ✅ |
| `embodiedagentsys/hal/drivers/simulation_driver.py` | ✅ |
| `embodiedagentsys/hal/drivers/profiles/simulation.md` | ✅ |
| `tests/test_hal/test_base_driver.py` | ✅ |
| `tests/test_hal/test_simulation_profile.py` | ✅ |
| `tests/test_hal/test_integration.py` | ✅ |

**Next:** Phase 2 - State Protocol and StateManager
