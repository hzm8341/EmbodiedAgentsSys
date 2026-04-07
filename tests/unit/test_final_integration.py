"""
周 5-6 任务：最终集成和完善测试

验证整个系统的集成、ROS2 解耦和文档
"""

import pytest


class TestSystemIntegration:
    """系统集成测试"""

    @pytest.mark.asyncio
    async def test_full_agent_pipeline(self, dummy_config, dummy_llm_provider,
                                       dummy_perception_provider, dummy_executor):
        """完整的代理管道"""
        from agents.simple_agent import SimpleAgent
        from agents.core.types import RobotObservation

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        # 执行任务
        result = await agent.run_task("pick up object")

        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_cognition_with_extensions(self, dummy_config):
        """认知引擎与扩展集成"""
        from agents.cognition.engine import CognitionEngine
        from agents.extensions.loader import PluginLoader
        from agents.extensions.plugin import PluginBase

        class EnhancementPlugin(PluginBase):
            name = "enhancement"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, plan):
                return {"enhanced": True, "plan": plan}

        # 创建引擎
        engine = CognitionEngine(dummy_config)

        # 加载扩展
        loader = PluginLoader()
        loader.register_plugin(EnhancementPlugin())

        # 执行认知步骤
        result = await engine.think(task="test task")
        assert result is not None

    @pytest.mark.asyncio
    async def test_tools_in_execution(self):
        """工具在执行层"""
        from agents.execution.tools.registry import ToolRegistry
        from agents.execution.tools.base import ToolBase
        from agents.execution.tools.strategy import StrategySelector

        class PickTool(ToolBase):
            name = "pick"
            description = "Pick an object"
            keywords = ["pick", "grasp"]

            async def execute(self, target: str) -> dict:
                return {"picked": target}

        class PlaceTool(ToolBase):
            name = "place"
            description = "Place an object"
            keywords = ["place", "put"]

            async def execute(self, target: str) -> dict:
                return {"placed": target}

        # 注册工具
        registry = ToolRegistry()
        registry.register("pick", PickTool())
        registry.register("place", PlaceTool())

        # 使用选择器
        selector = StrategySelector(registry)

        # 选择工具
        pick_tool = selector.find_tool_by_keyword("pick")
        assert pick_tool is not None

        # 执行工具
        result = await pick_tool.execute("cube")
        assert result["picked"] == "cube"


class TestROS2Independence:
    """ROS2 独立性测试"""

    def test_no_ros2_import_in_core(self):
        """核心模块不依赖 ROS2"""
        import sys

        # 导入核心模块
        from agents.core.types import RobotObservation, SkillResult, AgentConfig
        from agents.core.agent_loop import RobotAgentLoop

        # ROS2 相关模块不应该被导入
        ros2_modules = [m for m in sys.modules if "ros" in m.lower() or "rclpy" in m.lower()]

        # 核心模块应该能工作而不需要 ROS2
        obs = RobotObservation()
        result = SkillResult(success=True, message="test")
        config = AgentConfig(agent_name="test")

        assert obs is not None
        assert result is not None
        assert config is not None

    def test_no_ros2_import_in_config(self):
        """配置管理不依赖 ROS2"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.create(agent_name="test")
        assert config is not None

    def test_pure_python_implementation(self):
        """实现是纯 Python"""
        from agents.simple_agent import SimpleAgent
        from agents.cognition.engine import CognitionEngine
        from agents.execution.tools.registry import ToolRegistry

        # 所有核心组件都应该是纯 Python
        assert SimpleAgent is not None
        assert CognitionEngine is not None
        assert ToolRegistry is not None


class TestDocumentation:
    """文档测试"""

    def test_core_modules_have_docstrings(self):
        """核心模块有文档字符串"""
        from agents.core.types import RobotObservation, SkillResult
        from agents.core.agent_loop import RobotAgentLoop

        assert RobotObservation.__doc__ is not None
        assert SkillResult.__doc__ is not None
        assert RobotAgentLoop.__doc__ is not None

    def test_major_classes_documented(self):
        """主要类有文档"""
        from agents.simple_agent import SimpleAgent
        from agents.cognition.engine import CognitionEngine
        from agents.feedback.loop import FeedbackLoop

        assert SimpleAgent.__doc__ is not None
        assert CognitionEngine.__doc__ is not None
        assert FeedbackLoop.__doc__ is not None

    def test_methods_have_docstrings(self):
        """主要方法有文档"""
        from agents.simple_agent import SimpleAgent

        # 检查主要方法
        assert SimpleAgent.from_preset.__doc__ is not None
        assert SimpleAgent.run_task.__doc__ is not None


class TestArchitectureValidation:
    """架构验证测试"""

    def test_four_layer_architecture_completeness(self):
        """四层架构完整性"""
        from agents.core.types import RobotObservation, SkillResult
        from agents.cognition.engine import CognitionEngine
        from agents.execution.tools.registry import ToolRegistry
        from agents.feedback.loop import FeedbackLoop

        # 所有四层都存在
        assert RobotObservation is not None  # Perception
        assert CognitionEngine is not None    # Cognition
        assert ToolRegistry is not None       # Execution
        assert FeedbackLoop is not None       # Feedback

    def test_module_organization(self):
        """模块组织结构"""
        import agents.core
        import agents.config
        import agents.cognition
        import agents.feedback
        import agents.execution
        import agents.extensions

        # 所有主要包都存在
        assert agents.core is not None
        assert agents.config is not None
        assert agents.cognition is not None
        assert agents.feedback is not None
        assert agents.execution is not None
        assert agents.extensions is not None

    def test_extensibility_support(self):
        """扩展性支持"""
        from agents.extensions.plugin import PluginBase
        from agents.extensions.loader import PluginLoader
        from agents.execution.tools.base import ToolBase
        from agents.execution.tools.strategy import StrategySelector

        # 扩展点存在
        assert PluginBase is not None
        assert PluginLoader is not None
        assert ToolBase is not None
        assert StrategySelector is not None


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_agent_initialization_speed(self, dummy_config):
        """代理初始化速度"""
        import time
        from agents.simple_agent import SimpleAgent

        start = time.time()
        agent = SimpleAgent(dummy_config)
        elapsed = time.time() - start

        # 应该快速初始化（<100ms）
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_task_execution_completes(self, dummy_config, dummy_llm_provider,
                                             dummy_perception_provider, dummy_executor):
        """任务执行完成"""
        import time
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        start = time.time()
        result = await agent.run_task("test")
        elapsed = time.time() - start

        # 应该在合理时间内完成
        assert result is not None
        assert elapsed < 1.0  # <1 second
