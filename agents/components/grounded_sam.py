from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple
import numpy as np

__all__ = ["GroundedSAMResult", "GroundedSAMSegmenter"]


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


def _compute_iou(b1: Tuple[float, float, float, float],
                 b2: Tuple[float, float, float, float]) -> float:
    """Compute IoU between two bounding boxes [x1, y1, x2, y2]."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


class GroundedSAMSegmenter:
    """Two-stage open-vocabulary segmenter: GroundingDINO detection + SAM refinement.

    Pass dino_model_path="mock" and sam_model_path="mock" to use mock backends
    for testing without real model weights.

    Args:
        dino_model_path: Path to GroundingDINO weights, or "mock" for testing.
        sam_model_path: Path to SAM weights, or "mock" for testing.
        device: Inference device ("cuda" or "cpu").
        box_threshold: GroundingDINO bounding-box confidence threshold.
        text_threshold: GroundingDINO text-matching confidence threshold.
        nms_threshold: IoU threshold for NMS deduplication.
    """

    def __init__(
        self,
        dino_model_path: str,
        sam_model_path: str,
        device: str = "cuda",
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
        nms_threshold: float = 0.8,
    ):
        self.dino_model_path = dino_model_path
        self.sam_model_path = sam_model_path
        self.device = device
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self.nms_threshold = nms_threshold
        self._dino = None
        self._sam = None
        self._use_mock = (dino_model_path == "mock" or sam_model_path == "mock")

    def _load_models(self) -> None:
        """Lazy-load models on first call."""
        if self._dino is not None:
            return
        if self._use_mock:
            self._dino = _MockDINO()
            self._sam = _MockSAM()
            return
        try:
            from groundingdino.util.inference import load_model as load_dino
            from segment_anything import sam_model_registry, SamPredictor

            self._dino = load_dino(
                "groundingdino/config/GroundingDINO_SwinT_OGC.py",
                self.dino_model_path,
                device=self.device,
            )
            sam = sam_model_registry["vit_h"](checkpoint=self.sam_model_path)
            sam.to(device=self.device)
            self._sam = SamPredictor(sam)
        except ImportError as e:
            raise ImportError(
                f"Install groundingdino and segment_anything first: {e}"
            ) from e

    def _run_dino(
        self, image: np.ndarray, text_query: str
    ) -> Tuple[List[Tuple[float, float, float, float]], List[float], List[str]]:
        """Run GroundingDINO; returns (bboxes, scores, labels)."""
        return self._dino(image, text_query, self.box_threshold, self.text_threshold)

    def _run_sam(
        self, image: np.ndarray, bboxes: List[Tuple[float, float, float, float]]
    ) -> List[np.ndarray]:
        """Run SAM on each bounding box; returns list of masks."""
        return self._sam(image, bboxes)

    def _apply_nms(
        self,
        bboxes: List[Tuple[float, float, float, float]],
        scores: List[float],
        labels: List[str],
    ) -> Tuple[List[Tuple[float, float, float, float]], List[float], List[str]]:
        """Remove overlapping boxes with IoU > nms_threshold (keep highest score)."""
        if not bboxes:
            return bboxes, scores, labels

        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        keep: List[int] = []
        suppressed: set = set()

        for pos_i, i in enumerate(order):
            if i in suppressed:
                continue
            keep.append(i)
            for pos_j in range(pos_i + 1, len(order)):
                j = order[pos_j]
                if j in suppressed:
                    continue
                if _compute_iou(bboxes[i], bboxes[j]) > self.nms_threshold:
                    suppressed.add(j)

        return (
            [bboxes[k] for k in keep],
            [scores[k] for k in keep],
            [labels[k] for k in keep],
        )

    def segment(
        self,
        image: np.ndarray,
        text_query: str,
        mode: Literal["grasp", "map"] = "grasp",
    ) -> GroundedSAMResult:
        """Run two-stage segmentation and return results filtered by mode.

        Args:
            image: Input image (H, W, 3) uint8.
            text_query: Object name(s) to detect. Separate multiple with " . ".
            mode: "grasp" returns single highest-confidence mask;
                  "map" returns all detected masks.

        Returns:
            GroundedSAMResult (may be empty if no objects detected).
        """
        self._load_models()
        height, width = image.shape[:2]

        bboxes, scores, labels = self._run_dino(image, text_query)
        bboxes, scores, labels = self._apply_nms(bboxes, scores, labels)

        if not bboxes:
            return GroundedSAMResult(
                masks=[], bboxes=[], scores=[], labels=[],
                image_size=(height, width),
            )

        masks = self._run_sam(image, bboxes)

        result = GroundedSAMResult(
            masks=masks,
            bboxes=bboxes,
            scores=scores,
            labels=labels,
            image_size=(height, width),
        )

        if mode == "grasp":
            return result.best() or result
        return result


class _MockDINO:
    """Mock GroundingDINO for testing — returns one fixed bounding box."""

    def __call__(
        self,
        image: np.ndarray,
        text_query: str,
        box_thr: float,
        text_thr: float,
    ) -> Tuple[List[Tuple[float, float, float, float]], List[float], List[str]]:
        h, w = image.shape[:2]
        label = text_query.split(" . ")[0]
        return (
            [(w * 0.1, h * 0.1, w * 0.5, h * 0.5)],
            [0.85],
            [label],
        )


class _MockSAM:
    """Mock SAM for testing — fills the bounding-box region."""

    def __call__(
        self,
        image: np.ndarray,
        bboxes: List[Tuple[float, float, float, float]],
    ) -> List[np.ndarray]:
        h, w = image.shape[:2]
        masks = []
        for bbox in bboxes:
            mask = np.zeros((h, w), dtype=np.uint8)
            x1, y1, x2, y2 = (int(v) for v in bbox)
            mask[y1:y2, x1:x2] = 1
            masks.append(mask)
        return masks
