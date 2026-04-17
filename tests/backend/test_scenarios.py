"""Tests for predefined debugging scenarios."""
import pytest
from agents.core.types import RobotObservation
from backend.services.scenarios import (
    SCENARIOS,
    Scenario,
    get_scenario,
    list_scenarios,
)


EXPECTED_NAMES = {
    "spatial_detection",
    "single_grasp",
    "grasp_and_move",
    "error_recovery",
    "dynamic_environment",
}


def test_all_five_scenarios_registered():
    assert set(SCENARIOS.keys()) == EXPECTED_NAMES
    assert len(SCENARIOS) == 5


@pytest.mark.parametrize("name", sorted(EXPECTED_NAMES))
def test_scenario_fields_are_populated(name):
    sc = get_scenario(name)
    assert isinstance(sc, Scenario)
    assert sc.name == name
    assert sc.description
    assert sc.task
    assert "gripper_open" in sc.initial_state


@pytest.mark.parametrize("name", sorted(EXPECTED_NAMES))
def test_scenario_builds_robot_observation(name):
    sc = get_scenario(name)
    obs = sc.build_observation()
    assert isinstance(obs, RobotObservation)
    # Copy semantics: mutating returned state must not leak into the scenario
    obs.state["mutated"] = 9.9
    assert "mutated" not in sc.initial_state


def test_get_scenario_unknown_raises():
    with pytest.raises(KeyError):
        get_scenario("does_not_exist")


def test_list_scenarios_is_json_safe():
    catalog = list_scenarios()
    assert len(catalog) == 5
    for entry in catalog:
        assert set(entry.keys()) == {"name", "description", "task"}
        assert all(isinstance(v, str) for v in entry.values())


def test_grasp_and_move_mentions_target_and_goal():
    sc = get_scenario("grasp_and_move")
    assert "goal_x" in sc.initial_state
    assert "target_x" in sc.initial_state


def test_dynamic_environment_marks_movement():
    sc = get_scenario("dynamic_environment")
    assert sc.initial_state.get("target_moving") == 1.0


def test_error_recovery_marks_fragile():
    sc = get_scenario("error_recovery")
    assert sc.initial_state.get("fragile") == 1.0
