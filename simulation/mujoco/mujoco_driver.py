"""MuJoCo 仿真驱动 - 核心"""

import mujoco
import numpy as np
from typing import Optional

from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus
from simulation.mujoco.robot_model import RobotModel
from simulation.mujoco.sensors import ForceSensor, ContactSensor
from simulation.mujoco.config import (
    POSITION_LIMIT, Z_HEIGHT_LIMIT, VELOCITY_LIMIT,
    DEFAULT_TIMESTEP
)


class MuJoCoDriver:
    """MuJoCo 仿真驱动

    实现与 HAL 接口对齐的仿真驱动，支持：
    - 位置控制移动
    - 抓取/释放
    - 力觉反馈
    - 碰撞检测
    """

    def __init__(
        self,
        urdf_path: Optional[str] = None,
        timestep: float = DEFAULT_TIMESTEP,
    ):
        """
        Args:
            urdf_path: 机器人 URDF 路径（可选）
            timestep: 仿真时间步
        """
        self._timestep = timestep
        self._robot = RobotModel(urdf_path=urdf_path)
        self._force_sensor = ForceSensor()
        self._contact_sensor = ContactSensor()
        self._emergency_stopped = False
        self._grasped_object: Optional[str] = None

        # 获取模型和数据
        self._model = self._robot.get_model()
        self._data = self._robot.get_data()

        # 关联传感器
        self._force_sensor.attach_to_body("base", self._model, self._data)
        self._contact_sensor.attach(self._model, self._data)

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """执行动作，返回 ExecutionReceipt

        Args:
            action_type: 动作类型
            params: 动作参数

        Returns:
            ExecutionReceipt: 执行凭证
        """
        # 紧急停止状态检查
        if self._emergency_stopped:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.EMERGENCY_STOP,
                result_message="Driver is in emergency stop state"
            )

        # 白名单验证
        allowed = self.get_allowed_actions()
        if action_type not in allowed:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Action '{action_type}' not in whitelist"
            )

        # 执行动作
        try:
            if action_type == "move_to":
                return self._move_to(params)
            elif action_type == "move_relative":
                return self._move_relative(params)
            elif action_type == "grasp":
                return self._grasp(params)
            elif action_type == "release":
                return self._release(params)
            elif action_type == "get_scene":
                return self._get_scene_receipt(params)
            else:
                return ExecutionReceipt(
                    action_type=action_type,
                    params=params,
                    status=ExecutionStatus.FAILED,
                    result_message=f"Unknown action: {action_type}"
                )
        except Exception as e:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Execution failed: {str(e)}"
            )

    def _move_to(self, params: dict) -> ExecutionReceipt:
        """移动到目标位置"""
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        z = params.get("z", 0.0)

        # 范围检查
        if abs(x) > POSITION_LIMIT or abs(y) > POSITION_LIMIT or z > Z_HEIGHT_LIMIT:
            return ExecutionReceipt(
                action_type="move_to",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Position out of bounds: x={x}, y={y}, z={z}"
            )

        # 简单位置控制：直接设置位置
        self._data.body("base").xpos = np.array([x, y, z])
        mujoco.mj_forward(self._model, self._data)

        return ExecutionReceipt(
            action_type="move_to",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved to ({x}, {y}, {z})",
            result_data={"position": [x, y, z]}
        )

    def _move_relative(self, params: dict) -> ExecutionReceipt:
        """相对移动"""
        dx = params.get("dx", 0.0)
        dy = params.get("dy", 0.0)
        dz = params.get("dz", 0.0)

        # 速度限制
        velocity = np.sqrt(dx**2 + dy**2 + dz**2)
        if velocity > VELOCITY_LIMIT:
            return ExecutionReceipt(
                action_type="move_relative",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Velocity {velocity} exceeds limit {VELOCITY_LIMIT}"
            )

        # 获取当前位置
        current_pos = self._data.body("base").xpos.copy()
        new_pos = current_pos + np.array([dx, dy, dz])

        # 范围检查
        if abs(new_pos[0]) > POSITION_LIMIT or abs(new_pos[1]) > POSITION_LIMIT or new_pos[2] > Z_HEIGHT_LIMIT:
            return ExecutionReceipt(
                action_type="move_relative",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="Target position out of bounds"
            )

        # 应用移动
        self._data.body("base").xpos = new_pos
        mujoco.mj_forward(self._model, self._data)

        return ExecutionReceipt(
            action_type="move_relative",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved relative by ({dx}, {dy}, {dz})",
            result_data={"new_position": new_pos.tolist()}
        )

    def _grasp(self, params: dict) -> ExecutionReceipt:
        """抓取物体（简化版：无真实物理抓取）"""
        object_id = params.get("object_id", "target")
        force = params.get("force", 0.5)

        # 检查接触
        contacts = self._contact_sensor.get_contacts()
        has_contact = len(contacts) > 0

        if has_contact:
            self._grasped_object = object_id
            return ExecutionReceipt(
                action_type="grasp",
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Grasped {object_id}",
                result_data={"gripper_state": "closed", "force": force, "object": object_id}
            )
        else:
            return ExecutionReceipt(
                action_type="grasp",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="No contact detected, cannot grasp"
            )

    def _release(self, params: dict) -> ExecutionReceipt:
        """释放物体"""
        if self._grasped_object is None:
            return ExecutionReceipt(
                action_type="release",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="No object currently grasped"
            )

        released = self._grasped_object
        self._grasped_object = None

        return ExecutionReceipt(
            action_type="release",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Released {released}",
            result_data={"gripper_state": "open"}
        )

    def _get_scene_receipt(self, params: dict) -> ExecutionReceipt:
        """获取场景状态"""
        return ExecutionReceipt(
            action_type="get_scene",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Scene state retrieved",
            result_data=self.get_scene()
        )

    def get_scene(self) -> dict:
        """获取当前场景状态"""
        return {
            "robot_position": self._data.body("base").xpos.tolist() if self._data else [0, 0, 0],
            "grasped_object": self._grasped_object,
            "contacts": len(self._contact_sensor.get_contacts()),
        }

    def get_allowed_actions(self) -> list[str]:
        """返回允许的动作白名单"""
        return ["move_to", "move_relative", "grasp", "release", "get_scene"]

    def emergency_stop(self) -> ExecutionReceipt:
        """紧急停止"""
        self._emergency_stopped = True
        mujoco.mj_resetData(self._model, self._data)
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Emergency stop executed"
        )

    def reset(self) -> None:
        """重置驱动状态"""
        self._emergency_stopped = False
        mujoco.mj_resetData(self._model, self._data)

    def get_force_feedback(self) -> dict:
        """获取力觉反馈"""
        return self._force_sensor.get_force_torque()

    def get_contact_info(self) -> list:
        """获取接触信息"""
        return self._contact_sensor.get_contacts()

    def step(self) -> None:
        """执行一步仿真"""
        mujoco.mj_step(self._model, self._data)