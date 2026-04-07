"""
Week 8 Task 2.3：Vision 工具测试

验证视觉处理工具的功能：
- 对象检测
- 图像分割
- 姿态估计
- 相机标定
"""

import pytest


class TestVisionToolBasics:
    """Vision 工具基本功能"""

    @pytest.mark.asyncio
    async def test_detect_objects(self):
        """可以检测对象"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()
        result = await tool.execute(operation="detect_objects")

        assert result is not None
        assert result.get("success") is True
        assert "detections" in result
        assert isinstance(result["detections"], list)

    @pytest.mark.asyncio
    async def test_segment_image(self):
        """支持图像分割"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()
        result = await tool.execute(operation="segment")

        assert result is not None
        assert result.get("success") is True
        assert "segments" in result
        assert result.get("operation") == "segment"

    @pytest.mark.asyncio
    async def test_pose_estimation(self):
        """支持姿态估计"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()
        result = await tool.execute(operation="estimate_pose")

        assert result is not None
        assert result.get("success") is True
        assert "pose" in result
        assert "position" in result["pose"]
        assert "orientation" in result["pose"]

    @pytest.mark.asyncio
    async def test_camera_calibration(self):
        """支持相机标定"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()
        result = await tool.execute(operation="calibrate")

        assert result is not None
        assert result.get("success") is True
        assert "calibration_result" in result
        assert "calibration_error" in result


class TestVisionToolWithImages:
    """Vision 工具处理图像数据"""

    @pytest.mark.asyncio
    async def test_detect_objects_with_image_data(self):
        """检测带有图像数据的对象"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()

        # 模拟图像数据
        image_data = {"width": 640, "height": 480, "channels": 3}

        result = await tool.execute(
            operation="detect_objects", image_data=image_data
        )

        assert result.get("success") is True
        assert "detections" in result

    @pytest.mark.asyncio
    async def test_segment_with_config(self):
        """图像分割支持配置"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()

        config = {"algorithm": "watershed", "threshold": 0.5}

        result = await tool.execute(operation="segment", config=config)

        assert result.get("success") is True
        assert result.get("algorithm") == "watershed"


class TestVisionToolValidation:
    """Vision 工具输入验证"""

    @pytest.mark.asyncio
    async def test_invalid_operation(self):
        """拒绝无效的操作"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()

        with pytest.raises(ValueError):
            await tool.execute(operation="invalid_operation")

    @pytest.mark.asyncio
    async def test_operation_required(self):
        """操作参数是必需的"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()

        with pytest.raises(ValueError):
            await tool.execute()


class TestVisionToolMetadata:
    """Vision 工具元数据"""

    def test_vision_tool_metadata(self):
        """Vision 工具有正确的元数据"""
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()

        assert tool.name == "vision"
        assert tool.description is not None
        assert len(tool.description) > 0
        assert hasattr(tool, "keywords")
        assert "vision" in tool.keywords
        assert "detect" in tool.keywords

    def test_vision_tool_is_tool_base(self):
        """Vision 工具继承自 ToolBase"""
        from agents.execution.tools.vision_tool import VisionTool
        from agents.execution.tools.base import ToolBase

        assert issubclass(VisionTool, ToolBase)


class TestVisionToolIntegration:
    """Vision 工具与工具框架的集成"""

    @pytest.mark.asyncio
    async def test_vision_with_tool_registry(self):
        """Vision 工具可以注册到 ToolRegistry"""
        from agents.execution.tools.vision_tool import VisionTool
        from agents.execution.tools.registry import ToolRegistry

        registry = ToolRegistry()
        vision = VisionTool()
        registry.register("vision", vision)

        retrieved = registry.get("vision")
        assert retrieved is vision

    @pytest.mark.asyncio
    async def test_vision_with_strategy_selector(self):
        """Vision 工具可以通过 StrategySelector 选择"""
        from agents.execution.tools.vision_tool import VisionTool
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.strategy import StrategySelector

        registry = ToolRegistry()
        vision = VisionTool()
        registry.register("vision", vision)

        selector = StrategySelector(registry)

        # 通过关键词选择
        tool = selector.find_tool_by_keyword("detect")
        assert tool is vision

        # 为任务排名
        ranked = selector.rank_tools_for_task("detect objects in image")
        assert len(ranked) > 0
        assert ranked[0] is vision


class TestVisionToolPerformance:
    """Vision 工具性能"""

    @pytest.mark.asyncio
    async def test_fast_object_detection(self):
        """对象检测应该快速完成"""
        import time
        from agents.execution.tools.vision_tool import VisionTool

        tool = VisionTool()

        start = time.time()
        result = await tool.execute(operation="detect_objects")
        elapsed = time.time() - start

        assert result.get("success") is True
        assert elapsed < 1.0, f"Detection took {elapsed:.3f}s, expected < 1s"
