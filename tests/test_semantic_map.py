import tempfile
from pathlib import Path

import pytest

from agents.components.semantic_map import SemanticMap


def test_add_and_get_location():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("desk", x=1.2, y=0.5, theta=0.0)
    loc = sm.get_location("desk")
    assert loc == {"x": 1.2, "y": 0.5, "theta": 0.0}


def test_add_and_get_object():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
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
    sm2.load()
    assert sm2.get_location("shelf") is not None


def test_list_locations():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("desk", x=1.0, y=0.0, theta=0.0)
    sm.add_location("table", x=2.0, y=0.0, theta=0.0)
    assert set(sm.list_locations()) == {"desk", "table"}


def test_list_objects():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("shelf", x=1.0, y=0.0, theta=0.0)
    sm.add_object("bottle", location="shelf")
    sm.add_object("cup", location="shelf")
    assert set(sm.list_objects()) == {"bottle", "cup"}


def test_summary_for_prompt_contains_location_names():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("lab_bench", x=1.5, y=0.0, theta=0.0)
    sm.add_object("beaker", location="lab_bench")
    summary = sm.summary_for_prompt()
    assert "lab_bench" in summary
    assert "beaker" in summary
