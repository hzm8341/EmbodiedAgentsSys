"""
周 4 任务：工具层测试

RED 阶段：编写工具层的失败测试
目标：验证工具调用和策略选择
"""

import pytest


class TestToolFramework:
    """工具框架测试"""

    def test_tool_base_exists(self):
        """工具基类存在"""
        from agents.execution.tools.base import ToolBase

        assert ToolBase is not None

    def test_tool_registry_exists(self):
        """工具注册表存在"""
        from agents.execution.tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert registry is not None

    def test_strategy_selector_exists(self):
        """策略选择器存在"""
        from agents.execution.tools.strategy import StrategySelector

        selector = StrategySelector()
        assert selector is not None


class TestToolBase:
    """工具基类测试"""

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """工具可以执行"""
        from agents.execution.tools.base import ToolBase

        class GripperTool(ToolBase):
            name = "gripper"
            description = "Control gripper"

            async def execute(self, action: str) -> dict:
                return {"success": True, "action": action}

        tool = GripperTool()
        result = await tool.execute("open")

        assert result["success"] is True

    def test_tool_metadata(self):
        """工具有元数据"""
        from agents.execution.tools.base import ToolBase

        class MoveTool(ToolBase):
            name = "move"
            description = "Move robot"
            category = "motion"

            async def execute(self, *args, **kwargs):
                return {"moved": True}

        tool = MoveTool()
        assert tool.name == "move"
        assert tool.description == "Move robot"


class TestToolRegistry:
    """工具注册表测试"""

    def test_register_tool(self):
        """可以注册工具"""
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.base import ToolBase

        class TestTool(ToolBase):
            name = "test"
            description = "Test tool"

            async def execute(self, *args, **kwargs):
                return {"test": True}

        registry = ToolRegistry()
        tool = TestTool()
        registry.register(tool.name, tool)

        assert registry.get("test") is not None

    def test_list_tools(self):
        """可以列出工具"""
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.base import ToolBase

        class Tool1(ToolBase):
            name = "tool1"
            description = "Tool 1"

            async def execute(self, *args, **kwargs):
                return {}

        class Tool2(ToolBase):
            name = "tool2"
            description = "Tool 2"

            async def execute(self, *args, **kwargs):
                return {}

        registry = ToolRegistry()
        registry.register("tool1", Tool1())
        registry.register("tool2", Tool2())

        tools = registry.list_tools()
        assert len(tools) == 2


class TestStrategySelector:
    """策略选择器测试"""

    def test_selector_selects_tool(self):
        """选择器可以选择工具"""
        from agents.execution.tools.strategy import StrategySelector
        from agents.execution.tools.base import ToolBase
        from agents.execution.tools.registry import ToolRegistry

        class GripperTool(ToolBase):
            name = "gripper"
            description = "Gripper control"

            async def execute(self, *args, **kwargs):
                return {"action": "grip"}

        registry = ToolRegistry()
        registry.register("gripper", GripperTool())

        selector = StrategySelector(registry)
        selected = selector.select_tool("gripper")

        assert selected is not None
        assert selected.name == "gripper"

    @pytest.mark.asyncio
    async def test_selector_matches_task_to_tool(self):
        """选择器可以匹配任务到工具"""
        from agents.execution.tools.strategy import StrategySelector
        from agents.execution.tools.base import ToolBase
        from agents.execution.tools.registry import ToolRegistry

        class PickTool(ToolBase):
            name = "pick"
            description = "Pick objects"
            keywords = ["pick", "grasp", "grab"]

            async def execute(self, *args, **kwargs):
                return {"action": "pick"}

        registry = ToolRegistry()
        registry.register("pick", PickTool())

        selector = StrategySelector(registry)

        # 应该能根据关键词找到工具
        matched = selector.find_tool_by_keyword("pick")
        assert matched is not None

    @pytest.mark.asyncio
    async def test_selector_ranks_tools(self):
        """选择器可以对工具进行排名"""
        from agents.execution.tools.strategy import StrategySelector
        from agents.execution.tools.base import ToolBase
        from agents.execution.tools.registry import ToolRegistry

        class Tool1(ToolBase):
            name = "tool1"
            description = "First tool"

            async def execute(self, *args, **kwargs):
                return {}

        class Tool2(ToolBase):
            name = "tool2"
            description = "Second tool"

            async def execute(self, *args, **kwargs):
                return {}

        registry = ToolRegistry()
        registry.register("tool1", Tool1())
        registry.register("tool2", Tool2())

        selector = StrategySelector(registry)
        ranked = selector.rank_tools_for_task("any task")

        assert len(ranked) > 0


class TestToolExecution:
    """工具执行测试"""

    @pytest.mark.asyncio
    async def test_execute_tool_with_registry(self):
        """可以通过注册表执行工具"""
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.base import ToolBase

        class ActionTool(ToolBase):
            name = "action"
            description = "Execute action"

            async def execute(self, cmd: str) -> dict:
                return {"executed": cmd}

        registry = ToolRegistry()
        tool = ActionTool()
        registry.register("action", tool)

        retrieved = registry.get("action")
        result = await retrieved.execute("test_cmd")

        assert result["executed"] == "test_cmd"

    @pytest.mark.asyncio
    async def test_tool_composition(self):
        """工具可以组合"""
        from agents.execution.tools.base import ToolBase

        class StepTool(ToolBase):
            name = "step"
            description = "Single step"

            async def execute(self, distance: float) -> dict:
                return {"moved": distance}

        class SequenceTool(ToolBase):
            name = "sequence"
            description = "Execute sequence"

            async def execute(self, steps: list) -> dict:
                step_tool = StepTool()
                results = []
                for step in steps:
                    result = await step_tool.execute(step)
                    results.append(result)
                return {"sequence": results}

        seq_tool = SequenceTool()
        result = await seq_tool.execute([1.0, 2.0, 3.0])

        assert len(result["sequence"]) == 3


class TestToolIntegration:
    """工具集成测试"""

    @pytest.mark.asyncio
    async def test_full_tool_workflow(self):
        """完整的工具工作流"""
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.strategy import StrategySelector
        from agents.execution.tools.base import ToolBase

        class GraspTool(ToolBase):
            name = "grasp"
            description = "Grasp object"
            keywords = ["pick", "grasp", "grab"]

            async def execute(self, target: str) -> dict:
                return {"grasped": target}

        registry = ToolRegistry()
        registry.register("grasp", GraspTool())

        selector = StrategySelector(registry)

        # 根据任务描述找工具
        tool = selector.find_tool_by_keyword("pick")

        # 执行工具
        result = await tool.execute(target="cube")

        assert result["grasped"] == "cube"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """工具可以处理错误"""
        from agents.execution.tools.base import ToolBase

        class SafeTool(ToolBase):
            name = "safe"
            description = "Safe execution"

            async def execute(self, *args, **kwargs) -> dict:
                try:
                    # 模拟可能失败的操作
                    if kwargs.get("fail"):
                        raise ValueError("Operation failed")
                    return {"success": True}
                except Exception as e:
                    return {"success": False, "error": str(e)}

        tool = SafeTool()

        # 成功情况
        result1 = await tool.execute()
        assert result1["success"] is True

        # 失败情况
        result2 = await tool.execute(fail=True)
        assert result2["success"] is False
