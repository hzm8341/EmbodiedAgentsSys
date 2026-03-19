from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class GroundedSAMResult:
    """Two-stage grounded segmentation result."""
    masks: List[np.ndarray]          # pixel masks, each (H, W) uint8
    bboxes: List[List[float]]        # bounding boxes [x1, y1, x2, y2]
    scores: List[float]              # GroundingDINO confidence scores
    labels: List[str]                # text labels
    image_size: tuple                # (H, W)

    def best(self) -> Optional["GroundedSAMResult"]:
        """Return single highest-confidence result (for grasp mode)."""
        if not self.scores:
            return None
        idx = int(np.argmax(self.scores))
        return GroundedSAMResult(
            masks=[self.masks[idx]],
            bboxes=[self.bboxes[idx]],
            scores=[self.scores[idx]],
            labels=[self.labels[idx]],
            image_size=self.image_size,
        )
