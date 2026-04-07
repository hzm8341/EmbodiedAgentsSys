# tests/test_force_control_module.py
"""力控模块测试"""
import pytest
import numpy as np


def test_force_control_init():
    """验证力控模块初始化"""
    from skills.force_control.force_control import ForceController

    controller = ForceController()
    assert controller is not None


def test_force_controller_modes():
    """验证力控模式"""
    from skills.force_control.force_control import ForceController, ForceControlMode

    controller = ForceController()

    # 设置为位置模式
    controller.set_mode(ForceControlMode.POSITION)
    assert controller.mode == ForceControlMode.POSITION

    # 设置为力控模式
    controller.set_mode(ForceControlMode.FORCE)
    assert controller.mode == ForceControlMode.FORCE

    # 设置为混合模式
    controller.set_mode(ForceControlMode.HYBRID)
    assert controller.mode == ForceControlMode.HYBRID


def test_apply_force():
    """验证施加力"""
    from skills.force_control.force_control import ForceController

    controller = ForceController()

    # 施加力
    target_force = np.array([0.0, 0.0, -5.0])  # 5N 向下的力
    result = controller.apply_force(target_force)

    assert result is not None


def test_force_limit():
    """验证力限制"""
    from skills.force_control.force_control import ForceController

    controller = ForceController()
    controller.max_force = 10.0  # 最大10N

    # 超过限制的力
    large_force = np.array([0.0, 0.0, -15.0])
    clamped = controller.clamp_force(large_force)

    assert np.all(np.abs(clamped) <= controller.max_force)


def test_force_sensor_reading():
    """验证力传感器读数"""
    from skills.force_control.force_control import ForceController

    controller = ForceController()

    # 模拟力传感器数据
    force_data = np.array([0.1, -0.2, 1.5, 0.05, -0.03, 0.02])

    reading = controller.read_force_sensor(force_data)

    assert reading is not None
    assert len(reading) == 6  # 6轴力/力矩


def test_contact_detection():
    """验证接触检测"""
    from skills.force_control.force_control import ForceController

    controller = ForceController()
    controller.contact_threshold = 1.0  # 1N 阈值

    # 有接触
    force_with_contact = np.array([0.0, 0.0, 5.0])
    assert controller.detect_contact(force_with_contact) == True

    # 无接触
    force_no_contact = np.array([0.0, 0.0, 0.1])
    assert controller.detect_contact(force_no_contact) == False
