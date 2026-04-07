"""
Week 8 Task 2.2：Move 工具测试

验证移动规划工具的功能：
- 绝对位置移动
- 相对移动
- 避碰规划
- 轨迹规划
"""

import pytest


class TestMoveToolBasics:
    """Move 工具基本功能"""

    @pytest.mark.asyncio
    async def test_move_to_position(self):
        """可以移动到指定位置"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()
        target = {"x": 0.5, "y": 0.3, "z": 0.2}
        result = await tool.execute(target=target, mode="direct")

        assert result is not None
        assert result.get("success") is True
        assert result.get("target") == target
        assert "current_position" in result

    @pytest.mark.asyncio
    async def test_move_relative(self):
        """支持相对移动"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()

        # 第一次移动到基准位置
        base_target = {"x": 0.5, "y": 0.3, "z": 0.2}
        await tool.execute(target=base_target, mode="direct")

        # 相对移动
        delta = {"x": 0.1, "y": -0.05, "z": 0.02}
        result = await tool.execute(target=delta, mode="relative")

        assert result.get("success") is True
        assert result.get("mode") == "relative"

    @pytest.mark.asyncio
    async def test_collision_avoidance(self):
        """支持避碰规划"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()
        target = {"x": 0.5, "y": 0.3, "z": 0.2}

        # 使用避碰规划
        result = await tool.execute(target=target, mode="safe")

        assert result.get("success") is True
        assert result.get("mode") == "safe"
        assert "path_length" in result

    @pytest.mark.asyncio
    async def test_move_trajectory(self):
        """支持轨迹规划"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()

        # 定义一系列路径点
        trajectory = [
            {"x": 0.3, "y": 0.2, "z": 0.1},
            {"x": 0.5, "y": 0.3, "z": 0.15},
            {"x": 0.7, "y": 0.4, "z": 0.2},
        ]

        result = await tool.execute(trajectory=trajectory, mode="trajectory")

        assert result.get("success") is True
        assert result.get("mode") == "trajectory"
        assert result.get("waypoint_count") == 3


class TestMoveToolValidation:
    """Move 工具输入验证"""

    @pytest.mark.asyncio
    async def test_invalid_coordinates(self):
        """拒绝无效的坐标"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()

        # 坐标超出范围
        with pytest.raises(ValueError):
            target = {"x": 2.0, "y": 0.3, "z": 0.2}
            await tool.execute(target=target, mode="direct")

    @pytest.mark.asyncio
    async def test_invalid_mode(self):
        """拒绝无效的移动模式"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()

        with pytest.raises(ValueError):
            target = {"x": 0.5, "y": 0.3, "z": 0.2}
            await tool.execute(target=target, mode="invalid_mode")

    @pytest.mark.asyncio
    async def test_missing_coordinates(self):
        """检查必要的坐标信息"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()

        # 缺少 z 坐标
        with pytest.raises(ValueError):
            target = {"x": 0.5, "y": 0.3}
            await tool.execute(target=target, mode="direct")


class TestMoveToolMetadata:
    """Move 工具元数据"""

    def test_move_tool_metadata(self):
        """Move 工具有正确的元数据"""
        from agents.execution.tools.move_tool import MoveTool

        tool = MoveTool()

        assert tool.name == "move"
        assert tool.description is not None
        assert len(tool.description) > 0
        assert hasattr(tool, "keywords")
        assert "move" in tool.keywords
        assert "position" in tool.keywords

    def test_move_tool_is_tool_base(self):
        """Move 工具继承自 ToolBase"""
        from agents.execution.tools.move_tool import MoveTool
        from agents.execution.tools.base import ToolBase

        assert issubclass(MoveTool, ToolBase)


class TestMoveToolIntegration:
    """Move 工具与工具框架的集成"""

    @pytest.mark.asyncio
    async def test_move_with_tool_registry(self):
        """Move 工具可以注册到 ToolRegistry"""
        from agents.execution.tools.move_tool import MoveTool
        from agents.execution.tools.registry import ToolRegistry

        registry = ToolRegistry()
        move = MoveTool()
        registry.register("move", move)

        retrieved = registry.get("move")
        assert retrieved is move

    @pytest.mark.asyncio
    async def test_move_with_strategy_selector(self):
        """Move 工具可以通过 StrategySelector 选择"""
        from agents.execution.tools.move_tool import MoveTool
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.strategy import StrategySelector

        registry = ToolRegistry()
        move = MoveTool()
        registry.register("move", move)

        selector = StrategySelector(registry)

        # 通过关键词选择
        tool = selector.find_tool_by_keyword("position")
        assert tool is move

        # 为任务排名
        ranked = selector.rank_tools_for_task("move to position")
        assert len(ranked) > 0
        assert ranked[0] is move
