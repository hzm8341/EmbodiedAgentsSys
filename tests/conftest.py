"""
Conftest for VLA+ tests.
Pre-imports agents.config_vla_plus and pins it in sys.modules to prevent
pytest's module cleanup from causing double-import issues with the editable install.
"""
import sys
import os

os.environ.setdefault("AGENTS_DOCS_BUILD", "1")

# Pre-import and pin config module to prevent double-import from editable install + PYTHONPATH
import agents.config_vla_plus as _cfg_mod  # noqa: E402
sys.modules["agents.config_vla_plus"] = _cfg_mod
