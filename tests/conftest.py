"""
Conftest for EmbodiedAgentsSys tests.
Sets AGENTS_DOCS_BUILD=1 to bypass sugarcoat check and pre-loads
pure-Python submodules so they are cached in sys.modules before any test runs.
"""
import os

# Must be set before any agents.* imports to bypass sugarcoat version check
os.environ["AGENTS_DOCS_BUILD"] = "1"

import sys
import importlib

# Ensure project root is in sys.path so agents.* can be found
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_CORRECT_COMPONENTS_PATH = os.path.join(_PROJECT_ROOT, "agents", "components")
_CORRECT_CLIENTS_INIT = os.path.join(_PROJECT_ROOT, "agents", "clients", "__init__.py")
_CORRECT_AGENTS_INIT = os.path.join(_PROJECT_ROOT, "agents", "__init__.py")


def _path_is_wrong(module, correct_path):
    """Return True if the module's __path__ doesn't match the expected directory."""
    current = list(getattr(module, "__path__", []))
    return current != [correct_path]


def _file_is_wrong(module, correct_init):
    """Return True if the module's __file__ is absent or points elsewhere."""
    f = getattr(module, "__file__", None)
    if not f:
        return True
    try:
        return not os.path.samefile(f, correct_init)
    except OSError:
        return True


def _purge_subtree(prefix):
    """Remove all sys.modules entries for a package tree."""
    for name in list(sys.modules.keys()):
        if name == prefix or name.startswith(prefix + "."):
            del sys.modules[name]


# Fix agents.components if loaded from a stale location (e.g. deleted worktree)
_acomp = sys.modules.get("agents.components")
if _acomp is not None and _path_is_wrong(_acomp, _CORRECT_COMPONENTS_PATH):
    _purge_subtree("agents.components")

# Fix agents.clients if broken (no __file__ or wrong location)
_acl = sys.modules.get("agents.clients")
if _acl is not None and _file_is_wrong(_acl, _CORRECT_CLIENTS_INIT):
    _purge_subtree("agents.clients")

# Fix top-level agents package if loaded from wrong location
_agents = sys.modules.get("agents")
if _agents is not None and _file_is_wrong(_agents, _CORRECT_AGENTS_INIT):
    _purge_subtree("agents")

# Clean up any broken/None placeholder entries left by earlier import attempts
for _mod_name in list(sys.modules.keys()):
    if sys.modules[_mod_name] is None and _mod_name.startswith("agents"):
        del sys.modules[_mod_name]

# Pre-load pure-Python submodules so they are always available regardless of
# collection order.  This prevents "No module named '...'" errors that arise
# when a previous test collection step leaves a parent package in a partial
# state in sys.modules.
_PRELOAD = [
    "agents.components.semantic_parser",
    "agents.components.voice_command",
    "agents.components.task_planner",
    "agents.components.semantic_map",
    "agents.components.grounded_sam",
    "agents.components.data_structures",
    "agents.components.collision_checker",
    "agents.components.qwen3l_processor",
    "agents.components.sam3_segmenter",
    "agents.components.vla_plus",
    "agents.clients.vla_adapters.base",
    "agents.clients.vla_adapters.lerobot",
    "agents.clients.vla_adapters.act",
    "agents.clients.vla_adapters.gr00t",
]

for _mod_name in _PRELOAD:
    if _mod_name not in sys.modules or sys.modules[_mod_name] is None:
        # Remove any broken parent entries first
        _parts = _mod_name.split(".")
        for _i in range(1, len(_parts) + 1):
            _parent = ".".join(_parts[:_i])
            if _parent in sys.modules and sys.modules[_parent] is None:
                del sys.modules[_parent]
        try:
            importlib.import_module(_mod_name)
        except Exception:
            pass  # Best-effort; individual tests will surface the real error
