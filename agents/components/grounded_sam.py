from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np


@dataclass
class GroundedSAMResult:
    """Result of a two-stage grounded segmentation pipeline.

    All list fields (masks, bboxes, scores, labels) are parallel and have the same length,
    one entry per detected object.
    """

    masks: List[np.ndarray]                              # pixel masks, each (H, W) uint8
    bboxes: List[Tuple[float, float, float, float]]      # bounding boxes (x1, y1, x2, y2)
    scores: List[float]                                  # GroundingDINO confidence scores
    labels: List[str]                                    # text labels
    image_size: Tuple[int, int]                          # (H, W)

    def best(self) -> Optional["GroundedSAMResult"]:
        """Return a new GroundedSAMResult containing only the highest-confidence detection.

        Returns None if scores is empty (no detections present).
        """
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
