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

# Clean up agents.config if it's the old config.py instead of the config/ package
_config = sys.modules.get("agents.config")
if _config is not None and hasattr(_config, "__path__"):
    # It's a package, keep it
    pass
elif _config is not None:
    # It's the old config.py, remove it so agents.config/ package can be used
    _purge_subtree("agents.config")

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


# ============================================================================
# TDD 测试框架：Fixtures 和 Mocks
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock
import numpy as np


# ============================================================================
# 基础类型 Fixtures
# ============================================================================

@pytest.fixture
def dummy_config():
    """虚拟代理配置"""
    class DummyConfig:
        def __init__(self):
            self.agent_name = "test_agent"
            self.max_steps = 100  # 足够多的步骤用于测试
            self.llm_model = "qwen"
            self.perception_enabled = True

    return DummyConfig()


@pytest.fixture
def dummy_observation():
    """虚拟机器人观察数据"""
    class DummyObservation:
        def __init__(self):
            self.image = None
            self.state = {"ready": True}
            self.gripper = {"position": 0.5}
            self.timestamp = 1000.0

    return DummyObservation()


@pytest.fixture
def dummy_skill_result():
    """虚拟技能执行结果"""
    class DummySkillResult:
        def __init__(self, success=True, message="success", data=None):
            self.success = success
            self.message = message
            self.data = data or {}

    return DummySkillResult()


# ============================================================================
# Provider Fixtures（提供者 mocks）
# ============================================================================

@pytest.fixture
def dummy_llm_provider():
    """虚拟 LLM 提供者"""
    mock = AsyncMock()
    mock.generate_action = AsyncMock(return_value="mock_action_code")
    mock.generate_code = AsyncMock(return_value="print('executing')")
    mock.called = False

    async def track_call(*args, **kwargs):
        mock.called = True
        return "mock_action"

    mock.generate_action = AsyncMock(side_effect=track_call)
    return mock


@pytest.fixture
def dummy_perception_provider(dummy_observation):
    """虚拟感知提供者"""
    mock = AsyncMock()
    mock.called = False

    async def track_call(*args, **kwargs):
        mock.called = True
        return dummy_observation

    mock.get_observation = AsyncMock(side_effect=track_call)
    return mock


@pytest.fixture
def dummy_executor(dummy_skill_result):
    """虚拟执行器"""
    mock = AsyncMock()
    mock.called = False

    async def track_call(*args, **kwargs):
        mock.called = True
        return dummy_skill_result

    mock.execute = AsyncMock(side_effect=track_call)
    return mock


# ============================================================================
# 配置相关 Fixtures
# ============================================================================

@pytest.fixture
def temp_config_yaml(tmp_path):
    """临时 YAML 配置文件"""
    import yaml

    config_data = {
        "agent_name": "test_agent",
        "max_steps": 100,
        "llm_model": "qwen",
        "perception_enabled": True,
    }

    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return str(config_file)


# ============================================================================
# 测试环境清理
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_env():
    """清理环境变量（每个测试后）"""
    # 保存原始环境变量
    original_env = os.environ.copy()

    yield

    # 恢复环境变量
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# 常用工具函数
# ============================================================================

def create_test_image(shape=(480, 640, 3)):
    """创建测试图像（numpy 数组）"""
    return np.random.randint(0, 255, shape, dtype=np.uint8)
