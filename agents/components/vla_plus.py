import numpy as np
import sys
import importlib
from typing import Dict, Any, Optional

# Use importlib to ensure we get the same VLAPlusConfig instance as the caller.
# This avoids double-import issues caused by editable installs + PYTHONPATH.
_cfg_module = importlib.import_module('agents.config_vla_plus')
VLAPlusConfig = _cfg_module.VLAPlusConfig

from .sam3_segmenter import SAM3Segmenter
from .qwen3l_processor import Qwen3LProcessor
from .collision_checker import CollisionChecker


class VLAPlus:
    """
    VLA+ (Vision-Language-Action Plus) main component.

    Integrates SAM3 segmentation and qwen3-l scene understanding
    to enable voice-controlled object grasping.
    """

    def __init__(self, config: Optional[VLAPlusConfig] = None):
        self.config = config or VLAPlusConfig()
        self._segmenter: Optional[SAM3Segmenter] = None
        self._processor: Optional[Qwen3LProcessor] = None
        self._collision_checker: Optional[CollisionChecker] = None

    def _setup_components(self) -> None:
        """Initialize sub-components lazily."""
        if self._segmenter is None:
            self._segmenter = SAM3Segmenter(
                model_path=self.config.sam3_model_path,
                device=self.config.device,
                confidence_threshold=self.config.confidence_threshold,
                min_object_size=self.config.min_object_size
            )
        if self._processor is None:
            self._processor = Qwen3LProcessor(
                model_path=self.config.qwen3l_model_path,
                device=self.config.device
            )
        if self._collision_checker is None:
            self._collision_checker = CollisionChecker(
                collision_margin=self.config.collision_margin
            )

    async def analyze_scene(
        self,
        image: np.ndarray,
        instruction: str
    ) -> Dict[str, Any]:
        """
        Analyze scene from image and instruction.

        Args:
            image: RGB image (H, W, 3) uint8
            instruction: User instruction text

        Returns:
            Dict with objects, scene_description, target_object, grasp_candidates
        """
        self._setup_components()

        # Step 1: Segment the scene
        seg_result = await self._segmenter.segment(image)

        # Convert SegmentationResult to dict for processor
        seg_dict = {
            "masks": seg_result.masks,
            "bboxes": seg_result.bboxes,
            "scores": seg_result.scores,
            "areas": seg_result.areas,
            "image_size": seg_result.image_size
        }

        # Step 2: Understand the scene
        understanding = await self._processor.understand(image, seg_dict, instruction)

        # Step 3: Generate grasp candidates
        grasp_candidates = self._generate_grasp_candidates(seg_result, understanding)

        # Step 4: Validate grasp candidates
        if self.config.enable_collision_check and grasp_candidates:
            grasp_candidates = self._collision_checker.validate_grasp_points(grasp_candidates)

        return {
            "objects": understanding.get("objects", []),
            "scene_description": understanding.get("scene_description", ""),
            "target_object": understanding.get("target_object"),
            "grasp_candidates": grasp_candidates
        }

    def _generate_grasp_candidates(
        self,
        seg_result: Any,
        understanding: Dict[str, Any]
    ) -> list:
        """Generate grasp candidates from segmentation and understanding."""
        candidates = []
        for i, bbox in enumerate(seg_result.bboxes[:self.config.max_grasp_candidates]):
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            candidates.append({
                "position": {"x": cx / 1000.0, "y": cy / 1000.0, "z": 0.3},
                "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                "quality_score": seg_result.scores[i] if i < len(seg_result.scores) else 0.5,
                "approach_direction": [0.0, 0.0, -1.0],
                "gripper_width": 0.05,
                "collision_free": True
            })
        return candidates
