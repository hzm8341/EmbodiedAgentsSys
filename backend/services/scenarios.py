"""Predefined test scenarios for the interactive agent debugger.

Each scenario bundles an initial observation and a task description so that the
frontend can launch pre-canned demos with a single click.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from agents.core.types import RobotObservation


@dataclass(frozen=True)
class Scenario:
    """A single test scenario for agent debugging."""
    name: str
    description: str
    task: str
    initial_state: Dict[str, float]
    initial_gripper: Dict[str, float]
    action_sequence: List[dict] = field(default_factory=list)

    def build_observation(self) -> RobotObservation:
        """Materialize a RobotObservation from this scenario's initial data."""
        return RobotObservation(
            state=dict(self.initial_state),
            gripper=dict(self.initial_gripper),
        )

    def to_dict(self) -> dict:
        """JSON-serializable view for the frontend catalog."""
        return {
            "name": self.name,
            "description": self.description,
            "task": self.task,
        }


SCENARIOS: Dict[str, Scenario] = {
    "spatial_detection": Scenario(
        name="spatial_detection",
        description="Robot scans the workspace to identify all three objects",
        task="Scan the workspace and identify all objects",
        initial_state={"gripper_open": 1.0},
        initial_gripper={"position": 0.04, "force": 0.0},
        action_sequence=[
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.85}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": -0.12, "z": 0.85}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.52, "y": 0.0,  "z": 0.85}},
        ],
    ),
    "single_grasp": Scenario(
        name="single_grasp",
        description="Pick up the red cube on the table (z≈0.72)",
        task="Pick up the red cube",
        initial_state={"gripper_open": 1.0, "target_x": 0.45, "target_y": 0.12, "target_z": 0.72},
        initial_gripper={"position": 0.04, "force": 0.0},
        action_sequence=[
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.85}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.72}},
            {"action": "grasp", "params": {"arm": "left", "force": 50}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.90}},
        ],
    ),
    "grasp_and_move": Scenario(
        name="grasp_and_move",
        description="Pick up the red cube and move it to the left side",
        task="Pick up the red cube and move it to the blue region",
        initial_state={"gripper_open": 1.0, "target_x": 0.45, "target_y": 0.12, "target_z": 0.72},
        initial_gripper={"position": 0.04, "force": 0.0},
        action_sequence=[
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.85}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.72}},
            {"action": "grasp", "params": {"arm": "left", "force": 50}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.20, "y": 0.40, "z": 0.85}},
        ],
    ),
    "error_recovery": Scenario(
        name="error_recovery",
        description="Approach the blue block and retry grasp if first attempt misses",
        task="Carefully pick up the fragile object (may fail initially)",
        initial_state={"gripper_open": 1.0, "target_x": 0.45, "target_y": -0.12, "target_z": 0.71},
        initial_gripper={"position": 0.04, "force": 0.0},
        action_sequence=[
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": -0.12, "z": 0.85}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": -0.12, "z": 0.71}},
            {"action": "grasp", "params": {"arm": "left", "force": 20}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.45, "y": -0.12, "z": 0.68}},
            {"action": "grasp", "params": {"arm": "left", "force": 40}},
        ],
    ),
    "dynamic_environment": Scenario(
        name="dynamic_environment",
        description="Pick up the yellow sphere and transport it across the table",
        task="Pick up the moving object (it may shift during execution)",
        initial_state={"gripper_open": 1.0, "target_x": 0.52, "target_y": 0.0, "target_z": 0.71},
        initial_gripper={"position": 0.04, "force": 0.0},
        action_sequence=[
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.52, "y": 0.0,  "z": 0.85}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.52, "y": 0.0,  "z": 0.71}},
            {"action": "grasp", "params": {"arm": "left", "force": 30}},
            {"action": "move_arm_to", "params": {"arm": "left", "x": 0.30, "y": -0.20, "z": 0.85}},
        ],
    ),
}


def get_scenario(name: str) -> Scenario:
    """Fetch a scenario by name. Raises KeyError if unknown."""
    return SCENARIOS[name]


def list_scenarios() -> List[dict]:
    """Return a JSON-serializable catalog of all scenarios."""
    return [s.to_dict() for s in SCENARIOS.values()]
