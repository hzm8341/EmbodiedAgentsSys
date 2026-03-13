#!/usr/bin/env python3
"""VLA+ 手动集成测试脚本

运行方式:
    PYTHONPATH=/media/hzm/data_disk/EmbodiedAgentsSys python scripts/test_vla_plus_manual.py
"""
# ---- ROS2 stub (必须在所有 agents 导入之前) ----
import sys
import types
import importlib.util
import os

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _stub(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

for _name in [
    "rclpy", "rclpy.logging", "rclpy.node", "rclpy.signals", "rclpy.exceptions",
    "rclpy.impl", "rclpy.impl.implementation_singleton", "rclpy.executors",
    "rclpy.callback_groups", "rclpy.parameter", "rclpy.qos", "rclpy.timer",
    "rclpy.clock", "rclpy.duration", "rclpy.time", "rclpy.action",
    "rclpy.action.client", "rclpy.action.server", "rclpy.subscription",
    "rclpy.publisher", "rclpy.service", "rclpy.client",
    "ros_sugar", "ros_sugar.launch", "ros_sugar.launch.launcher",
    "ros_sugar.supported_types", "ros_sugar.core", "ros_sugar.core.node",
    "msgpack_numpy", "msgpack",
    "std_msgs", "std_msgs.msg", "sensor_msgs", "sensor_msgs.msg",
    "geometry_msgs", "geometry_msgs.msg", "nav_msgs", "nav_msgs.msg",
    "builtin_interfaces", "builtin_interfaces.msg",
    "rcl_interfaces", "rcl_interfaces.msg", "cv_bridge",
]:
    if _name not in sys.modules:
        _stub(_name)

sys.modules["rclpy.logging"].get_logger = lambda name: types.SimpleNamespace(
    info=lambda *a, **k: None, warn=lambda *a, **k: None,
    warning=lambda *a, **k: None, error=lambda *a, **k: None,
    debug=lambda *a, **k: None,
)

_agents_ros = _stub("agents.ros")
for _attr in ["BaseAttrs", "BaseComponent", "ComponentRunType", "FixedInput",
              "SupportedType", "Topic", "BaseTopic", "Event", "Action"]:
    setattr(_agents_ros, _attr, object)
_agents_ros.base_validators = types.SimpleNamespace(
    in_=lambda *a, **k: None, in_range=lambda *a, **k: None,
    instance_of=lambda *a, **k: None, optional=lambda *a, **k: None,
    and_=lambda *a, **k: None, or_=lambda *a, **k: None,
)

_agents_config = _stub("agents.config")
_agents_config.BaseComponentConfig = object
_stub("agents.utils").flatten = lambda x: x
for _attr in ["Idefics2", "OllamaModel", "Model"]:
    setattr(_stub("agents.models"), _attr, object)
_stub("agents.vectordbs").ChromaDB = object
for _n in ["agents.clients", "agents.clients.roboml", "agents.clients.generic",
           "agents.clients.model_base", "agents.clients.ros", "agents.clients.ollama",
           "agents.config_fara"]:
    _m = _stub(_n)
    for _a in ["GenericHTTPClient", "ModelClient", "RoboMLHTTPClient",
               "HTTPModelClient", "HTTPDBClient", "RESPDBClient", "RESPModelClient", "OllamaClient"]:
        setattr(_m, _a, object)

# Stub agents.components package, then load submodules directly
_comp_pkg = types.ModuleType("agents.components")
_comp_pkg.__path__ = [os.path.join(_WORKTREE, "agents", "components")]
_comp_pkg.__package__ = "agents.components"
_comp_pkg.__spec__ = None
sys.modules["agents.components"] = _comp_pkg

for _submod, _fname in [
    ("agents.components.data_structures", "data_structures.py"),
    ("agents.components.sam3_segmenter", "sam3_segmenter.py"),
    ("agents.components.qwen3l_processor", "qwen3l_processor.py"),
    ("agents.components.collision_checker", "collision_checker.py"),
    ("agents.components.vla_plus", "vla_plus.py"),
]:
    _path = os.path.join(_WORKTREE, "agents", "components", _fname)
    if os.path.exists(_path):
        _spec = importlib.util.spec_from_file_location(_submod, _path)
        _mod = importlib.util.module_from_spec(_spec)
        _mod.__package__ = "agents.components"
        sys.modules[_submod] = _mod
        _spec.loader.exec_module(_mod)
        setattr(_comp_pkg, _fname.replace(".py", ""), _mod)

# Load agents.config_vla_plus directly
_cfg_path = os.path.join(_WORKTREE, "agents", "config_vla_plus.py")
_cfg_spec = importlib.util.spec_from_file_location("agents.config_vla_plus", _cfg_path)
_cfg_mod = importlib.util.module_from_spec(_cfg_spec)
_cfg_mod.__package__ = "agents"
sys.modules["agents.config_vla_plus"] = _cfg_mod
_cfg_spec.loader.exec_module(_cfg_mod)
# ---- end ROS2 stub ----

import numpy as np
import asyncio


def check(name, condition, detail=""):
    status = "✅" if condition else "❌"
    print(f"{status} {name}" + (f": {detail}" if detail else ""))
    return condition


async def main():
    print("=== VLA+ 手动集成测试 ===\n")
    passed = 0
    total = 0

    # 1. 配置
    print("--- 1. 配置系统 ---")
    from agents.config_vla_plus import VLAPlusConfig, SceneUnderstandingConfig
    cfg = VLAPlusConfig()
    total += 3
    passed += check("VLAPlusConfig 默认值", cfg.confidence_threshold == 0.7)
    passed += check("VLAPlusConfig collision_check", cfg.enable_collision_check is True)
    scene_cfg = SceneUnderstandingConfig()
    passed += check("SceneUnderstandingConfig 类别", "水果" in scene_cfg.object_categories)

    # 2. 数据结构
    print("\n--- 2. 数据结构 ---")
    from agents.components.data_structures import ObjectInfo, GraspPoint
    mask = np.zeros((50, 50), dtype=bool)
    obj = ObjectInfo(name="苹果", category="水果", bbox=[0, 0, 1, 1], mask=mask, confidence=0.9, attributes={})
    total += 2
    passed += check("ObjectInfo 创建", obj.name == "苹果")
    passed += check("ObjectInfo to_dict", "name" in obj.to_dict())

    # 3. SAM3 分割
    print("\n--- 3. SAM3 分割器 ---")
    from agents.components.sam3_segmenter import SAM3Segmenter
    seg = SAM3Segmenter(model_path="test", device="cpu")
    img = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    result = await seg.segment(img)
    total += 2
    passed += check("SAM3 segment 返回结果", result is not None)
    passed += check("SAM3 image_size 正确", result.image_size == (240, 320), str(result.image_size))

    # 4. Qwen3L 处理器
    print("\n--- 4. Qwen3L 处理器 ---")
    from agents.components.qwen3l_processor import Qwen3LProcessor
    proc = Qwen3LProcessor(model_path="test", device="cpu")
    seg_dict = {"masks": [mask], "scores": [0.9], "bboxes": [[0, 0, 50, 50]]}
    understand_result = await proc.understand(img, seg_dict, "抓取苹果")
    total += 2
    passed += check("Qwen3L understand 返回字典", isinstance(understand_result, dict))
    passed += check("Qwen3L 包含 objects", "objects" in understand_result)

    # 5. 碰撞检测
    print("\n--- 5. 碰撞检测器 ---")
    from agents.components.collision_checker import CollisionChecker
    checker = CollisionChecker()
    total += 2
    passed += check("工作空间内点有效", checker._check_workspace_bounds({"x": 0.1, "y": 0.1, "z": 0.3}))
    passed += check("工作空间外点无效", not checker._check_workspace_bounds({"x": 5.0, "y": 0.0, "z": 0.3}))

    # 6. VLAPlus 完整 pipeline
    print("\n--- 6. VLAPlus 完整 Pipeline ---")
    from agents.components.vla_plus import VLAPlus, VLAPlusConfig
    vla = VLAPlus(config=VLAPlusConfig(device="cpu"))
    pipeline_result = await vla.analyze_scene(img, "抓取苹果")
    total += 4
    passed += check("Pipeline 返回 scene_description", "scene_description" in pipeline_result)
    passed += check("Pipeline 返回 objects", "objects" in pipeline_result)
    passed += check("Pipeline 返回 grasp_candidates", "grasp_candidates" in pipeline_result)
    passed += check("Pipeline grasp_candidates 有 collision_free 标记",
                    all("collision_free" in gp for gp in pipeline_result["grasp_candidates"]))

    print(f"\n{'='*40}")
    print(f"结果: {passed}/{total} 通过")
    if passed == total:
        print("✅ 全部通过！")
    else:
        print(f"❌ {total - passed} 项失败")
    print('='*40)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
