import pytest
import numpy as np
from agents.components.collision_checker import CollisionChecker


def test_collision_checker_initialization():
    checker = CollisionChecker(
        collision_margin=0.05,
        workspace_bounds={"x": [-0.5, 0.5], "y": [-0.5, 0.5], "z": [0.0, 0.8]}
    )
    assert checker.collision_margin == 0.05
    assert checker.workspace_bounds["x"] == [-0.5, 0.5]
    assert checker.workspace_bounds["z"][1] == 0.8


def test_collision_checker_defaults():
    checker = CollisionChecker()
    assert checker.collision_margin == 0.05
    assert "x" in checker.workspace_bounds
    assert "y" in checker.workspace_bounds
    assert "z" in checker.workspace_bounds


def test_validate_grasp_points_filters_out_of_bounds():
    checker = CollisionChecker(collision_margin=0.01)
    grasp_points = [
        {
            "position": {"x": 0.1, "y": 0.1, "z": 0.3},
            "quality_score": 0.9,
            "approach_direction": [0, 0, -1],
            "gripper_width": 0.05,
            "collision_free": True
        },
        {
            "position": {"x": 10.0, "y": 10.0, "z": 10.0},  # Out of bounds
            "quality_score": 0.8,
            "approach_direction": [0, 0, -1],
            "gripper_width": 0.05,
            "collision_free": True
        }
    ]
    validated = checker.validate_grasp_points(grasp_points)
    in_bounds = [p for p in validated if p["position"]["x"] == 0.1]
    out_of_bounds = [p for p in validated if p["position"]["x"] == 10.0]
    assert len(in_bounds) == 1
    assert len(out_of_bounds) == 1
    assert out_of_bounds[0]["collision_free"] is False


def test_workspace_bounds_check():
    checker = CollisionChecker(collision_margin=0.0)
    assert checker._check_workspace_bounds({"x": 0.0, "y": 0.0, "z": 0.4}) is True
    assert checker._check_workspace_bounds({"x": 1.0, "y": 0.0, "z": 0.4}) is False
