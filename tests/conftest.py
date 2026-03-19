"""
Conftest for VLA+ tests.
Ensures agents.config_vla_plus is loaded from the worktree path,
not from the editable install, to avoid triggering ros_sugar/__init__.py.
"""
import sys
import importlib.util

WORKTREE = "/media/hzm/data_disk/EmbodiedAgentsSys/.worktrees/vla-plus"

import os

# Load agents.config_vla_plus directly from worktree if not already loaded by root conftest
if "agents.config_vla_plus" not in sys.modules:
    config_path = f"{WORKTREE}/agents/config_vla_plus.py"
    if os.path.exists(config_path):
        spec = importlib.util.spec_from_file_location(
            "agents.config_vla_plus",
            config_path,
        )
        if spec:
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = "agents"
            sys.modules["agents.config_vla_plus"] = mod
            spec.loader.exec_module(mod)
