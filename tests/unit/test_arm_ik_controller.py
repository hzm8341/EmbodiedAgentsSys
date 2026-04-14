import numpy as np
import pytest
from simulation.mujoco.arm_ik_controller import ArmIKController


def test_arm_ik_controller_init():
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    assert controller.left_chain is not None
    assert controller.right_chain is not None


def test_solve_left_arm():
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    target = np.array([0.1, 0.1, 0.2])
    q_solution = controller.solve("left", target)
    assert q_solution is not None
    assert len(q_solution) == 13


def test_solve_right_arm():
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    target = np.array([0.1, -0.1, 0.2])
    q_solution = controller.solve("right", target)
    assert q_solution is not None
    assert len(q_solution) == 13


def test_solve_invalid_arm():
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    target = np.array([0.1, 0.1, 0.2])
    q_solution = controller.solve("invalid", target)
    assert q_solution is None
