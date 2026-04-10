"""URDF loader for Vuer Server."""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel


class LinkInfo(BaseModel):
    name: str
    visual_geometry: Optional[str] = None
    collision_geometry: Optional[str] = None
    material_color: Optional[List[float]] = None
    inertial_mass: Optional[float] = None


class JointInfo(BaseModel):
    name: str
    type: str  # revolute, fixed, prismatic, etc.
    parent: str
    child: str
    axis: Optional[List[float]] = None
    origin_xyz: Optional[List[float]] = None
    origin_rpy: Optional[List[float]] = None
    limit_lower: Optional[float] = None
    limit_upper: Optional[float] = None


class URDFModel(BaseModel):
    name: str
    links: List[LinkInfo]
    joints: List[JointInfo]


class URDFLoader:
    """Loads and parses URDF files."""

    def __init__(self, urdf_dir: Path):
        self.urdf_dir = Path(urdf_dir)

    def load(self, urdf_path: str) -> URDFModel:
        """Load URDF file and return structured model."""
        tree = ET.parse(urdf_path)
        root = tree.getroot()

        links = []
        joints = []

        for element in root:
            tag = element.tag.lower()
            if tag == 'link':
                links.append(self._parse_link(element))
            elif tag == 'joint':
                joints.append(self._parse_joint(element))

        return URDFModel(
            name=root.get('name', 'unknown'),
            links=links,
            joints=joints
        )

    def _parse_link(self, elem: ET.Element) -> LinkInfo:
        name = elem.get('name', '')
        visual_geom = None
        collision_geom = None
        color = None
        mass = None

        for child in elem:
            tag = child.tag.lower()
            if tag == 'visual':
                geom = child.find('geometry')
                if geom is not None:
                    mesh = geom.find('mesh')
                    if mesh is not None:
                        visual_geom = mesh.get('filename')
                material = child.find('material')
                if material is not None:
                    color_elem = material.find('color')
                    if color_elem is not None:
                        rgba = color_elem.get('rgba', '').split()
                        color = [float(x) for x in rgba] if rgba else None
            elif tag == 'collision':
                geom = child.find('geometry')
                if geom is not None:
                    mesh = geom.find('mesh')
                    if mesh is not None:
                        collision_geom = mesh.get('filename')
            elif tag == 'inertial':
                mass_elem = child.find('mass')
                if mass_elem is not None:
                    mass = float(mass_elem.get('value', 0))

        return LinkInfo(
            name=name,
            visual_geometry=visual_geom,
            collision_geometry=collision_geom,
            material_color=color,
            inertial_mass=mass
        )

    def _parse_joint(self, elem: ET.Element) -> JointInfo:
        name = elem.get('name', '')
        joint_type = elem.get('type', 'fixed')
        parent = elem.find('parent')
        child = elem.find('child')
        axis = elem.find('axis')
        origin = elem.find('origin')
        limit = elem.find('limit')

        parent_name = parent.get('link') if parent is not None else ''
        child_name = child.get('link') if child is not None else ''

        axis_xyz = None
        if axis is not None:
            axis_xyz = [float(x) for x in axis.get('xyz', '0 0 0').split()]

        origin_xyz = None
        origin_rpy = None
        if origin is not None:
            xyz = origin.get('xyz')
            rpy = origin.get('rpy')
            if xyz:
                origin_xyz = [float(x) for x in xyz.split()]
            if rpy:
                origin_rpy = [float(x) for x in rpy.split()]

        limit_lower = None
        limit_upper = None
        if limit is not None:
            limit_lower = float(limit.get('lower', 0))
            limit_upper = float(limit.get('upper', 0))

        return JointInfo(
            name=name,
            type=joint_type,
            parent=parent_name,
            child=child_name,
            axis=axis_xyz,
            origin_xyz=origin_xyz,
            origin_rpy=origin_rpy,
            limit_lower=limit_lower,
            limit_upper=limit_upper
        )
