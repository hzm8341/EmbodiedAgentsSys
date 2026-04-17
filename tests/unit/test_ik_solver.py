"""Unit tests for simulation/mujoco/ik_solver.py"""

import numpy as np
import pytest
from pathlib import Path

from simulation.mujoco.ik_solver import IKChain


# Minimal URDF for testing - a simple 2-link planar arm
_MINIMAL_URDF = """
<mujoco model="test_arm">
    <compiler angle="radian" inertiafromgeom="true"/>
    <worldbody>
        <body name="base" pos="0 0 0">
            <joint name="base_joint" type="free"/>
            <geom type="box" size="0.05 0.05 0.1" rgba="0.5 0.5 0.8 1"/>
            <body name="link1" pos="0 0 0.1">
                <joint name="joint1" type="hinge" axis="0 0 1" pos="0 0 0"/>
                <geom type="capsule" fromto="0 0 0 0 0 0.2" rgba="0.8 0.3 0.3 1" size="0.02"/>
                <body name="link2" pos="0 0 0.2">
                    <joint name="joint2" type="hinge" axis="0 0 1" pos="0 0 0"/>
                    <geom type="capsule" fromto="0 0 0 0 0 0.2" rgba="0.3 0.8 0.3 1" size="0.02"/>
                    <body name="end_effector" pos="0 0 0.2">
                        <geom type="sphere" size="0.03" rgba="0.3 0.3 0.8 1"/>
                    </body>
                </body>
            </body>
        </body>
    </worldbody>
</mujoco>
"""

# Write a temp URDF so tests can run without external files
_TMP_URDF = Path("/tmp/test_arm_ik.urdf")


def _get_test_urdf_path():
    if not _TMP_URDF.exists():
        _TMP_URDF.write_text(_MINIMAL_URDF)
    return str(_TMP_URDF)


class TestIKChainInitialization:
    """IKChain initialization tests."""

    def test_ik_chain_initialization(self):
        """IKChain can be created with a valid URDF and end-effector link."""
        urdf_path = _get_test_urdf_path()
        ik = IKChain(urdf_path, "end_effector")
        assert ik is not None

    def test_ik_chain_raises_on_missing_urdf(self):
        """IKChain raises FileNotFoundError for a missing URDF."""
        with pytest.raises(FileNotFoundError):
            IKChain("/nonexistent/path.urdf", "end_effector")

    def test_ik_chain_raises_on_bad_link(self):
        """IKChain raises RuntimeError when end-effector link is not found."""
        urdf_path = _get_test_urdf_path()
        with pytest.raises(RuntimeError):
            IKChain(urdf_path, "nonexistent_link")


class TestJacobian:
    """Jacobian computation tests."""

    def test_jacobian_shape(self):
        """get_jacobian returns a matrix with shape[0] == 3."""
        urdf_path = _get_test_urdf_path()
        ik = IKChain(urdf_path, "end_effector")
        q = np.zeros(ik._nq)
        J = ik.get_jacobian(q)
        assert J.shape[0] == 3
        assert J.ndim == 2


class TestEndEffectorPosition:
    """End-effector position tests."""

    def test_end_effector_position_shape(self):
        """get_end_effector_position returns an array with shape == (3,)."""
        urdf_path = _get_test_urdf_path()
        ik = IKChain(urdf_path, "end_effector")
        q = np.zeros(ik._nq)
        pos = ik.get_end_effector_position(q)
        assert pos.shape == (3,)
