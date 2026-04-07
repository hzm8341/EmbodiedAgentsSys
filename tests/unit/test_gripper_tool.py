"""
Week 8 Task 2.1：Gripper 控制工具测试

验证机械爪工具的功能：
- 打开/关闭动作
- 力度控制
- 位置反馈
- 错误处理
"""

import pytest


class TestGripperToolBasics:
    """Gripper 工具基本功能"""

    @pytest.mark.asyncio
    async def test_gripper_open(self):
        """机械爪可以打开"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()
        result = await tool.execute(action="open")

        assert result is not None
        assert result.get("action") == "open"
        assert result.get("success") is True
        assert "position" in result

    @pytest.mark.asyncio
    async def test_gripper_close(self):
        """机械爪可以关闭"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()
        result = await tool.execute(action="close")

        assert result is not None
        assert result.get("action") == "close"
        assert result.get("success") is True
        assert "position" in result

    @pytest.mark.asyncio
    async def test_gripper_grasp_force(self):
        """机械爪支持力度控制"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()

        # 轻力度抓取
        result = await tool.execute(action="grasp", force=0.5)
        assert result.get("force") == 0.5
        assert result.get("success") is True

        # 重力度抓取
        result = await tool.execute(action="grasp", force=1.0)
        assert result.get("force") == 1.0
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_gripper_position_feedback(self):
        """机械爪返回位置反馈"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()

        # 打开时的位置
        result = await tool.execute(action="open")
        open_position = result.get("position")
        assert open_position == 1.0, "Open position should be 1.0"

        # 关闭时的位置
        result = await tool.execute(action="close")
        close_position = result.get("position")
        assert close_position == 0.0, "Close position should be 0.0"


class TestGripperToolValidation:
    """Gripper 工具输入验证"""

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """拒绝无效的动作"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()

        with pytest.raises(ValueError):
            await tool.execute(action="invalid_action")

    @pytest.mark.asyncio
    async def test_force_out_of_range(self):
        """力度在 0-1 范围内"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()

        # 力度过大
        with pytest.raises(ValueError):
            await tool.execute(action="grasp", force=1.5)

        # 力度为负
        with pytest.raises(ValueError):
            await tool.execute(action="grasp", force=-0.5)


class TestGripperToolMetadata:
    """Gripper 工具元数据"""

    def test_gripper_tool_metadata(self):
        """Gripper 工具有正确的元数据"""
        from agents.execution.tools.gripper_tool import GripperTool

        tool = GripperTool()

        assert tool.name == "gripper"
        assert tool.description is not None
        assert len(tool.description) > 0
        assert hasattr(tool, "keywords")
        assert "gripper" in tool.keywords
        assert "grasp" in tool.keywords

    def test_gripper_tool_is_tool_base(self):
        """Gripper 工具继承自 ToolBase"""
        from agents.execution.tools.gripper_tool import GripperTool
        from agents.execution.tools.base import ToolBase

        assert issubclass(GripperTool, ToolBase)


class TestGripperToolIntegration:
    """Gripper 工具与工具框架的集成"""

    @pytest.mark.asyncio
    async def test_gripper_with_tool_registry(self):
        """Gripper 工具可以注册到 ToolRegistry"""
        from agents.execution.tools.gripper_tool import GripperTool
        from agents.execution.tools.registry import ToolRegistry

        registry = ToolRegistry()
        gripper = GripperTool()
        registry.register("gripper", gripper)

        retrieved = registry.get("gripper")
        assert retrieved is gripper

    @pytest.mark.asyncio
    async def test_gripper_with_strategy_selector(self):
        """Gripper 工具可以通过 StrategySelector 选择"""
        from agents.execution.tools.gripper_tool import GripperTool
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.strategy import StrategySelector

        registry = ToolRegistry()
        gripper = GripperTool()
        registry.register("gripper", gripper)

        selector = StrategySelector(registry)

        # 通过名称选择
        tool = selector.select_tool("gripper")
        assert tool is gripper

        # 通过关键词选择
        tool = selector.find_tool_by_keyword("grasp")
        assert tool is gripper

        # 为任务排名
        ranked = selector.rank_tools_for_task("grasp object")
        assert len(ranked) > 0
        assert ranked[0] is gripper
