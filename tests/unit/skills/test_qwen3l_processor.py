import pytest
import numpy as np
from unittest.mock import Mock, patch
from agents.components.qwen3l_processor import Qwen3LProcessor, SceneUnderstandingResult


def test_qwen3l_processor_initialization():
    """Test Qwen3LProcessor initialization"""
    processor = Qwen3LProcessor(
        model_path="test_models/qwen3l",
        device="cpu",
        temperature=0.2,
        max_tokens=1000
    )
    assert processor.model_path == "test_models/qwen3l"
    assert processor.device == "cpu"
    assert processor.temperature == 0.2
    assert processor.max_tokens == 1000
    assert processor._model is None
    assert processor._model_loaded is False


def test_qwen3l_processor_default_params():
    """Test Qwen3LProcessor default parameters"""
    processor = Qwen3LProcessor(model_path="test_models/qwen3l")
    assert processor.device == "cuda"
    assert processor.temperature == 0.1
    assert processor.max_tokens == 500


def test_build_prompt_contains_instruction():
    """Test that prompt includes the user instruction"""
    processor = Qwen3LProcessor(model_path="test", device="cpu")
    seg_result = {"masks": [np.zeros((10, 10))], "scores": [0.9], "bboxes": [[0, 0, 10, 10]]}
    prompt = processor._build_prompt("抓取香蕉", seg_result)
    assert "抓取香蕉" in prompt
    assert "1" in prompt  # num_objects


def test_parse_response_valid_json():
    """Test parsing a valid JSON response"""
    processor = Qwen3LProcessor(model_path="test", device="cpu")
    response = '''{"scene_description": "场景中有香蕉", "objects": [{"name": "香蕉", "category": "水果", "confidence": 0.95, "attributes": {"颜色": "黄色"}}], "target_object": "香蕉"}'''
    result = processor._parse_response(response)
    assert result["scene_description"] == "场景中有香蕉"
    assert len(result["objects"]) == 1
    assert result["objects"][0]["name"] == "香蕉"
    assert result["target_object"] == "香蕉"


def test_parse_response_fallback():
    """Test fallback parsing when JSON is invalid"""
    processor = Qwen3LProcessor(model_path="test", device="cpu")
    response = "场景中有香蕉和苹果"
    result = processor._parse_response(response)
    assert "scene_description" in result
    assert "objects" in result
    assert isinstance(result["objects"], list)


@pytest.mark.asyncio
async def test_understand_returns_dict():
    """Test that understand() returns a dict with required keys"""
    processor = Qwen3LProcessor(model_path="test_models/qwen3l", device="cpu")
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    seg_result = {
        "masks": [np.zeros((100, 100), dtype=bool)],
        "bboxes": [[0.1, 0.2, 0.3, 0.4]],
        "scores": [0.9],
        "areas": [1000.0],
        "image_size": (480, 640)
    }

    result = await processor.understand(test_image, seg_result, "看看场景里有什么")

    assert isinstance(result, dict)
    assert "objects" in result
    assert "scene_description" in result
    assert isinstance(result["objects"], list)
