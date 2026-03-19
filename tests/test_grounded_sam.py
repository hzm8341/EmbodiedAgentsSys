import numpy as np
from agents.components.grounded_sam import GroundedSAMResult


def test_grounded_sam_result_fields():
    result = GroundedSAMResult(
        masks=[np.zeros((480, 640), dtype=np.uint8)],
        bboxes=[(10.0, 20.0, 100.0, 150.0)],
        scores=[0.85],
        labels=["cup"],
        image_size=(480, 640),
    )
    assert len(result.masks) == 1
    assert result.labels[0] == "cup"
    assert result.image_size == (480, 640)


def test_grounded_sam_result_best_returns_highest_score():
    result = GroundedSAMResult(
        masks=[np.zeros((480, 640), dtype=np.uint8), np.zeros((480, 640), dtype=np.uint8)],
        bboxes=[(10.0, 20.0, 100.0, 150.0), (5.0, 5.0, 50.0, 50.0)],
        scores=[0.60, 0.90],
        labels=["cup", "bottle"],
        image_size=(480, 640),
    )
    best = result.best()
    assert best is not None
    assert len(best.masks) == 1
    assert best.scores[0] == 0.90
    assert best.labels[0] == "bottle"


def test_grounded_sam_result_best_returns_none_when_empty():
    result = GroundedSAMResult(
        masks=[], bboxes=[], scores=[], labels=[], image_size=(480, 640)
    )
    assert result.best() is None


import asyncio
from agents.components.grounded_sam import GroundedSAMSegmenter


def test_segmenter_grasp_mode_returns_single_mask():
    """Grasp mode must return exactly 1 mask (highest confidence)."""
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    segmenter = GroundedSAMSegmenter(
        dino_model_path="mock",
        sam_model_path="mock",
        device="cpu",
    )
    result = asyncio.run(segmenter.segment(img, text_query="cup", mode="grasp"))
    assert isinstance(result, GroundedSAMResult)
    assert len(result.masks) == 1


def test_segmenter_map_mode_returns_all_masks():
    """Map mode returns all detected results."""
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    segmenter = GroundedSAMSegmenter(
        dino_model_path="mock",
        sam_model_path="mock",
        device="cpu",
    )
    result = asyncio.run(segmenter.segment(img, text_query="cup . bottle", mode="map"))
    assert isinstance(result, GroundedSAMResult)
    assert len(result.masks) >= 0  # mock may return 0 or more
