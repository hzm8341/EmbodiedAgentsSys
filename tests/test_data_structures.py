import numpy as np
from agents.components.data_structures import (
    SceneAnalysisResult,
    ObjectInfo,
    GraspCommand,
    GraspPoint
)

# Note: importing directly from the module (not agents.components) to avoid
# triggering agents/components/__init__.py which pulls in rclpy via agents/ros.py

def test_object_info_creation():
    """Test ObjectInfo creation and serialization"""
    mask = np.zeros((100, 100), dtype=bool)
    mask[10:20, 10:20] = True

    obj = ObjectInfo(
        name="香蕉",
        category="水果",
        bbox=[0.1, 0.2, 0.3, 0.4],
        mask=mask,
        confidence=0.95,
        attributes={"颜色": "黄色", "形状": "弯曲"}
    )

    assert obj.name == "香蕉"
    assert obj.category == "水果"
    assert obj.confidence == 0.95
    assert "颜色" in obj.attributes

    obj_dict = obj.to_dict()
    assert obj_dict["name"] == "香蕉"
    assert obj_dict["confidence"] == 0.95

def test_scene_analysis_result_creation():
    """Test SceneAnalysisResult creation"""
    obj = ObjectInfo(name="测试物体", category="测试", bbox=[0, 0, 1, 1],
                     mask=np.zeros((10, 10), dtype=bool), confidence=0.9,
                     attributes={})

    result = SceneAnalysisResult(
        detected_objects=[obj],
        segmentation_masks=[np.zeros((100, 100), dtype=bool)],
        grasp_candidates=[],
        scene_description="测试场景",
        timestamp=1234567890.0
    )

    assert len(result.detected_objects) == 1
    assert result.scene_description == "测试场景"
    assert result.timestamp == 1234567890.0

def test_grasp_point_creation():
    """Test GraspPoint creation and serialization"""
    gp = GraspPoint(
        position={"x": 0.1, "y": 0.2, "z": 0.3},
        orientation={"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        quality_score=0.85,
        approach_direction=[0.0, 0.0, -1.0],
        gripper_width=0.05,
        collision_free=True
    )

    assert gp.quality_score == 0.85
    assert gp.collision_free is True
    gp_dict = gp.to_dict()
    assert gp_dict["quality_score"] == 0.85

def test_grasp_command_creation():
    """Test GraspCommand creation and serialization"""
    cmd = GraspCommand(
        target_object="香蕉",
        grasp_point={"x": 0.1, "y": 0.2, "z": 0.3, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        approach_vector=[0.0, 0.0, -1.0],
        gripper_width=0.05,
        force_limit=10.0,
        pre_grasp_pose={"x": 0.1, "y": 0.2, "z": 0.4},
        post_grasp_pose={"x": 0.1, "y": 0.2, "z": 0.5}
    )

    assert cmd.target_object == "香蕉"
    assert cmd.force_limit == 10.0
    cmd_dict = cmd.to_dict()
    assert cmd_dict["target_object"] == "香蕉"
