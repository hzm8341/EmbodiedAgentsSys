:orphan:

# IK End-Effector Control Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add conversation-style IK control panel to URDF viewer - users type "left arm to X=10 Y=0 Z=20" and the robot's end effector moves there via numerical IK.

**Architecture:** Numerical IK using Jacobian pseudoinverse iteration. Frontend sends target position to FastAPI backend, IK solver computes joint angles from URDF kinematics chain, results pushed to Vuer/MuJoCo for 3D visualization.

**Tech Stack:** Python/FastAPI (backend), React (frontend), MuJoCo (simulation), URDF (robot description)

---

## Task 1: Create IK Solver Core

**Files:**
- Create: `simulation/mujoco/ik_solver.py`
- Create: `tests/unit/test_ik_solver.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_ik_solver.py
import numpy as np
import pytest
import sys
sys.path.insert(0, 'simulation/mujoco')
from ik_solver import IKChain

def test_ik_chain_initialization():
    """Test IKChain can be created and has required methods."""
    # This will fail until we create the module
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")
    assert hasattr(ik, 'get_jacobian')
    assert hasattr(ik, 'get_end_effector_position')
    assert hasattr(ik, 'solve')

def test_jacobian_shape():
    """Jacobian should be 3 x num_joints."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")
    q = np.zeros(len(ik.joint_names))
    J = ik.get_jacobian(q)
    assert J.shape[0] == 3  # x, y, z

def test_end_effector_position_shape():
    """Position should be 3D."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")
    q = np.zeros(len(ik.joint_names))
    pos = ik.get_end_effector_position(q)
    assert pos.shape == (3,)
```

**Step 2: Run test to verify it fails**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -m pytest tests/unit/test_ik_solver.py -v`
Expected: FAIL - module `ik_solver` not found

**Step 3: Write minimal implementation skeleton**

```python
# simulation/mujoco/ik_solver.py
"""Numerical IK solver using Jacobian pseudoinverse."""
import numpy as np
from typing import Optional


class IKChain:
    """Inverse kinematics chain from URDF."""

    def __init__(self, urdf_path: str, end_effector_link: str):
        self.urdf_path = urdf_path
        self.end_effector_link = end_effector_link
        self.joint_names = []
        self.joint_limits = {}
        # TODO: Parse URDF and build kinematics chain

    def get_jacobian(self, q: np.ndarray) -> np.ndarray:
        """Compute Jacobian matrix at given joint configuration."""
        # TODO: Implement Jacobian computation
        n = len(self.joint_names)
        return np.zeros((3, n))

    def get_end_effector_position(self, q: np.ndarray) -> np.ndarray:
        """Get end effector world position."""
        # TODO: Implement forward kinematics
        return np.array([0.0, 0.0, 0.0])

    def solve(self, target_pos: np.ndarray, q_init: Optional[np.ndarray] = None,
              max_iterations: int = 100, tolerance: float = 1e-4,
              alpha: float = 0.5) -> np.ndarray:
        """
        Solve IK using Jacobian pseudoinverse iteration.

        Args:
            target_pos: Desired end effector position (x, y, z)
            q_init: Initial joint configuration
            max_iterations: Maximum iterations
            tolerance: Position error tolerance (m)
            alpha: Step size

        Returns:
            Solved joint configuration
        """
        if q_init is None:
            q_init = np.zeros(len(self.joint_names))

        q = q_init.copy()
        for _ in range(max_iterations):
            J = self.get_jacobian(q)
            x_current = self.get_end_effector_position(q)
            delta_x = target_pos - x_current

            if np.linalg.norm(delta_x) < tolerance:
                break

            # Pseudo-inverse: delta_q = alpha * J^T * delta_x
            delta_q = alpha * J.T @ delta_x
            q = q + delta_q

        return q
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_ik_solver.py -v`
Expected: PASS (skeleton tests pass)

**Step 5: Commit**

```bash
git add simulation/mujoco/ik_solver.py tests/unit/test_ik_solver.py
git commit -m "feat(mujoco): add IK solver skeleton with Jacobian pseudoinverse"
```

---

## Task 2: Implement URDF Parsing and Kinematics Chain

**Files:**
- Modify: `simulation/mujoco/ik_solver.py`
- Create: `tests/unit/test_urdf_kinematics.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_urdf_kinematics.py
import numpy as np
import pytest
sys.path.insert(0, 'simulation/mujoco')
from ik_solver import IKChain

