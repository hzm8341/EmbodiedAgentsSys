"""
Root conftest.py - stubs ROS2 and deep agent dependencies before any test
collection occurs, so tests can run in a non-ROS environment.
"""
import sys
import types
import importlib
import importlib.util

WORKTREE = "/media/hzm/data_disk/EmbodiedAgentsSys/.worktrees/vla-plus"


def _stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _make_stub_package(name: str, path: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__path__ = [path]
    mod.__package__ = name
    mod.__spec__ = None
    sys.modules[name] = mod
    return mod


def _load_module_directly(module_name: str, file_path: str, package: str = None) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package or ".".join(module_name.split(".")[:-1])
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _is_ros_available() -> bool:
    try:
        import rclpy  # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False


if not _is_ros_available():
    # Stub ROS2 and all transitive dependencies
    for name in [
        "rclpy", "rclpy.logging", "rclpy.node", "rclpy.signals",
        "rclpy.exceptions", "rclpy.impl", "rclpy.impl.implementation_singleton",
        "rclpy.executors", "rclpy.callback_groups", "rclpy.parameter",
        "rclpy.qos", "rclpy.timer", "rclpy.clock", "rclpy.duration",
        "rclpy.time", "rclpy.action", "rclpy.action.client",
        "rclpy.action.server", "rclpy.subscription", "rclpy.publisher",
        "rclpy.service", "rclpy.client",
        "ros_sugar", "ros_sugar.launch", "ros_sugar.launch.launcher",
        "ros_sugar.supported_types", "ros_sugar.core", "ros_sugar.core.node",
        "msgpack_numpy", "msgpack",
        "std_msgs", "std_msgs.msg",
        "sensor_msgs", "sensor_msgs.msg",
        "geometry_msgs", "geometry_msgs.msg",
        "nav_msgs", "nav_msgs.msg",
        "builtin_interfaces", "builtin_interfaces.msg",
        "rcl_interfaces", "rcl_interfaces.msg",
        "cv_bridge",
    ]:
        if name not in sys.modules:
            _stub(name)

    sys.modules["rclpy.logging"].get_logger = lambda name: types.SimpleNamespace(
        info=lambda *a, **k: None,
        warn=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        error=lambda *a, **k: None,
        debug=lambda *a, **k: None,
    )

    # Stub agents.ros
    agents_ros = _stub("agents.ros")
    agents_ros.BaseAttrs = object
    agents_ros.BaseComponent = object
    agents_ros.ComponentRunType = object
    agents_ros.FixedInput = object
    agents_ros.SupportedType = object
    agents_ros.Topic = object
    agents_ros.BaseTopic = object
    agents_ros.Event = object
    agents_ros.Action = object
    agents_ros.base_validators = types.SimpleNamespace(
        in_=lambda *a, **k: None,
        in_range=lambda *a, **k: None,
        instance_of=lambda *a, **k: None,
        optional=lambda *a, **k: None,
        and_=lambda *a, **k: None,
        or_=lambda *a, **k: None,
    )

    # Stub agents.config and agents.utils
    agents_config = _stub("agents.config")
    agents_config.BaseComponentConfig = object
    agents_utils = _stub("agents.utils")
    agents_utils.flatten = lambda x: x

    # Stub agents.models
    agents_models = _stub("agents.models")
    for attr in ["Idefics2", "OllamaModel", "Model"]:
        setattr(agents_models, attr, object)

    # Stub agents.vectordbs
    agents_vdbs = _stub("agents.vectordbs")
    agents_vdbs.ChromaDB = object

    # Stub agents.clients and submodules
    for name in [
        "agents.clients", "agents.clients.roboml", "agents.clients.generic",
        "agents.clients.model_base", "agents.clients.ros", "agents.clients.ollama",
        "agents.config_fara",
    ]:
        m = _stub(name)
        for attr in [
            "GenericHTTPClient", "ModelClient", "RoboMLHTTPClient",
            "HTTPModelClient", "HTTPDBClient", "RESPDBClient", "RESPModelClient",
            "OllamaClient",
        ]:
            setattr(m, attr, object)

    # Stub agents.components as a package (prevents __init__.py execution)
    _make_stub_package("agents.components", f"{WORKTREE}/agents/components")

    # Directly load submodules that tests actually need (skip if not yet created)
    import os
    for submod_name, filename in [
        ("agents.components.data_structures", "data_structures.py"),
        ("agents.components.sam3_segmenter", "sam3_segmenter.py"),
        ("agents.components.qwen3l_processor", "qwen3l_processor.py"),
        ("agents.components.vla_plus", "vla_plus.py"),
    ]:
        path = f"{WORKTREE}/agents/components/{filename}"
        if not os.path.exists(path):
            continue
        mod = _load_module_directly(submod_name, path)
        if mod is not None:
            attr = filename.replace(".py", "")
            setattr(sys.modules["agents.components"], attr, mod)

    # Load agents.config_vla_plus directly for config tests
    config_path = f"{WORKTREE}/agents/config_vla_plus.py"
    if os.path.exists(config_path):
        _load_module_directly("agents.config_vla_plus", config_path, "agents")

    # Stub agents.components.voice_command
    vc = _stub("agents.components.voice_command")
    vc.VoiceCommand = object
