import numpy as np
import pytest
from agents.components.grounded_sam import GroundedSAMResult

def test_grounded_sam_result_fields():
    result = GroundedSAMResult(
        masks=[np.zeros((480, 640), dtype=np.uint8)],
        bboxes=[[10.0, 20.0, 100.0, 150.0]],
        scores=[0.85],
        labels=["cup"],
        image_size=(480, 640),
    )
    assert len(result.masks) == 1
    assert result.labels[0] == "cup"
    assert result.image_size == (480, 640)
