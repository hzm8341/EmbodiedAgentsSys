"""MuJoCo 仿真驱动 - 核心"""

import mujoco
import threading
import numpy as np
from typing import Callable, Optional

from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus
from simulation.mujoco.arm_ik_controller import ArmIKController
from simulation.mujoco.scene_builder import GRASPABLE_OBJECTS, build_robot_scene
from simulation.mujoco.sensors import ForceSensor, ContactSensor
from simulation.mujoco.config import (
    POSITION_LIMIT, Z_HEIGHT_LIMIT, VELOCITY_LIMIT,
    DEFAULT_TIMESTEP
)

# Distance threshold (m) within which an object is considered "in grasp"
_GRASP_REACH = 0.20


class MuJoCoDriver:
    """MuJoCo 仿真驱动"""

    _viewer = None

    # Serializes mj_forward / mj_jacBody / sync() across the animation thread
    # and the viewer-loop thread.  Both threads must hold this lock before
    # touching mjData or calling viewer.sync().
    _render_lock: threading.Lock

    def set_viewer(self, viewer) -> None:
        self._viewer = viewer

    def _animate_joints(
        self,
        joint_ids: list,
        q_start: "np.ndarray",
        q_target: "np.ndarray",
        n_frames: int = 40,
        on_frame: Optional[Callable] = None,
    ) -> None:
        """Interpolate joint positions over n_frames; viewer thread handles sync()."""
        import time as _time
        for i in range(1, n_frames + 1):
            alpha = i / n_frames
            q_interp = q_start + alpha * (q_target - q_start)
            with self._render_lock:
                for idx, jid in enumerate(joint_ids):
                    self._data.qpos[self._model.jnt_qposadr[jid]] = q_interp[idx]
                mujoco.mj_forward(self._model, self._data)
                if on_frame is not None:
                    on_frame()
            # Sleep outside the lock so the viewer thread can call sync()
            _time.sleep(1 / 60)

    def __init__(
        self,
        urdf_path: Optional[str] = None,
        model_path: Optional[str] = None,
        timestep: float = DEFAULT_TIMESTEP,
    ):
        sim_path = model_path or urdf_path
        self._render_lock = threading.Lock()
        self._force_sensor = ForceSensor()
        self._contact_sensor = ContactSensor()
        self._emergency_stopped = False
        self._grasped_object: Optional[str] = None

        # Build scene (loads URDF + adds objects/lighting/floor via MjSpec)
        if sim_path:
            self._model, self._data = build_robot_scene(sim_path)
        else:
            # Headless fallback
            from simulation.mujoco.robot_model import RobotModel
            _robot = RobotModel(urdf_path=None)
            self._model = _robot.get_model()
            self._data = _robot.get_data()

        # Attach sensors
        try:
            self._force_sensor.attach_to_body("base", self._model, self._data)
        except Exception:
            pass
        self._contact_sensor.attach(self._model, self._data)

        # End-effector body names
        self._left_ee_name = self._detect_body("Empty_LinkLEND", "la_end", "Empty_Link21", "la_sensor")
        self._right_ee_name = self._detect_body("Empty_LinkREND", "ra_end", "Empty_Link14", "ra_sensor")

        # Graspable object body IDs and their freejoint qpos addresses
        self._graspable_body_ids: dict[str, int] = {}
        self._graspable_qpos_adr: dict[str, int] = {}
        for obj_name in GRASPABLE_OBJECTS:
            bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, obj_name)
            if bid >= 0:
                self._graspable_body_ids[obj_name] = bid
                jid = mujoco.mj_name2id(
                    self._model, mujoco.mjtObj.mjOBJ_JOINT, f"{obj_name}_free"
                )
                if jid >= 0:
                    self._graspable_qpos_adr[obj_name] = int(self._model.jnt_qposadr[jid])

        # Grasped object tracking
        self._grasped_body_id: Optional[int] = None
        self._grasped_qpos_adr: Optional[int] = None
        self._grasp_offset = np.zeros(3)

        # IK controller
        ik_path = urdf_path
        self._arm_ik_controller = None
        self._left_joint_ids = []
        self._right_joint_ids = []
        if ik_path:
            try:
                self._arm_ik_controller = ArmIKController(ik_path)
                self._left_joint_ids = [
                    mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
                    for name in ["left_hand_joint1", "left_hand_joint2", "left_hand_joint3",
                                 "left_hand_joint4", "left_hand_joint5", "left_hand_joint6",
                                 "left_hand_joint7"]
                ]
                self._right_joint_ids = [
                    mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
                    for name in ["right_hand_joint1", "right_hand_joint2", "right_hand_joint3",
                                 "right_hand_joint4", "right_hand_joint5", "right_hand_joint6",
                                 "right_hand_joint7"]
                ]
            except Exception as e:
                print(f"Warning: Failed to initialize ArmIKController: {e}")

    def _detect_body(self, *candidates: str) -> str:
        for name in candidates:
            try:
                bid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, name)
                if bid >= 0:
                    return name
            except Exception:
                pass
        return candidates[-1]

    def reset_to_home(self) -> None:
        """重置到 home 姿态，恢复物体初始位置。sync() 由 viewer 线程负责。"""
        with self._render_lock:
            if self._model.nkey > 0:
                mujoco.mj_resetDataKeyframe(self._model, self._data, 0)
            else:
                mujoco.mj_resetData(self._model, self._data)
            mujoco.mj_forward(self._model, self._data)
        # Clear grasp state (no lock needed for Python attrs)
        self._grasped_body_id = None
        self._grasped_qpos_adr = None
        self._grasp_offset = np.zeros(3)

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        if self._emergency_stopped:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.EMERGENCY_STOP,
                result_message="Driver is in emergency stop state"
            )

        allowed = self.get_allowed_actions()
        if action_type not in allowed:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Action '{action_type}' not in whitelist"
            )

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
                return self.move_arm_to(
                    params.get("arm"), params.get("x", 0.0),
                    params.get("y", 0.0), params.get("z", 0.0)
                )
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
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        z = params.get("z", 0.0)

        if abs(x) > POSITION_LIMIT or abs(y) > POSITION_LIMIT or z < 0 or z > Z_HEIGHT_LIMIT:
            return ExecutionReceipt(
                action_type="move_to",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Position out of bounds: x={x}, y={y}, z={z}"
            )

        for body_name in ("base", "base_link", "world"):
            try:
                self._data.body(body_name).xpos = np.array([x, y, z])
                break
            except Exception:
                continue
        mujoco.mj_forward(self._model, self._data)

        return ExecutionReceipt(
            action_type="move_to",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved to ({x}, {y}, {z})",
            result_data={"position": [x, y, z]}
        )

    def _move_relative(self, params: dict) -> ExecutionReceipt:
        dx = params.get("dx", 0.0)
        dy = params.get("dy", 0.0)
        dz = params.get("dz", 0.0)

        velocity = np.sqrt(dx**2 + dy**2 + dz**2)
        if velocity > VELOCITY_LIMIT:
            return ExecutionReceipt(
                action_type="move_relative",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Velocity {velocity} exceeds limit {VELOCITY_LIMIT}"
            )

        current_pos = self._data.body("base").xpos.copy()
        new_pos = current_pos + np.array([dx, dy, dz])

        if abs(new_pos[0]) > POSITION_LIMIT or abs(new_pos[1]) > POSITION_LIMIT or new_pos[2] < 0 or new_pos[2] > Z_HEIGHT_LIMIT:
            return ExecutionReceipt(
                action_type="move_relative",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="Target position out of bounds"
            )

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
        """抓取物体。arm 模式下寻找最近可抓取物并记录偏移量。"""
        object_id = params.get("object_id", "target")
        force = params.get("force", 0.5)
        arm = params.get("arm")

        if arm is not None:
            ee_name = self._left_ee_name if arm == "left" else self._right_ee_name
            try:
                ee_pos = self._data.body(ee_name).xpos.copy()
            except Exception:
                ee_pos = np.zeros(3)

            # Find nearest graspable object
            nearest_bid = None
            nearest_adr = None
            nearest_dist = float("inf")
            for obj_name, bid in self._graspable_body_ids.items():
                try:
                    obj_pos = self._data.body(bid).xpos.copy()
                except Exception:
                    continue
                dist = float(np.linalg.norm(obj_pos - ee_pos))
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_bid = bid
                    nearest_adr = self._graspable_qpos_adr.get(obj_name)

            if nearest_bid is not None and nearest_dist < _GRASP_REACH:
                self._grasped_body_id = nearest_bid
                self._grasped_qpos_adr = nearest_adr
                try:
                    obj_pos = self._data.body(nearest_bid).xpos.copy()
                except Exception:
                    obj_pos = ee_pos.copy()
                self._grasp_offset = obj_pos - ee_pos
                grasp_msg = f"Grasped object (dist={nearest_dist:.3f}m, arm={arm})"
            else:
                # Gripper animation even if no object in range
                grasp_msg = f"Grasped (arm={arm}) — no object within {_GRASP_REACH}m"

            self._animate_gripper(arm, close=True)
            self._grasped_object = object_id
            return ExecutionReceipt(
                action_type="grasp",
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=grasp_msg,
                result_data={"gripper_state": "closed", "force": force}
            )

        # Legacy contact-sensor mode
        contacts = self._contact_sensor.get_contacts()
        if len(contacts) > 0:
            self._grasped_object = object_id
            return ExecutionReceipt(
                action_type="grasp",
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Grasped {object_id}",
                result_data={"gripper_state": "closed", "force": force, "object": object_id}
            )
        return ExecutionReceipt(
            action_type="grasp",
            params=params,
            status=ExecutionStatus.FAILED,
            result_message="No contact detected, cannot grasp"
        )

    def _animate_gripper(self, arm: str, close: bool = True) -> None:
        import time as _time
        candidates = (
            [f"{arm}_gripper_joint", f"{arm}_finger_joint1", f"{arm}_finger_joint2"]
            if arm in ("left", "right")
            else []
        )
        gripper_ids = []
        for name in candidates:
            try:
                jid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
                if jid >= 0:
                    gripper_ids.append(jid)
            except Exception:
                pass

        if not gripper_ids:
            return

        target = 0.0 if close else 0.04
        for jid in gripper_ids:
            adr = self._model.jnt_qposadr[jid]
            q_start = np.array([self._data.qpos[adr]])
            q_end = np.array([target])
            self._animate_joints([jid], q_start, q_end, n_frames=20)

    def _mujoco_ik_solve(
        self,
        ee_body_name: str,
        target_pos: np.ndarray,
        joint_ids: list,
        q_init: Optional[np.ndarray] = None,
        max_iter: int = 300,
        tol: float = 5e-3,
        alpha: float = 0.5,
        lam: float = 0.01,
    ) -> tuple:
        """IK using MuJoCo's mj_jacBody. Returns (q_solution, final_error).

        Operates on a temporary copy of qpos so the live simulation state
        is never corrupted during the search.
        """
        q_save = self._data.qpos.copy()
        try:
            # IK modifies qpos iteratively — hold the lock for the whole solve
            # so the viewer thread never sees an in-progress intermediate state.
            with self._render_lock:
                # Seed joint positions
                for i, jid in enumerate(joint_ids):
                    adr = self._model.jnt_qposadr[jid]
                    self._data.qpos[adr] = float(q_init[i]) if q_init is not None else 0.0

                body_id = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_BODY, ee_body_name)
                n = len(joint_ids)
                jacp = np.zeros((3, self._model.nv))
                jacr = np.zeros((3, self._model.nv))

                for _ in range(max_iter):
                    mujoco.mj_forward(self._model, self._data)
                    ee_pos = self._data.body(body_id).xpos.copy()
                    error = target_pos - ee_pos
                    if np.linalg.norm(error) < tol:
                        break

                    jacp[:] = 0.0
                    mujoco.mj_jacBody(self._model, self._data, jacp, jacr, body_id)

                    J = np.zeros((3, n))
                    for i, jid in enumerate(joint_ids):
                        J[:, i] = jacp[:, self._model.jnt_dofadr[jid]]

                    Jpseudo = J.T @ np.linalg.inv(J @ J.T + lam * np.eye(3))
                    dq = alpha * (Jpseudo @ error)

                    for i, jid in enumerate(joint_ids):
                        adr = self._model.jnt_qposadr[jid]
                        self._data.qpos[adr] += dq[i]
                        lo = float(self._model.jnt_range[jid, 0])
                        hi = float(self._model.jnt_range[jid, 1])
                        if lo < hi:
                            self._data.qpos[adr] = float(np.clip(self._data.qpos[adr], lo, hi))

                mujoco.mj_forward(self._model, self._data)
                ee_final = self._data.body(body_id).xpos.copy()
                final_error = float(np.linalg.norm(target_pos - ee_final))
                q_sol = np.array([self._data.qpos[self._model.jnt_qposadr[jid]] for jid in joint_ids])
                return q_sol, final_error

        finally:
            # Always restore qpos so the search doesn't pollute live state
            with self._render_lock:
                self._data.qpos[:] = q_save
                mujoco.mj_forward(self._model, self._data)

    def _release(self, params: dict) -> ExecutionReceipt:
        arm = params.get("arm")
        if arm is not None:
            self._animate_gripper(arm, close=False)

        # Drop held object
        self._grasped_body_id = None
        self._grasped_qpos_adr = None
        self._grasp_offset = np.zeros(3)

        released = self._grasped_object
        self._grasped_object = None

        msg = f"Released {released}" if released else "Gripper opened"
        return ExecutionReceipt(
            action_type="release",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=msg,
            result_data={"gripper_state": "open"}
        )

    def _get_scene_receipt(self, params: dict) -> ExecutionReceipt:
        return ExecutionReceipt(
            action_type="get_scene",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Scene state retrieved",
            result_data=self.get_scene()
        )

    def get_scene(self) -> dict:
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
        return ["move_to", "move_relative", "grasp", "release", "get_scene", "move_arm_to"]

    def move_arm_to(self, arm: str, x: float, y: float, z: float) -> ExecutionReceipt:
        """移动指定臂末端到目标位置（MuJoCo Jacobian IK），如有抓取物则随臂携带。"""
        params = {"arm": arm, "x": x, "y": y, "z": z}

        if arm not in ["left", "right"]:
            return ExecutionReceipt(
                action_type="move_arm_to", params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Invalid arm '{arm}'. Must be 'left' or 'right'."
            )

        joint_ids = self._left_joint_ids if arm == "left" else self._right_joint_ids
        ee_name   = self._left_ee_name   if arm == "left" else self._right_ee_name

        if not joint_ids or any(jid < 0 for jid in joint_ids):
            return ExecutionReceipt(
                action_type="move_arm_to", params=params,
                status=ExecutionStatus.FAILED,
                result_message="Arm joint IDs not found in model."
            )

        target_pos = np.array([x, y, z])
        # Read current joint positions via jnt_qposadr
        q_init = np.array([self._data.qpos[self._model.jnt_qposadr[jid]] for jid in joint_ids])

        # MuJoCo-native IK (uses mj_jacBody — works in world frame directly)
        q_solution, ik_error = self._mujoco_ik_solve(ee_name, target_pos, joint_ids, q_init)

        _IK_TOL = 0.05  # 5 cm
        if ik_error > _IK_TOL:
            return ExecutionReceipt(
                action_type="move_arm_to", params=params,
                status=ExecutionStatus.FAILED,
                result_message=(
                    f"Target position ({x:.2f}, {y:.2f}, {z:.2f}) is outside the {arm} arm's "
                    f"reachable workspace (IK residual={ik_error:.3f} m). "
                    f"Left arm home is near [0, 0.21, 0.80]; right arm near [0, -0.21, 0.80]."
                )
            )

        # Animate from current config to solution
        grasped_adr  = self._grasped_qpos_adr
        grasp_offset = self._grasp_offset.copy()

        def carry_callback():
            if grasped_adr is None:
                return
            try:
                ee_pos = self._data.body(ee_name).xpos.copy()
                self._data.qpos[grasped_adr:grasped_adr + 3] = ee_pos + grasp_offset
            except Exception:
                pass

        self._animate_joints(joint_ids, q_init, q_solution, on_frame=carry_callback)

        try:
            actual_pos = self._data.body(ee_name).xpos.tolist()
        except Exception:
            actual_pos = list(target_pos)

        return ExecutionReceipt(
            action_type="move_arm_to", params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved {arm} arm to ({x}, {y}, {z})",
            result_data={"target": [x, y, z], "actual": actual_pos,
                         "joint_angles": q_solution.tolist()}
        )

    def emergency_stop(self) -> ExecutionReceipt:
        self._emergency_stopped = True
        mujoco.mj_resetData(self._model, self._data)
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Emergency stop executed"
        )

    def reset(self) -> None:
        self._emergency_stopped = False
        self.reset_to_home()

    def get_force_feedback(self) -> dict:
        return self._force_sensor.get_force_torque()

    def get_contact_info(self) -> list:
        return self._contact_sensor.get_contacts()

    def step(self) -> None:
        mujoco.mj_step(self._model, self._data)
