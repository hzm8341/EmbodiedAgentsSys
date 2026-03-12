"""
conftest.py - pytest configuration for tests that need to import
agents.components submodules without triggering the full ROS2/rclpy
dependency chain in agents/components/__init__.py.
"""
import sys
import types


def _make_stub_package(name: str, path: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__path__ = [path]
    mod.__package__ = name
    mod.__spec__ = None
    return mod


# Only inject stubs if rclpy is not available (non-ROS environment)
try:
    import rclpy  # noqa: F401
except (ImportError, ModuleNotFoundError):
    import importlib
    import importlib.util

    worktree = "/media/hzm/data_disk/EmbodiedAgentsSys/.worktrees/vla-plus"

    # Stub agents.components package so its __init__.py is not executed,
    # but submodules like data_structures can still be imported directly.
    if "agents.components" not in sys.modules:
        stub_pkg = _make_stub_package(
            "agents.components",
            f"{worktree}/agents/components",
        )
        sys.modules["agents.components"] = stub_pkg

    # Now load data_structures directly into the stub package
    spec = importlib.util.spec_from_file_location(
        "agents.components.data_structures",
        f"{worktree}/agents/components/data_structures.py",
    )
    if spec and "agents.components.data_structures" not in sys.modules:
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = "agents.components"
        sys.modules["agents.components.data_structures"] = mod
        spec.loader.exec_module(mod)
        # Also attach to stub package for attribute access
        sys.modules["agents.components"].data_structures = mod
