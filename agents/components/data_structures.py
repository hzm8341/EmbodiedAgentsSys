from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np
import time


@dataclass
class ObjectInfo:
    """Object information from scene analysis"""
    name: str
    category: str
    bbox: List[float]
    mask: np.ndarray
    confidence: float
    attributes: Dict[str, Any]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category,
            "bbox": self.bbox,
            "mask": self.mask.tolist() if self.mask is not None else None,
            "confidence": self.confidence,
            "attributes": self.attributes
        }


@dataclass
class GraspPoint:
    """Grasp point information"""
    position: Dict[str, float]
    orientation: Dict[str, float]
    quality_score: float
    approach_direction: List[float]
    gripper_width: float
    collision_free: bool

    def to_dict(self) -> Dict:
        return {
            "position": self.position,
            "orientation": self.orientation,
            "quality_score": self.quality_score,
            "approach_direction": self.approach_direction,
            "gripper_width": self.gripper_width,
            "collision_free": self.collision_free
        }


@dataclass
class GraspCommand:
    """Grasp execution command"""
    target_object: str
    grasp_point: Dict[str, float]
    approach_vector: List[float]
    gripper_width: float
    force_limit: float
    pre_grasp_pose: Dict[str, float]
    post_grasp_pose: Dict[str, float]

    def to_dict(self) -> Dict:
        return {
            "target_object": self.target_object,
            "grasp_point": self.grasp_point,
            "approach_vector": self.approach_vector,
            "gripper_width": self.gripper_width,
            "force_limit": self.force_limit,
            "pre_grasp_pose": self.pre_grasp_pose,
            "post_grasp_pose": self.post_grasp_pose
        }


@dataclass
class SceneAnalysisResult:
    """Scene analysis result"""
    detected_objects: List[ObjectInfo]
    segmentation_masks: List[np.ndarray]
    grasp_candidates: List[GraspPoint]
    scene_description: str
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "detected_objects": [obj.to_dict() for obj in self.detected_objects],
            "segmentation_masks": [mask.tolist() for mask in self.segmentation_masks],
            "grasp_candidates": [gp.to_dict() for gp in self.grasp_candidates],
            "scene_description": self.scene_description,
            "timestamp": self.timestamp
        }
