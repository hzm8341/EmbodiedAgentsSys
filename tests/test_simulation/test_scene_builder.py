import pytest
from simulation.mujoco.scene_builder import SceneBuilder


class TestSceneBuilder:
    def test_create_empty_scene(self):
        """应该能创建空场景"""
        builder = SceneBuilder()
        assert builder is not None

    def test_add_ground(self):
        """应该能添加地面"""
        builder = SceneBuilder()
        builder.add_ground()
        model, data = builder.build()
        assert model is not None
        assert data is not None

    def test_add_box(self):
        """应该能添加方块"""
        builder = SceneBuilder()
        builder.add_body("box", "box", pos=(0, 0, 0.5), size=(0.1, 0.1, 0.1))
        model, data = builder.build()
        assert model is not None

    def test_build_returns_model_and_data(self):
        """build() 应返回 (model, data) 元组"""
        builder = SceneBuilder()
        result = builder.build()
        assert isinstance(result, tuple)
        assert len(result) == 2