from pathlib import Path

import pytest

from agents.components.semantic_map import SemanticMap


def test_add_and_get_location(tmp_path):
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("desk", x=1.2, y=0.5, theta=0.0)
    loc = sm.get_location("desk")
    assert loc == {"x": 1.2, "y": 0.5, "theta": 0.0}


def test_add_and_get_object(tmp_path):
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("table", x=3.1, y=-0.8, theta=1.57)
    sm.add_object("cup", location="table", pos_3d=[3.1, -0.8, 0.85])
    obj = sm.get_object("cup")
    assert obj["location"] == "table"


def test_persist_and_reload(tmp_path):
    map_path = tmp_path / "map.yaml"
    sm1 = SemanticMap(map_path=str(map_path))
    sm1.add_location("shelf", x=2.0, y=1.0, theta=0.5)
    sm1.save()
    sm2 = SemanticMap(map_path=str(map_path))
    assert sm2.get_location("shelf") is not None


def test_list_locations(tmp_path):
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("desk", x=1.0, y=0.0, theta=0.0)
    sm.add_location("table", x=2.0, y=0.0, theta=0.0)
    assert set(sm.list_locations()) == {"desk", "table"}


def test_list_objects(tmp_path):
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("shelf", x=1.0, y=0.0, theta=0.0)
    sm.add_object("bottle", location="shelf")
    sm.add_object("cup", location="shelf")
    assert set(sm.list_objects()) == {"bottle", "cup"}


def test_summary_for_prompt_contains_location_names(tmp_path):
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("lab_bench", x=1.5, y=0.0, theta=0.0)
    sm.add_object("beaker", location="lab_bench")
    summary = sm.summary_for_prompt()
    assert "lab_bench" in summary
    assert "beaker" in summary


def test_get_location_returns_none_for_unknown(tmp_path):
    sm = SemanticMap(map_path=str(tmp_path / "map.yaml"))
    assert sm.get_location("nonexistent") is None


def test_get_object_returns_none_for_unknown(tmp_path):
    sm = SemanticMap(map_path=str(tmp_path / "map.yaml"))
    assert sm.get_object("nonexistent") is None


def test_add_object_preserves_all_zero_pos_3d(tmp_path):
    sm = SemanticMap(map_path=str(tmp_path / "map.yaml"))
    sm.add_location("base", x=0.0, y=0.0, theta=0.0)
    sm.add_object("target", location="base", pos_3d=[0.0, 0.0, 0.0])
    obj = sm.get_object("target")
    assert obj["pos_3d"] == [0.0, 0.0, 0.0]
