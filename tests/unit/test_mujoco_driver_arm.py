"""Tests for move_arm_to functionality in MuJoCoDriver.

Note: The actual URDF (eu_ca_describtion_lbs6.urdf) has pre-existing STL mesh issues
that prevent loading. These tests use urdf_path=None to verify the implementation
logic without requiring mesh files.
"""
import numpy as np
import pytest
from simulation.mujoco import MuJoCoDriver


def test_move_arm_no_urdf():
    """测试无URDF时的错误处理"""
    driver = MuJoCoDriver(urdf_path=None)
    receipt = driver.move_arm_to("left", 0.1, 0.0, 0.2)
    assert receipt.status.value == "failed"
    assert "not initialized" in receipt.result_message.lower()


def test_move_arm_invalid_arm():
    """测试无效臂参数（无URDF场景）"""
    driver = MuJoCoDriver(urdf_path=None)
    receipt = driver.move_arm_to("invalid", 0.1, 0.0, 0.2)
    # Without URDF, returns "not initialized" (arm check comes after IK check)
    assert receipt.status.value == "failed"


def test_move_arm_in_allowed_actions():
    """测试move_arm_to在允许的动作列表中"""
    driver = MuJoCoDriver(urdf_path=None)
    allowed = driver.get_allowed_actions()
    assert "move_arm_to" in allowed


def test_move_arm_via_execute_action():
    """测试通过execute_action调用move_arm_to"""
    driver = MuJoCoDriver(urdf_path=None)
    receipt = driver.execute_action("move_arm_to", {"arm": "left", "x": 0.1, "y": 0.0, "z": 0.2})
    assert receipt.status.value == "failed"  # No URDF loaded


# Integration tests - require working URDF with arm joints
# These are skipped unless eu_ca_describtion_lbs6.urdf meshes are fixed
SKIP_INTEGRATION = True  # Set to False when URDF mesh issues are resolved


@pytest.mark.skipif(SKIP_INTEGRATION, reason="URDF mesh issues not resolved")
def test_move_arm_to_left_integration():
    """Integration test: 左臂移动（需要修复的URDF）"""
    driver = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    receipt = driver.move_arm_to("left", 0.1, 0.0, 0.2)
    assert receipt.status.value == "success"
    assert "left" in receipt.result_message.lower()


@pytest.mark.skipif(SKIP_INTEGRATION, reason="URDF mesh issues not resolved")
def test_move_arm_to_right_integration():
    """Integration test: 右臂移动（需要修复的URDF）"""
    driver = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    receipt = driver.move_arm_to("right", 0.1, 0.0, 0.2)
    assert receipt.status.value == "success"
