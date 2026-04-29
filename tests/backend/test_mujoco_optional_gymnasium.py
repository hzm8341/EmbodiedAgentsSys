"""Regression tests for optional gymnasium dependency in simulation.mujoco."""

import importlib

import pytest


def test_simulation_mujoco_import_does_not_require_gymnasium() -> None:
    module = importlib.import_module("simulation.mujoco")

    assert hasattr(module, "MuJoCoDriver")
    assert hasattr(module, "GymnasiumEnvDriver")


def test_gymnasium_driver_stub_raises_clear_error_when_dependency_missing() -> None:
    module = importlib.import_module("simulation.mujoco")

    with pytest.raises(ModuleNotFoundError, match="No module named 'gymnasium'"):
        module.GymnasiumEnvDriver()
