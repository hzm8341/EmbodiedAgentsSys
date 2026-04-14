"""IK solving API endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import os

import sys
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
    target_link: Optional[str] = None
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
# Note: end_effector is the link name (child of the last joint), not the joint name
ROBOT_CONFIGS = {
    "eyoubot": {
        "urdf_path": "assets/eyoubot/eu_ca_vuer.urdf",
        "end_effectors": {
            "left": "Empty_Link21",   # child link of left_hand_joint7
            "right": "Empty_Link14",  # child link of right_hand_joint7
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
            if req.robot_id not in ROBOT_CONFIGS:
                raise HTTPException(status_code=404, detail=f"Robot not found: {req.robot_id}")
            config = ROBOT_CONFIGS[req.robot_id]
            if req.arm not in config["end_effectors"]:
                raise HTTPException(status_code=400, detail=f"Unknown arm: {req.arm}")
            target_link = config["end_effectors"][req.arm]
        else:
            target_link = req.target_link

        # Get IK chain
        ik = get_ik_chain(req.robot_id, target_link)

        # Get current position
        q_init = np.zeros(ik._nq)
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
            JointSolution(name=f"q{i}", position=float(q))
            for i, q in enumerate(q_solution)
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