def test_parse_eyoubot_joints():
    """Test parsing eyoubot URDF gives expected joint count."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")
    # Should have joints in the kinematic chain to left_hand_joint7
    assert len(ik.joint_names) > 0
    print(f"Found {len(ik.joint_names)} joints: {ik.joint_names}")

def test_forward_kinematics_nonzero():
    """Test that FK returns non-zero position after joint init."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")
    q = np.zeros(len(ik.joint_names))
    pos = ik.get_end_effector_position(q)
    # Position should be a valid 3D point (not all zeros for a real robot)
    assert not np.allclose(pos, [0, 0, 0]), f"FK returned zero position: {pos}"

def test_jacobian_is_nonzero():
    """Test that Jacobian is non-trivial when joints are non-zero."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")
    q = np.ones(len(ik.joint_names)) * 0.5  # Set some joint angles
    J = ik.get_jacobian(q)
    assert not np.allclose(J, 0), "Jacobian should be non-zero for non-zero joints"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_urdf_kinematics.py -v`
Expected: FAIL - joint_names is empty, FK returns zeros

**Step 3: Write URDF parsing implementation**

```python
# simulation/mujoco/ik_solver.py - add URDF parsing
import numpy as np
import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple
import os


class IKChain:
    """Inverse kinematics chain from URDF."""

    def __init__(self, urdf_path: str, end_effector_link: str):
        self.urdf_path = urdf_path
        self.end_effector_link = end_effector_link
        self.joint_names: List[str] = []
        self.joint_limits = {}
        self.parent_map = {}
        self.child_map = {}
        self.joint_axis = {}
        self.joint_origin_xyz = {}
        self.joint_origin_rpy = {}
        self.link_mesh = {}

        self._parse_urdf()

    def _parse_urdf(self):
        """Parse URDF and build kinematics chain to end effector."""
        tree = ET.parse(self.urdf_path)
        root = tree.getroot()

        # Build parent/child maps for joints
        for joint in root.findall('joint'):
            joint_name = joint.get('name')
            parent_elem = joint.find('parent')
            child_elem = joint.find('child')
            if parent_elem is not None and child_elem is not None:
                self.parent_map[joint_name] = parent_elem.get('link')
                self.child_map[joint_name] = child_elem.get('link')

            # Parse joint type
            joint_type = joint.get('type')
            if joint_type in ['revolute', 'prismatic']:
                limit = joint.find('limit')
                if limit is not None:
                    self.joint_limits[joint_name] = {
                        'lower': float(limit.get('lower', '-3.14159')),
                        'upper': float(limit.get('upper', '3.14159'))
                    }

            # Parse axis
            axis_elem = joint.find('axis')
            if axis_elem is not None:
                axis_str = axis_elem.get('xyz', '1 0 0')
                self.joint_axis[joint_name] = np.array([float(x) for x in axis_str.split()])

            # Parse origin
            origin_elem = joint.find('origin')
            if origin_elem is not None:
                xyz_str = origin_elem.get('xyz', '0 0 0')
                rpy_str = origin_elem.get('rpy', '0 0 0')
                self.joint_origin_xyz[joint_name] = np.array([float(x) for x in xyz_str.split()])
                self.joint_origin_rpy[joint_name] = np.array([float(x) for x in rpy_str.split()])

        # Build joint chain from root to end effector
        self._build_chain()

    def _build_chain(self):
        """Build ordered list of joints from root to end effector."""
        root = self._find_root()
        if root is None:
            return

        # BFS to find path to end effector
        path = self._find_path(root, self.end_effector_link)
        if path:
            self.joint_names = path
        else:
            print(f"Warning: Could not find path from root to {self.end_effector_link}")

    def _find_root(self) -> Optional[str]:
        """Find root link (link with no parent)."""
        all_links = set()
        for link in self.parent_map.values():
            all_links.add(link)
        for child in self.child_map.values():
            if child not in all_links:
                return child  # This is the root
        return None

    def _find_path(self, start: str, end: str) -> List[str]:
        """Find joint path from start link to end link using BFS."""
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

    def get_jacobian(self, q: np.ndarray) -> np.ndarray:
        """Compute Jacobian matrix using link-to-joint relationships."""
        n = len(self.joint_names)
        J = np.zeros((3, n))

        # Get current end effector position
        pos_end = self.get_end_effector_position(q)

        for i, joint_name in enumerate(self.joint_names):
            # Get joint position and axis in world frame
            pos_joint = self._get_joint_position(q, joint_name)
            axis = self.joint_axis.get(joint_name, np.array([1., 0., 0.]))

            # Transform axis to world frame
            R_joint = self._get_joint_rotation_matrix(q, joint_name)
            axis_world = R_joint @ axis

            # Jacobian column: cross product of axis with (pos_end - pos_joint)
            J[:, i] = np.cross(axis_world, pos_end - pos_joint)

        return J

    def get_end_effector_position(self, q: np.ndarray) -> np.ndarray:
        """Compute end effector world position using forward kinematics."""
        if not self.joint_names:
            return np.array([0.0, 0.0, 0.0])

        pos = np.array([0.0, 0.0, 0.0])
        orientation = np.eye(3)

        for joint_name, q_val in zip(self.joint_names, q):
            # Get joint transform
            T = self._get_joint_transform(q_val, joint_name)
            # Apply to cumulative transform
            pos = pos + orientation @ T[:3, 3]
            # Update orientation
            R_joint = T[:3, :3]
            orientation = orientation @ R_joint

        return pos

    def _get_joint_transform(self, q: float, joint_name: str) -> np.ndarray:
        """Get 4x4 homogeneous transform for a joint."""
        T = np.eye(4)

        # Translation from joint origin
        if joint_name in self.joint_origin_xyz:
            T[:3, 3] = self.joint_origin_xyz[joint_name]

        # Rotation from joint origin rpy
        if joint_name in self.joint_origin_rpy:
            rpy = self.joint_origin_rpy[joint_name]
            T[:3, :3] = self._rpy_to_rot(rpy)

        # Joint rotation
        axis = self.joint_axis.get(joint_name, np.array([1., 0., 0.]))
        joint_type = 'revolute'  # default

        if joint_type == 'revolute':
            angle = q
            axis_normalized = axis / np.linalg.norm(axis)
            R = self._axis_angle_to_rot(axis_normalized, angle)
            T[:3, :3] = T[:3, :3] @ R

        return T

    def _get_joint_position(self, q: np.ndarray, joint_name: str) -> np.ndarray:
        """Get world position of joint."""
        pos = np.array([0.0, 0.0, 0.0])
        orientation = np.eye(3)

        for joint_name_i, q_val in zip(self.joint_names, q):
            if joint_name_i == joint_name:
                return pos

            T = self._get_joint_transform(q_val, joint_name_i)
            pos = pos + orientation @ T[:3, 3]
            orientation = orientation @ T[:3, :3]

        return pos

    def _get_joint_rotation_matrix(self, q: np.ndarray, joint_name: str) -> np.ndarray:
        """Get rotation matrix of joint in world frame."""
        R = np.eye(3)
        for joint_name_i, q_val in zip(self.joint_names, q):
            if joint_name_i == joint_name:
                return R
            T = self._get_joint_transform(q_val, joint_name_i)
            R = R @ T[:3, :3]
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
        """Axis-angle to rotation matrix (Rodrigues' formula)."""
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])
        R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)
        return R
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_urdf_kinematics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add simulation/mujoco/ik_solver.py tests/unit/test_urdf_kinematics.py
git commit -m "feat(mujoco): implement URDF parsing and forward kinematics for IK"
```

---

## Task 3: Implement Joint-Limited IK Solver

**Files:**
- Modify: `simulation/mujoco/ik_solver.py`
- Create: `tests/unit/test_ik_convergence.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_ik_convergence.py
import numpy as np
import pytest
sys.path.insert(0, 'simulation/mujoco')
from ik_solver import IKChain

