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
