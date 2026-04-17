"""Predefined test scenarios for the interactive agent debugger.

Each scenario bundles an initial observation and a task description so that the
frontend can launch pre-canned demos with a single click.
"""
from __future__ import annotations

from dataclasses import dataclass
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
        description="Robot scans the workspace to identify objects and their layout",
        task="Scan the workspace and identify all objects",
        initial_state={
            "gripper_open": 1.0,
            "object_red_cube_x": 0.5,
            "object_red_cube_y": 0.0,
            "object_blue_block_x": 0.0,
            "object_blue_block_y": 0.5,
        },
        initial_gripper={"position": 0.04, "force": 0.0},
    ),
    "single_grasp": Scenario(
        name="single_grasp",
        description="Pick up a target object in a single motion",
        task="Pick up the red cube",
        initial_state={
            "gripper_open": 1.0,
            "target_x": 0.4,
            "target_y": 0.2,
            "target_z": 0.4,
        },
        initial_gripper={"position": 0.04, "force": 0.0},
    ),
    "grasp_and_move": Scenario(
        name="grasp_and_move",
        description="Pick up an object and move it to a target region",
        task="Pick up the red cube and move it to the blue region",
        initial_state={
            "gripper_open": 1.0,
            "target_x": 0.4,
            "target_y": 0.2,
            "target_z": 0.4,
            "goal_x": 0.1,
            "goal_y": 0.5,
        },
        initial_gripper={"position": 0.04, "force": 0.0},
    ),
    "error_recovery": Scenario(
        name="error_recovery",
        description="Attempt a difficult grasp and recover from initial failure",
        task="Carefully pick up the fragile object (may fail initially)",
        initial_state={
            "gripper_open": 1.0,
            "target_x": 0.4,
            "target_y": 0.2,
            "target_z": 0.4,
            "fragile": 1.0,
        },
        initial_gripper={"position": 0.04, "force": 0.0},
    ),
    "dynamic_environment": Scenario(
        name="dynamic_environment",
        description="Object moves mid-task, requiring adaptive re-planning",
        task="Pick up the moving object (it may shift during execution)",
        initial_state={
            "gripper_open": 1.0,
            "target_x": 0.4,
            "target_y": 0.2,
            "target_z": 0.4,
            "target_moving": 1.0,
        },
        initial_gripper={"position": 0.04, "force": 0.0},
    ),
}


def get_scenario(name: str) -> Scenario:
    """Fetch a scenario by name. Raises KeyError if unknown."""
    return SCENARIOS[name]


def list_scenarios() -> List[dict]:
    """Return a JSON-serializable catalog of all scenarios."""
    return [s.to_dict() for s in SCENARIOS.values()]
