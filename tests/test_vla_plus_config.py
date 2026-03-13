# tests/test_vla_plus_config.py
import pytest
from agents.config_vla_plus import VLAPlusConfig, SceneUnderstandingConfig

def test_vla_plus_config_defaults():
    """Test VLAPlusConfig default values"""
    config = VLAPlusConfig()
    assert config.sam3_model_path == "models/sam3/sam3_vit_h.pth"
    assert config.qwen3l_model_path == "models/qwen3l/qwen3l-7b-instruct"
    assert config.confidence_threshold == 0.7
    assert config.enable_collision_check is True

def test_scene_understanding_config_defaults():
    """Test SceneUnderstandingConfig default values"""
    config = SceneUnderstandingConfig()
    assert "水果" in config.object_categories
    assert "颜色" in config.attribute_categories
    assert config.temperature == 0.1
    assert config.max_tokens == 500
