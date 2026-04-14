import numpy as np
from typing import Optional
from simulation.mujoco.ik_solver import IKChain


class ArmIKController:
    """双臂 IK 控制，支持左臂/右臂末端位置控制"""

    LEFT_ARM_END_EFFECTOR = "Empty_LinkLEND"
    RIGHT_ARM_END_EFFECTOR = "Empty_LinkREND"

    def __init__(self, urdf_path: str):
        self.left_chain = IKChain(urdf_path, self.LEFT_ARM_END_EFFECTOR)
        self.right_chain = IKChain(urdf_path, self.RIGHT_ARM_END_EFFECTOR)

    def solve(self, arm: str, target_pos: np.ndarray, q_init: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        if arm == "left":
            chain = self.left_chain
        elif arm == "right":
            chain = self.right_chain
        else:
            return None
        return chain.solve(target_pos, q_init)
