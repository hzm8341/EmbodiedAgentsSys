import pytest
import numpy as np
from simulation.mujoco.sensors import ForceSensor, ContactSensor


class TestForceSensor:
    def test_create_force_sensor(self):
        """应该能创建力传感器"""
        sensor = ForceSensor()
        assert sensor is not None

    def test_get_force_torque(self):
        """应该能获取力/力矩数据"""
        sensor = ForceSensor()
        ft = sensor.get_force_torque()
        assert isinstance(ft, dict)
        assert "force" in ft
        assert "torque" in ft
        assert len(ft["force"]) == 3
        assert len(ft["torque"]) == 3


class TestContactSensor:
    def test_create_contact_sensor(self):
        """应该能创建接触传感器"""
        sensor = ContactSensor()
        assert sensor is not None

    def test_get_contacts(self):
        """应该能获取接触点列表"""
        sensor = ContactSensor()
        contacts = sensor.get_contacts()
        assert isinstance(contacts, list)