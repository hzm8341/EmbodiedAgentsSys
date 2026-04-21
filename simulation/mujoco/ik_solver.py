"""Numerical IK solver using pure Python URDF parsing + Jacobian pseudoinverse."""

import numpy as np
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Tuple
import os


class IKChain:
    """Inverse kinematics solver using Jacobian pseudoinverse.

    Parses URDF manually to build kinematics chain and compute
    forward kinematics and Jacobian without MuJoCo model loading.

    FK uses ALL joints in the path (fixed + revolute) so that the
    target position is expressed in the same world frame as MuJoCo.
    Only revolute joints are IK degrees of freedom.
    """

    def __init__(self, urdf_path: str, end_effector_link: str):
        """
        Args:
            urdf_path: Path to the robot URDF file.
            end_effector_link: Name of the end-effector body/link in the URDF.
        """
        if not os.path.exists(urdf_path):
            raise FileNotFoundError(f"URDF not found: {urdf_path}")

        self.urdf_path = urdf_path
        self.end_effector_link = end_effector_link

        # Parse URDF
        self.tree = ET.parse(urdf_path)
        self.root = self.tree.getroot()

        # Data structures
        self.parent_map: Dict[str, str] = {}  # joint -> parent link
        self.child_map: Dict[str, str] = {}   # joint -> child link
        self.joint_limits: Dict[str, Tuple[float, float]] = {}
        self.joint_axis: Dict[str, np.ndarray] = {}
        self.joint_origin_xyz: Dict[str, np.ndarray] = {}
        self.joint_origin_rpy: Dict[str, np.ndarray] = {}
        self.joint_types: Dict[str, str] = {}
        self.link_xyz: Dict[str, np.ndarray] = {}

        # All joints in the path root→EE (used for FK, includes fixed joints)
        self._all_path_joints: List[str] = []
        # Only revolute joints (IK degrees of freedom)
        self.joint_names: List[str] = []
        self._nq: int = 0

        self._parse_urdf()
        self._build_chain()

    def _parse_urdf(self):
        """Parse URDF and extract joint/link information."""
        for joint in self.root.findall('joint'):
            name = joint.get('name')
            jtype = joint.get('type', 'fixed')

            parent = joint.find('parent')
            child = joint.find('child')

            if parent is not None and child is not None:
                self.parent_map[name] = parent.get('link')
                self.child_map[name] = child.get('link')

            self.joint_types[name] = jtype

            # Parse origin for ALL joint types (fixed joints carry structural offsets)
            origin = joint.find('origin')
            if origin is not None:
                xyz_str = origin.get('xyz', '0 0 0')
                rpy_str = origin.get('rpy', '0 0 0')
                self.joint_origin_xyz[name] = np.array([float(x) for x in xyz_str.split()])
                self.joint_origin_rpy[name] = np.array([float(x) for x in rpy_str.split()])
            else:
                self.joint_origin_xyz[name] = np.array([0., 0., 0.])
                self.joint_origin_rpy[name] = np.array([0., 0., 0.])

            # Revolute-only properties
            if jtype == 'revolute':
                limit = joint.find('limit')
                if limit is not None:
                    self.joint_limits[name] = (
                        float(limit.get('lower', '-3.14159')),
                        float(limit.get('upper', '3.14159'))
                    )
                axis_elem = joint.find('axis')
                if axis_elem is not None:
                    axis_str = axis_elem.get('xyz', '1 0 0')
                    self.joint_axis[name] = np.array([float(x) for x in axis_str.split()])
                else:
                    self.joint_axis[name] = np.array([1., 0., 0.])

        # Extract link positions (for reference)
        for link in self.root.findall('link'):
            name = link.get('name')
            visual = link.find('visual')
            if visual is not None:
                origin = visual.find('origin')
                if origin is not None:
                    xyz_str = origin.get('xyz', '0 0 0')
                    self.link_xyz[name] = np.array([float(x) for x in xyz_str.split()])

    def _build_chain(self):
        """Build ordered joint chain from root to end effector."""
        root = self._find_root()
        if root is None:
            return

        path = self._find_path(root, self.end_effector_link)
        if path:
            # All joints for FK (fixed joints contribute structural translations)
            self._all_path_joints = path
            # Only revolute joints are IK degrees of freedom
            self.joint_names = [j for j in path if self.joint_types.get(j) == 'revolute']
            self._nq = len(self.joint_names)
        else:
            print(f"Warning: Could not find path from root to {self.end_effector_link}")

    def _find_root(self) -> Optional[str]:
        """Find root link (has no parent)."""
        child_links = set(self.child_map.values())
        for parent in self.parent_map.values():
            if parent not in child_links:
                return parent
        return list(self.parent_map.values())[0] if self.parent_map else None

    def _find_path(self, start: str, end: str) -> List[str]:
        """BFS to find joint path from start link to end link."""
        if start == end:
            return []

        visited = {start}
        queue = [(start, [])]

        while queue:
            current, path = queue.pop(0)
            for joint_name, child in self.child_map.items():
                if self.parent_map.get(joint_name) == current and child not in visited:
                    new_path = path + [joint_name]
                    if child == end:
                        return new_path
                    visited.add(child)
                    queue.append((child, new_path))
        return []

    @property
    def _model(self):
        """Dummy model object for compatibility."""
        return None

    @property
    def njnt(self) -> int:
        return len(self.joint_names)

    def _q_val_for_joint(self, joint_name: str, q: np.ndarray) -> float:
        """Return the q value for a joint; 0.0 for non-revolute joints."""
        jtype = self.joint_types.get(joint_name, 'fixed')
        if jtype == 'revolute':
            try:
                idx = self.joint_names.index(joint_name)
                return float(q[idx]) if idx < len(q) else 0.0
            except ValueError:
                return 0.0
        return 0.0

    def get_jacobian(self, q: np.ndarray) -> np.ndarray:
        """Compute 3xN geometric Jacobian for end effector."""
        n = len(self.joint_names)
        J = np.zeros((3, n))

        if n == 0:
            return J

        pos_end = self.get_end_effector_position(q)

        for i, joint_name in enumerate(self.joint_names):
            pos_joint = self._get_joint_position_world(q, joint_name)
            axis = self.joint_axis.get(joint_name, np.array([1., 0., 0.]))

            R_joint = self._get_joint_rotation_world(q, joint_name)
            axis_world = R_joint @ axis

            J[:, i] = np.cross(axis_world, pos_end - pos_joint)

        return J

    def get_end_effector_position(self, q: np.ndarray) -> np.ndarray:
        """Compute end effector world position via FK over ALL path joints."""
        if not self._all_path_joints:
            return np.array([0.0, 0.0, 0.0])

        pos = np.array([0.0, 0.0, 0.0])
        orientation = np.eye(3)

        for joint_name in self._all_path_joints:
            q_val = self._q_val_for_joint(joint_name, q)
            T = self._get_joint_transform(q_val, joint_name)
            pos = pos + orientation @ T[:3, 3]
            orientation = orientation @ T[:3, :3]

        return pos

    def _get_joint_transform(self, q: float, joint_name: str) -> np.ndarray:
        """Get 4x4 homogeneous transform for joint."""
        T = np.eye(4)

        if joint_name in self.joint_origin_xyz:
            T[:3, 3] = self.joint_origin_xyz[joint_name]

        if joint_name in self.joint_origin_rpy:
            T[:3, :3] = self._rpy_to_rot(self.joint_origin_rpy[joint_name])

        jtype = self.joint_types.get(joint_name, 'fixed')
        axis = self.joint_axis.get(joint_name, np.array([1., 0., 0.]))

        if jtype == 'revolute':
            angle = q
            axis_norm = axis / np.linalg.norm(axis)
            R = self._axis_angle_to_rot(axis_norm, angle)
            T[:3, :3] = T[:3, :3] @ R
        elif jtype == 'prismatic':
            T[:3, 3] = T[:3, 3] + axis * q
        # fixed joints: only origin offset applied (already set above)

        return T

    def _get_joint_position_world(self, q: np.ndarray, joint_name: str) -> np.ndarray:
        """Get world position of a revolute joint (position before that joint's rotation)."""
        pos = np.array([0.0, 0.0, 0.0])
        orientation = np.eye(3)

        for jname in self._all_path_joints:
            if jname == joint_name:
                return pos
            q_val = self._q_val_for_joint(jname, q)
            T = self._get_joint_transform(q_val, jname)
            pos = pos + orientation @ T[:3, 3]
            orientation = orientation @ T[:3, :3]

        return pos

    def _get_joint_rotation_world(self, q: np.ndarray, joint_name: str) -> np.ndarray:
        """Get rotation matrix of a joint in world frame."""
        R = np.eye(3)
        for jname in self._all_path_joints:
            q_val = self._q_val_for_joint(jname, q)
            T = self._get_joint_transform(q_val, jname)
            R = R @ T[:3, :3]
            if jname == joint_name:
                return R
        return R

    def _rpy_to_rot(self, rpy: np.ndarray) -> np.ndarray:
        """Roll-Pitch-Yaw to rotation matrix."""
        cr, sr = np.cos(rpy[0]), np.sin(rpy[0])
        cp, sp = np.cos(rpy[1]), np.sin(rpy[1])
        cy, sy = np.cos(rpy[2]), np.sin(rpy[2])
        return np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp, cp*sr, cp*cr]
        ])

    def _axis_angle_to_rot(self, axis: np.ndarray, angle: float) -> np.ndarray:
        """Axis-angle to rotation matrix (Rodrigues)."""
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])
        return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)

    def solve(self, target_pos: np.ndarray, q_init: Optional[np.ndarray] = None,
              max_iterations: int = 100, tolerance: float = 1e-4,
              alpha: float = 0.5) -> np.ndarray:
        """Solve IK using Jacobian pseudoinverse iteration."""
        if q_init is None:
            q = np.zeros(self._nq)
        else:
            q = q_init.copy().astype(np.float64)

        target = np.asarray(target_pos, dtype=np.float64)

        for _ in range(max_iterations):
            pos = self.get_end_effector_position(q)
            error = target - pos

            if np.linalg.norm(error) < tolerance:
                break

            J = self.get_jacobian(q)

            # Damped pseudoinverse
            lambda_sq = (1 - alpha) ** 2
            Jpseudo = J.T @ np.linalg.inv(J @ J.T + lambda_sq * np.eye(3))

            delta_q = alpha * (Jpseudo @ error)
            q = q + delta_q

            # Apply joint limits
            for i, name in enumerate(self.joint_names):
                if name in self.joint_limits:
                    lower, upper = self.joint_limits[name]
                    q[i] = np.clip(q[i], lower, upper)

        return q

    def solve_with_joint_limits(self, target_pos: np.ndarray,
                               q_init: Optional[np.ndarray] = None,
                               joint_limits: dict = None,
                               max_iterations: int = 100,
                               tolerance: float = 1e-4,
                               alpha: float = 0.5,
                               damping: float = 0.01) -> np.ndarray:
        """Solve IK with explicit joint limits using damped least squares."""
        if q_init is None:
            q = np.zeros(self._nq)
        else:
            q = q_init.copy().astype(np.float64)

        if joint_limits is None:
            joint_limits = self.joint_limits

        target = np.asarray(target_pos, dtype=np.float64)

        for _ in range(max_iterations):
            J = self.get_jacobian(q)
            pos = self.get_end_effector_position(q)
            error = target - pos

            if np.linalg.norm(error) < tolerance:
                break

            JJ_t = J @ J.T
            delta_q = J.T @ np.linalg.solve(JJ_t + damping * np.eye(3), error)

            q_new = q + alpha * delta_q

            for i, name in enumerate(self.joint_names):
                if name in joint_limits:
                    lower, upper = joint_limits[name]
                    q_new[i] = np.clip(q_new[i], lower, upper)

            q = q_new

        return q
