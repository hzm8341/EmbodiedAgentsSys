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


def test_grasp_and_move_mentions_target():
    sc = get_scenario("grasp_and_move")
    assert "target_x" in sc.initial_state
    assert sc.initial_state["target_x"] == pytest.approx(0.45)


def test_dynamic_environment_has_target():
    sc = get_scenario("dynamic_environment")
    assert "target_x" in sc.initial_state
    # action_sequence must include at least one grasp step
    actions = [s["action"] for s in sc.action_sequence]
    assert "grasp" in actions


def test_error_recovery_has_multiple_grasp_attempts():
    sc = get_scenario("error_recovery")
    grasp_count = sum(1 for s in sc.action_sequence if s["action"] == "grasp")
    assert grasp_count >= 2, f"expected ≥2 grasp attempts, got {grasp_count}"