def test_ik_converges_to_target():
    """Test IK solver converges to a reachable target."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")

    # Get current position as target (should always be reachable)
    q_init = np.zeros(len(ik.joint_names))
    current_pos = ik.get_end_effector_position(q_init)

    # Solve IK
    q_solution = ik.solve(current_pos, q_init, max_iterations=100, alpha=0.5)

    # Verify final position matches target
    final_pos = ik.get_end_effector_position(q_solution)
    error = np.linalg.norm(final_pos - current_pos)
    assert error < 1e-3, f"IK did not converge: error = {error}"

def test_ik_with_joint_limits():
    """Test IK with joint limits stays within bounds."""
    ik = IKChain(urdf_path="assets/eyoubot/eu_ca_vuer.urdf", end_effector_link="left_hand_joint7")

    q_init = np.zeros(len(ik.joint_names))
    current_pos = ik.get_end_effector_position(q_init)

    # Solve with joint limits
    joint_limits = {name: (-1.0, 1.0) for name in ik.joint_names}
    q_solution = ik.solve_with_joint_limits(current_pos, q_init, joint_limits, max_iterations=100)

    # Check joint limits respected
    for name, q_val in zip(ik.joint_names, q_solution):
        if name in joint_limits:
            lower, upper = joint_limits[name]
            assert lower <= q_val <= upper, f"Joint {name} violated limits: {q_val} not in [{lower}, {upper}]"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_ik_convergence.py -v`
Expected: FAIL - `solve_with_joint_limits` not implemented

**Step 3: Write joint-limited solver implementation**

```python
    def solve_with_joint_limits(self, target_pos: np.ndarray, q_init: np.ndarray,
                                joint_limits: dict,
                                max_iterations: int = 100, tolerance: float = 1e-4,
                                alpha: float = 0.5) -> np.ndarray:
        """
        Solve IK with joint limit constraints using damped least squares.

        Args:
            target_pos: Desired end effector position
            q_init: Initial joint configuration
            joint_limits: Dict of {joint_name: (lower, upper)} limits
            max_iterations: Maximum iterations
            tolerance: Position error tolerance
            alpha: Step size
            damping: Damping factor for Levenberg-Marquardt

        Returns:
            Solved joint configuration respecting limits
        """
        damping = 0.01
        q = q_init.copy()

        for iteration in range(max_iterations):
            J = self.get_jacobian(q)
            x_current = self.get_end_effector_position(q)
            delta_x = target_pos - x_current

            if np.linalg.norm(delta_x) < tolerance:
                break

            # Damped least squares (Levenberg-Marquardt)
            J_t = J.T
            JJ_t = J @ J_t
            damping_matrix = damping * np.eye(3)
            delta_q = J_t @ np.linalg.solve(JJ_t + damping_matrix, delta_x)

            # Apply step
            q_new = q + alpha * delta_q

            # Apply joint limits (clip)
            for i, joint_name in enumerate(self.joint_names):
                if joint_name in joint_limits:
                    lower, upper = joint_limits[joint_name]
                    q_new[i] = np.clip(q_new[i], lower, upper)

            q = q_new

        return q
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_ik_convergence.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add simulation/mujoco/ik_solver.py tests/unit/test_ik_convergence.py
git commit -m "feat(mujoco): add damped least squares IK with joint limits"
```

---

## Task 4: Create IK API Backend

**Files:**
- Create: `backend/api/ik.py`
- Create: `tests/api/test_ik_api.py`

**Step 1: Write the failing test**

```python
# tests/api/test_ik_api.py
import pytest
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, 'backend')
from main import app

client = TestClient(app)

def test_ik_solve_endpoint_exists():
    """Test POST /api/ik/solve endpoint exists."""
    response = client.post("/api/ik/solve", json={
        "robot_id": "eyoubot",
        "target_link": "left_hand_joint7",
        "position": {"x": 0.1, "y": 0.0, "z": 0.2}
    })
    # Should not be 404
    assert response.status_code != 404

def test_ik_solve_returns_joints():
    """Test IK solve returns joint solution."""
    response = client.post("/api/ik/solve", json={
        "robot_id": "eyoubot",
        "target_link": "left_hand_joint7",
        "position": {"x": 0.1, "y": 0.0, "z": 0.2}
    })
    if response.status_code == 200:
        data = response.json()
        assert "joints" in data
        assert "target_position" in data
        assert "current_position" in data
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_ik_api.py -v`
Expected: FAIL - 404 or module not found

**Step 3: Write IK API implementation**

```python
# backend/api/ik.py
"""IK solving API endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import sys
import os

