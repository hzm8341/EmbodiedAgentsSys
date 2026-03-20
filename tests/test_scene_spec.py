# tests/test_scene_spec.py
import pytest
from agents.components.scene_spec import SceneSpec

MINIMAL_DICT = {
    "scene_type": "warehouse_pick",
    "environment": "Large warehouse with shelving units",
    "robot_type": "arm",
    "task_description": "Pick red box from shelf A and place on conveyor",
}

FULL_DICT = {
    **MINIMAL_DICT,
    "objects": ["red_box", "shelf_A", "conveyor"],
    "constraints": ["avoid_fragile_area"],
    "success_criteria": ["box_on_conveyor"],
    "metadata": {"operator": "test"},
}


def test_from_dict_minimal():
    spec = SceneSpec.from_dict(MINIMAL_DICT)
    assert spec.scene_type == "warehouse_pick"
    assert spec.objects == []
    assert spec.constraints == []


def test_from_dict_full():
    spec = SceneSpec.from_dict(FULL_DICT)
    assert "red_box" in spec.objects
    assert spec.metadata["operator"] == "test"


def test_to_yaml_round_trip():
    spec = SceneSpec.from_dict(FULL_DICT)
    yaml_str = spec.to_yaml()
    spec2 = SceneSpec.from_yaml(yaml_str)
    assert spec2.scene_type == spec.scene_type
    assert spec2.objects == spec.objects
    assert spec2.constraints == spec.constraints


def test_missing_required_field_raises():
    bad = {k: v for k, v in MINIMAL_DICT.items() if k != "task_description"}
    with pytest.raises((KeyError, TypeError, ValueError)):
        SceneSpec.from_dict(bad)


def test_yaml_contains_scene_type():
    spec = SceneSpec.from_dict(MINIMAL_DICT)
    assert "warehouse_pick" in spec.to_yaml()


def test_robot_type_preserved():
    spec = SceneSpec.from_dict(MINIMAL_DICT)
    assert spec.robot_type == "arm"
