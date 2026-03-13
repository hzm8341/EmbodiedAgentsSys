import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from agents.components.vla_plus import VLAPlus
from agents.config_vla_plus import VLAPlusConfig


def test_vla_plus_initialization():
    config = VLAPlusConfig(device="cpu")
    vla = VLAPlus(config=config)
    assert vla.config.device == "cpu"
    assert vla.config.confidence_threshold == 0.7
    assert vla._segmenter is None
    assert vla._processor is None
    assert vla._collision_checker is None


def test_vla_plus_default_config():
    vla = VLAPlus()
    assert vla.config is not None
    assert isinstance(vla.config, VLAPlusConfig)


def test_vla_plus_setup_components():
    config = VLAPlusConfig(device="cpu")
    vla = VLAPlus(config=config)
    vla._setup_components()
    assert vla._segmenter is not None
    assert vla._processor is not None
    assert vla._collision_checker is not None


@pytest.mark.asyncio
async def test_analyze_scene_returns_result():
    config = VLAPlusConfig(device="cpu")
    vla = VLAPlus(config=config)
    vla._setup_components()

    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    mock_seg_result = MagicMock()
    mock_seg_result.masks = [np.zeros((480, 640), dtype=np.uint8)]
    mock_seg_result.bboxes = [[0.1, 0.2, 0.3, 0.4]]
    mock_seg_result.scores = [0.9]
    mock_seg_result.areas = [1000.0]
    mock_seg_result.image_size = (480, 640)

    vla._segmenter.segment = AsyncMock(return_value=mock_seg_result)
    vla._processor.understand = AsyncMock(return_value={
        "objects": [{"name": "香蕉", "category": "水果", "confidence": 0.95, "attributes": {}}],
        "scene_description": "场景中有香蕉",
        "target_object": "香蕉"
    })

    result = await vla.analyze_scene(test_image, "抓取香蕉")

    assert result is not None
    assert "objects" in result
    assert "scene_description" in result
    assert result["scene_description"] == "场景中有香蕉"