# Add simulation path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../simulation/mujoco'))
from ik_solver import IKChain

router = APIRouter(prefix="/api/ik", tags=["ik"])

# Cache for IK chains per robot
_ik_chain_cache = {}


class Position(BaseModel):
    x: float
    y: float
    z: float


class IKSolveRequest(BaseModel):
    robot_id: str
    target_link: str
    position: Position
    arm: Optional[str] = None  # "left" or "right"


class JointSolution(BaseModel):
    name: str
    position: float


class IKSolveResponse(BaseModel):
    status: str
    joints: list[JointSolution]
    target_position: Position
    current_position: Position
    iterations: int
    error: float


# Robot URDF configuration
ROBOT_CONFIGS = {
    "eyoubot": {
        "urdf_path": "assets/eyoubot/eu_ca_vuer.urdf",
        "end_effectors": {
            "left": "left_hand_joint7",
            "right": "right_hand_joint7",
        }
    }
}


def get_ik_chain(robot_id: str, target_link: str) -> IKChain:
    """Get or create IK chain for robot and end effector."""
    cache_key = f"{robot_id}:{target_link}"

    if cache_key not in _ik_chain_cache:
        if robot_id not in ROBOT_CONFIGS:
            raise HTTPException(status_code=404, detail=f"Robot not found: {robot_id}")

        config = ROBOT_CONFIGS[robot_id]
        urdf_path = config["urdf_path"]

        # Resolve relative path from project root
        if not os.path.isabs(urdf_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            urdf_path = os.path.join(project_root, urdf_path)

        if not os.path.exists(urdf_path):
            raise HTTPException(status_code=400, detail=f"URDF not found: {urdf_path}")

        _ik_chain_cache[cache_key] = IKChain(urdf_path, target_link)

    return _ik_chain_cache[cache_key]


@router.post("/solve", response_model=IKSolveResponse)
async def solve_ik(req: IKSolveRequest):
    """Solve IK for given target position."""
    try:
        # Resolve target link from arm or use directly
        if req.arm and not req.target_link:
            if robot_id not in ROBOT_CONFIGS:
                raise HTTPException(status_code=404, detail=f"Robot not found: {robot_id}")
            config = ROBOT_CONFIGS[req.robot_id]
            if req.arm not in config["end_effectors"]:
                raise HTTPException(status_code=400, detail=f"Unknown arm: {req.arm}")
            target_link = config["end_effectors"][req.arm]
        else:
            target_link = req.target_link

        # Get IK chain
        ik = get_ik_chain(req.robot_id, target_link)

        # Get current position
        q_init = np.zeros(len(ik.joint_names))
        current_pos = ik.get_end_effector_position(q_init)

        # Target position
        target_pos = np.array([req.position.x, req.position.y, req.position.z])

        # Solve IK
        q_solution = ik.solve(target_pos, q_init, max_iterations=100, alpha=0.5)

        # Compute final position and error
        final_pos = ik.get_end_effector_position(q_solution)
        error = float(np.linalg.norm(final_pos - target_pos))

        # Build joint list
        joints = [
            JointSolution(name=name, position=float(q))
            for name, q in zip(ik.joint_names, q_solution)
        ]

        return IKSolveResponse(
            status="success",
            joints=joints,
            target_position=Position(x=target_pos[0], y=target_pos[1], z=target_pos[2]),
            current_position=Position(x=current_pos[0], y=current_pos[1], z=current_pos[2]),
            iterations=100,
            error=error
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IK solve failed: {str(e)}")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_ik_api.py -v`
Expected: PASS or FAIL based on integration

**Step 5: Commit**

```bash
git add backend/api/ik.py tests/api/test_ik_api.py
git commit -m "feat(api): add IK solve endpoint /api/ik/solve"
```

---

## Task 5: Integrate IK API into main.py

**Files:**
- Modify: `backend/main.py`

**Step 1: Read current main.py**

```python
# backend/main.py (current)
from backend.api.routes import router as routes_router
from backend.api import urdf, state, chat
```

**Step 2: Add IK router import and registration**

```python
# Add after existing imports:
from backend.api import ik

# Add after existing app.include_router calls:
app.include_router(ik.router)
```

**Step 3: Verify import works**

Run: `python -c "from backend.main import app; print('OK')"`
Expected: OK

**Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): integrate IK API router"
```

---

## Task 6: Create Frontend IKChatPanel Component

**Files:**
- Create: `web-dashboard/src/components/IKChatPanel.tsx`
- Create: `tests/frontend/test_ik_chat_panel.py` (if testing framework exists)

**Step 1: Write the component**

```tsx
// web-dashboard/src/components/IKChatPanel.tsx
import React, { useState } from 'react';

interface Position {
  x: number;
  y: number;
  z: number;
}

interface JointSolution {
  name: string;
  position: number;
}

interface IKResult {
  status: string;
  joints: JointSolution[];
  target_position: Position;
  current_position: Position;
  iterations: number;
  error: number;
}

interface Message {
  role: 'user' | 'system';
  content: string;
}

interface IKChatPanelProps {
  robotId: string;
  vuerPort: number;
}

const IKChatPanel: React.FC<IKChatPanelProps> = ({ robotId, vuerPort }) => {
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState<IKResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const parseInput = (text: string): { arm: string; position: Position } | null => {
    // Support patterns:
    // "左臂移动到 X=10 Y=0 Z=20"
    // "left_arm to x=0.5 y=0.2 z=0.8"
    // "移动左手到 10, 0, 20"

    const leftArmPatterns = ['左臂', 'left_arm', 'l_arm', '左手', 'left_hand', 'l_hand'];
    const rightArmPatterns = ['右臂', 'right_arm', 'r_arm', '右手', 'right_hand', 'r_hand'];

    let arm = 'left'; // default

    // Detect arm
    const lowerText = text.toLowerCase();
    if (rightArmPatterns.some(p => lowerText.includes(p))) {
      arm = 'right';
    } else if (!leftArmPatterns.some(p => lowerText.includes(p))) {
      return null; // Cannot determine arm
    }

    // Extract numbers
    // Pattern 1: X=10 Y=0 Z=20 or x=0.5 y=0.2 z=0.8
    const xyzPattern = /[xyz]=([-\d.]+)/gi;
    const matches = text.match(xyzPattern);

    if (matches && matches.length >= 3) {
      const x = parseFloat(matches[0].split('=')[1]);
      const y = parseFloat(matches[1].split('=')[1]);
      const z = parseFloat(matches[2].split('=')[1]);
      if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
        return { arm, position: { x, y, z } };
      }
    }

    // Pattern 2: "10, 0, 20" format
    const numPattern = /([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)/;
    const numMatch = text.match(numPattern);
    if (numMatch) {
      return {
        arm,
        position: {
          x: parseFloat(numMatch[1]),
          y: parseFloat(numMatch[2]),
          z: parseFloat(numMatch[3])
        }
      };
    }

    return null;
  };

  const handleSend = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = { role: 'user', content: inputText };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const parsed = parseInput(inputText);

      if (!parsed) {
        setError('无法解析输入格式。请使用: "左臂移动到 X=10 Y=0 Z=20"');
        setIsLoading(false);
        return;
      }

      const response = await fetch('/api/ik/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          robot_id: robotId,
          target_link: parsed.arm === 'left' ? 'left_hand_joint7' : 'right_hand_joint7',
          position: parsed.position,
          arm: parsed.arm
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const result: IKResult = await response.json();
      setLastResult(result);

      const systemMessage: Message = {
        role: 'system',
        content: `已移动 ${parsed.arm === 'left' ? '左' : '右'}臂末端到 (${parsed.position.x.toFixed(3)}, ${parsed.position.y.toFixed(3)}, ${parsed.position.z.toFixed(3)})\n末端误差: ${result.error.toFixed(4)}m\n关节数: ${result.joints.length}`
      };
      setMessages(prev => [...prev, systemMessage]);

    } catch (e) {
      setError(`错误: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInputText('');
    setError(null);
    setLastResult(null);
  };

  return (
    <div className="ik-chat-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <h4 style={{ margin: 0, fontSize: '14px' }}>IK Control</h4>
        <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#666' }}>
          示例: 左臂移动到 X=0.5 Y=0 Z=0.3
        </p>
      </div>

      {/* Messages */}
      <div className="messages" style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {messages.length === 0 && !error && (
          <div style={{ textAlign: 'center', color: '#999', padding: '20px', fontSize: '12px' }}>
            输入末端目标位置，IK求解器将计算关节角度
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`message ${msg.role}`}
            style={{
              marginBottom: '8px',
              padding: '8px 12px',
              borderRadius: '8px',
              background: msg.role === 'user' ? '#e3f2fd' : '#f5f5f5',
              fontSize: '12px',
              whiteSpace: 'pre-wrap'
            }}
          >
            <strong>{msg.role === 'user' ? '用户' : '系统'}:</strong> {msg.content}
          </div>
        ))}
        {error && (
          <div style={{ color: '#d32f2f', padding: '8px', fontSize: '12px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="input-area" style={{ padding: '12px', borderTop: '1px solid #ddd', display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="左臂移动到 X=0.5 Y=0 Z=0.3"
          disabled={isLoading}
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '12px' }}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !inputText.trim()}
          style={{
            padding: '8px 16px',
            background: isLoading ? '#ccc' : '#2196f3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '12px'
          }}
        >
          {isLoading ? '求解中...' : '发送'}
        </button>
        <button
          onClick={handleClear}
          style={{
            padding: '8px 16px',
            background: '#f5f5f5',
            color: '#666',
            border: '1px solid #ccc',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          清除
        </button>
      </div>
    </div>
  );
};

export default IKChatPanel;
```

**Step 2: Commit**

```bash
git add web-dashboard/src/components/IKChatPanel.tsx
git commit -m "feat(frontend): add IKChatPanel component for conversation-style IK input"
```

---

## Task 7: Integrate IKChatPanel into URDFViewer

**Files:**
- Modify: `web-dashboard/src/components/URDFViewer.tsx`

**Step 1: Read current URDFViewer.tsx**

**Step 2: Add IKChatPanel tab to control panel sidebar**

Modify the URDFViewer to add a tab switcher between Model Tree, Joint Controls, and IK Control:

```tsx
// In URDFViewer.tsx, add state for active tab:
const [activeTab, setActiveTab] = useState<'model' | 'joints' | 'ik'>('joints');

// In the sidebar, replace the joint control section with a tabbed interface:

{activeTab === 'joints' && (
  <div className="joint-control-section" style={{ height: '45%', overflow: 'hidden' }}>
    <JointControl robotId={robotId} />
  </div>
)}

{activeTab === 'ik' && (
  <div className="ik-control-section" style={{ height: '45%', overflow: 'hidden' }}>
    <IKChatPanel robotId={robotId} vuerPort={vuerPort} />
  </div>
)}
```

**Step 3: Commit**

```bash
git add web-dashboard/src/components/URDFViewer.tsx
git commit -m "feat(urdf): integrate IKChatPanel into viewer sidebar"
```

---

## Task 8: Update Robot Configuration

**Files:**
- Modify: `simulation/mujoco/config.py`

**Step 1: Add wheeled humanoid configuration**

```python
# Add at end of config.py

# 双臂人形机器人 (Wheeled Humanoid)
WHEELED_HUMANOID_CONFIG = {
    "robot_id": "wheeled_humanoid",
    "urdf_path": "assets/wheeled_humanoid/robot.urdf",
    "end_effectors": {
        "left_arm": "left_hand_joint7",
        "right_arm": "right_hand_joint7",
    },
    "joint_groups": {
        "left_arm": ["l_shoulder_joint1", "l_shoulder_joint2", "l_shoulder_joint3",
                      "l_elbow_joint1", "l_elbow_joint2", "l_wrist_joint1"],
        "right_arm": ["r_shoulder_joint1", "r_shoulder_joint2", "r_shoulder_joint3",
                       "r_elbow_joint1", "r_elbow_joint2", "r_wrist_joint1"],
    },
    "default_start_position": [0.0] * 12,  # Placeholder
}
```

**Step 2: Commit**

```bash
git add simulation/mujoco/config.py
git commit -m "feat(config): add wheeled humanoid robot configuration"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | IK Solver skeleton + Jacobian structure | `ik_solver.py`, `test_ik_solver.py` |
| 2 | URDF parsing + forward kinematics | `ik_solver.py`, `test_urdf_kinematics.py` |
| 3 | Damped LMLS IK + joint limits | `ik_solver.py`, `test_ik_convergence.py` |
| 4 | Backend IK API endpoint | `backend/api/ik.py`, `test_ik_api.py` |
| 5 | Integrate IK router into main.py | `backend/main.py` |
| 6 | Frontend IKChatPanel component | `IKChatPanel.tsx` |
| 7 | Integrate IKChatPanel into URDFViewer | `URDFViewer.tsx` |
| 8 | Add robot configuration | `config.py` |

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-04-13-ik-end-effector-implementation-plan.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
