import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from agents.components.sam3_segmenter import SAM3Segmenter, SegmentationResult


def test_sam3_segmenter_initialization():
    """Test SAM3Segmenter initialization"""
    segmenter = SAM3Segmenter(
        model_path="test_models/sam3",
        device="cpu",
        confidence_threshold=0.5,
        min_object_size=50
    )

    assert segmenter.model_path == "test_models/sam3"
    assert segmenter.device == "cpu"
    assert segmenter.confidence_threshold == 0.5
    assert segmenter.min_object_size == 50
    assert segmenter._model is None
    assert segmenter._model_loaded is False


def test_sam3_segmenter_default_params():
    """Test SAM3Segmenter default parameters"""
    segmenter = SAM3Segmenter(model_path="test_models/sam3")
    assert segmenter.device == "cuda"
    assert segmenter.confidence_threshold == 0.5
    assert segmenter.min_object_size == 100


def test_filter_results_by_confidence():
    """Test that results below confidence threshold are filtered"""
    segmenter = SAM3Segmenter(model_path="test", device="cpu", confidence_threshold=0.7)

    masks = [np.ones((10, 10)), np.ones((10, 10)), np.ones((10, 10))]
    scores = [0.9, 0.5, 0.8]  # 0.5 should be filtered
    bboxes = [[0, 0, 10, 10], [0, 0, 10, 10], [0, 0, 10, 10]]

    valid = segmenter._filter_results(masks, scores, bboxes)
    assert 1 not in valid  # index 1 (score=0.5) should be filtered
    assert 0 in valid
    assert 2 in valid


def test_filter_results_by_size():
    """Test that small objects are filtered"""
    segmenter = SAM3Segmenter(model_path="test", device="cpu", min_object_size=100)

    small_mask = np.zeros((10, 10))
    small_mask[0:3, 0:3] = 1  # only 9 pixels, below threshold

    large_mask = np.ones((10, 10))  # 100 pixels

    masks = [small_mask, large_mask]
    scores = [0.9, 0.9]
    bboxes = [[0, 0, 3, 3], [0, 0, 10, 10]]

    valid = segmenter._filter_results(masks, scores, bboxes)
    assert 0 not in valid  # small mask filtered
    assert 1 in valid


@pytest.mark.asyncio
async def test_segment_returns_segmentation_result():
    """Test that segment() returns a SegmentationResult"""
    segmenter = SAM3Segmenter(model_path="test_models/sam3", device="cpu")
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    result = await segmenter.segment(test_image)

    assert isinstance(result, SegmentationResult)
    assert hasattr(result, "masks")
    assert hasattr(result, "bboxes")
    assert hasattr(result, "scores")
    assert hasattr(result, "areas")
    assert hasattr(result, "image_size")
    assert result.image_size == (480, 640)
