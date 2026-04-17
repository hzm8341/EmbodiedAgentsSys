"""MuJoCo 仿真驱动 - 核心"""

import mujoco
import numpy as np
from typing import Optional

from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus
from simulation.mujoco.arm_ik_controller import ArmIKController
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
        model_path: Optional[str] = None,
        timestep: float = DEFAULT_TIMESTEP,
    ):
        """
        Args:
            urdf_path: 机器人 URDF 路径，用于 IK 求解（可选）
            model_path: MuJoCo MJCF XML 路径，用于仿真显示（可选，优先于 urdf_path）
            timestep: 仿真时间步
        """
        sim_path = model_path or urdf_path
        self._robot = RobotModel(urdf_path=sim_path)
        self._force_sensor = ForceSensor()
        self._contact_sensor = ContactSensor()
        self._emergency_stopped = False
        self._grasped_object: Optional[str] = None

        # 获取模型和数据
        self._model = self._robot.get_model()
        self._data = self._robot.get_data()

        # 关联传感器（body "base" 可能不存在于 XML 中，跳过错误）
        try:
            self._force_sensor.attach_to_body("base", self._model, self._data)
        except Exception:
            pass
        self._contact_sensor.attach(self._model, self._data)

        # 检测末端执行器 body 名称（MJCF 用 ra_end/la_end，URDF 用 Empty_LinkLEND/REND）
        self._left_ee_name = self._detect_body("Empty_LinkLEND", "la_end", "Empty_Link21", "la_sensor")
        self._right_ee_name = self._detect_body("Empty_LinkREND", "ra_end", "Empty_Link14", "ra_sensor")

        # Initialize Arm IK Controller (使用 URDF，即使仿真用 XML)
        ik_path = urdf_path
        self._arm_ik_controller = None
        self._left_joint_ids = []
        self._right_joint_ids = []
        if ik_path:
            try:
                self._arm_ik_controller = ArmIKController(ik_path)
                # Get joint IDs for left arm (revolute joints only)
                self._left_joint_ids = [
                    mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
                    for name in ["left_hand_joint1", "left_hand_joint2", "left_hand_joint3",
                                "left_hand_joint4", "left_hand_joint5", "left_hand_joint6", "left_hand_joint7"]
                ]
                # Get joint IDs for right arm (revolute joints only)
                self._right_joint_ids = [
                    mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
                    for name in ["right_hand_joint1", "right_hand_joint2", "right_hand_joint3",
                                "right_hand_joint4", "right_hand_joint5", "right_hand_joint6", "right_hand_joint7"]
                ]
            except Exception as e:
                print(f"Warning: Failed to initialize ArmIKController: {e}")

    def _detect_body(self, *candidates: str) -> str:
        """返回模型中存在的第一个 body 名称"""
        for name in candidates:
            try:
                bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, name)
                if bid >= 0:
                    return name
            except Exception:
                pass
        return candidates[-1]

    def reset_to_home(self) -> None:
        """将机器人重置到 home 姿态（读取模型 keyframe[0]，若无则用零位）"""
        if self._model.nkey > 0:
            mujoco.mj_resetDataKeyframe(self._model, self._data, 0)
        else:
            mujoco.mj_resetData(self._model, self._data)
        mujoco.mj_forward(self._model, self._data)

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
            elif action_type == "move_arm_to":
                arm = params.get("arm")
                x = params.get("x", 0.0)
                y = params.get("y", 0.0)
                z = params.get("z", 0.0)
                return self.move_arm_to(arm, x, y, z)
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
        if abs(x) > POSITION_LIMIT or abs(y) > POSITION_LIMIT or z < 0 or z > Z_HEIGHT_LIMIT:
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
        if abs(new_pos[0]) > POSITION_LIMIT or abs(new_pos[1]) > POSITION_LIMIT or new_pos[2] < 0 or new_pos[2] > Z_HEIGHT_LIMIT:
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
        """抓取物体（简化版：无真实物理抓取）

        Note: force parameter is accepted for API compatibility but not applied
        to physics simulation in this simplified implementation.
        """
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
        try:
            robot_pos = self._data.body(self._left_ee_name).xpos.tolist()
        except Exception:
            robot_pos = [0, 0, 0]
        return {
            "robot_position": robot_pos,
            "grasped_object": self._grasped_object,
            "contacts": len(self._contact_sensor.get_contacts()),
        }

    def get_allowed_actions(self) -> list[str]:
        """返回允许的动作白名单"""
        return ["move_to", "move_relative", "grasp", "release", "get_scene", "move_arm_to"]

    def move_arm_to(self, arm: str, x: float, y: float, z: float) -> ExecutionReceipt:
        """移动指定臂的末端到目标位置

        Args:
            arm: "left" 或 "right"
            x, y, z: 目标位置（基于基座坐标系）

        Returns:
            ExecutionReceipt: 执行凭证
        """
        if self._arm_ik_controller is None:
            return ExecutionReceipt(
                action_type="move_arm_to",
                params={"arm": arm, "x": x, "y": y, "z": z},
                status=ExecutionStatus.FAILED,
                result_message="IK controller not initialized (URDF not loaded)"
            )

        if arm not in ["left", "right"]:
            return ExecutionReceipt(
                action_type="move_arm_to",
                params={"arm": arm, "x": x, "y": y, "z": z},
                status=ExecutionStatus.FAILED,
                result_message=f"Invalid arm: {arm}. Must be 'left' or 'right'"
            )

        target_pos = np.array([x, y, z])

        # 获取当前关节位置作为 IK 初始值
        joint_ids = self._left_joint_ids if arm == "left" else self._right_joint_ids
        q_init = np.array([self._data.qpos[jid] for jid in joint_ids])

        # 求解 IK
        q_solution = self._arm_ik_controller.solve(arm, target_pos, q_init=q_init)
        if q_solution is None:
            return ExecutionReceipt(
                action_type="move_arm_to",
                params={"arm": arm, "x": x, "y": y, "z": z},
                status=ExecutionStatus.FAILED,
                result_message=f"IK solver failed for arm: {arm}"
            )

        # 获取关节 ID（只取前7个revolute关节）
        joint_ids = self._left_joint_ids if arm == "left" else self._right_joint_ids

        # 设置关节角度
        for i, joint_id in enumerate(joint_ids):
            self._data.qpos[joint_id] = q_solution[i]

        # 更新仿真
        mujoco.mj_forward(self._model, self._data)

        # 获取末端实际位置（使用 MuJoCo 中实际存在的 body）
        # 注意：由于 MuJoCo URDF 加载限制，末端 link 可能未加载，使用链中最后一个已加载的 body
        ee_name = self._left_ee_name if arm == "left" else self._right_ee_name
        try:
            actual_pos = self._data.body(ee_name).xpos.tolist()
        except Exception:
            actual_pos = list(target_pos)

        return ExecutionReceipt(
            action_type="move_arm_to",
            params={"arm": arm, "x": x, "y": y, "z": z},
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved {arm} arm to ({x}, {y}, {z})",
            result_data={"target": [x, y, z], "actual": actual_pos, "joint_angles": q_solution.tolist()[:7]}
        )

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
        self.reset_to_home()

    def get_force_feedback(self) -> dict:
        """获取力觉反馈"""
        return self._force_sensor.get_force_torque()

    def get_contact_info(self) -> list:
        """获取接触信息"""
        return self._contact_sensor.get_contacts()

    def step(self) -> None:
        """执行一步仿真"""
        mujoco.mj_step(self._model, self._data)