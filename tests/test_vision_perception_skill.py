# tests/test_vision_perception_skill.py
"""视觉感知Skill测试"""
import pytest
import numpy as np


def test_perception_skill_init():
    """验证视觉感知Skill初始化"""
    from skills.vision.perception_skill import PerceptionSkill

    skill = PerceptionSkill()
    assert skill is not None


def test_detect_objects():
    """验证物体检测"""
    from skills.vision.perception_skill import PerceptionSkill

    skill = PerceptionSkill()

    # 模拟图像
    image = np.zeros((224, 224, 3), dtype=np.uint8)

    # 检测物体
    result = skill.detect_objects(image)

    assert result is not None
    assert isinstance(result, list)


def test_get_object_position():
    """验证获取物体位置"""
    from skills.vision.perception_skill import PerceptionSkill

    skill = PerceptionSkill()

    # 模拟检测结果
    detections = [
        {"class": "cube", "position": [0.1, 0.2, 0.3], "confidence": 0.9}
    ]

    position = skill.get_object_position(detections, "cube")

    assert position is not None
    assert position[0] == pytest.approx(0.1)
    assert position[1] == pytest.approx(0.2)
    assert position[2] == pytest.approx(0.3)


def test_is_object_in_view():
    """验证物体是否在视野内"""
    from skills.vision.perception_skill import PerceptionSkill

    skill = PerceptionSkill()

    # 物体在视野内
    detections_in = [{"class": "cube", "position": [0.1, 0.2, 0.5]}]
    assert skill.is_object_in_view(detections_in, "cube") is True

    # 物体不在视野内
    detections_out = [{"class": "cube", "position": [1.0, 2.0, 5.0]}]
    assert skill.is_object_in_view(detections_out, "cube") is False
