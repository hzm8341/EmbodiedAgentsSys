from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


def test_default_mujoco_urdf_mesh_references_exist() -> None:
    from simulation.mujoco.config import DEFAULT_URDF_PATH

    urdf_path = Path(DEFAULT_URDF_PATH)
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    missing: list[str] = []
    for mesh in root.findall(".//mesh"):
        filename = (mesh.attrib.get("filename") or "").strip()
        if not filename:
            continue
        if "://" in filename:
            continue
        resolved = (urdf_path.parent / filename).resolve()
        if not resolved.exists():
            missing.append(filename)

    assert missing == []


def test_default_mujoco_urdf_uses_meter_scale_debug_model() -> None:
    """The dev viewer should use the meter-scale model, not oversized STL meshes."""
    from simulation.mujoco.config import DEFAULT_URDF_PATH

    assert Path(DEFAULT_URDF_PATH).name == "eu_ca_simple.urdf"


def test_vuer_robot_map_points_to_existing_urdf() -> None:
    """Vuer must not advertise a URDF filename that is absent from assets."""
    from vuer_server.server import ROBOT_URDF_MAP

    for urdf_dir, urdf_file in ROBOT_URDF_MAP.values():
        assert Path(urdf_dir, urdf_file).exists()


def test_debug_table_is_in_front_of_robot_base() -> None:
    """The work table should not overlap the simple robot base footprint."""
    from simulation.mujoco.scene_builder import GRASPABLE_OBJECTS, TABLE_CENTER_Y, TABLE_HALF_Y

    assert TABLE_CENTER_Y - TABLE_HALF_Y > 0.12
    assert min(obj["pos"][1] for obj in GRASPABLE_OBJECTS.values()) > 0.25
