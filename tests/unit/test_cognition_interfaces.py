"""
周 2 第 2.2 任务：测试认知层的接口定义

RED 阶段：编写失败的测试
目标：验证三层都实现了清晰的接口契约
"""

import pytest
from abc import ABC, abstractmethod


class TestLayerInterfaceContracts:
    """层级接口契约测试"""

    def test_planning_layer_is_abc(self):
        """PlanningLayer 应该是抽象基类"""
        from agents.cognition.planning import PlanningLayerBase

        assert issubclass(PlanningLayerBase, ABC)

    def test_reasoning_layer_is_abc(self):
        """ReasoningLayer 应该是抽象基类"""
        from agents.cognition.reasoning import ReasoningLayerBase

        assert issubclass(ReasoningLayerBase, ABC)

    def test_learning_layer_is_abc(self):
        """LearningLayer 应该是抽象基类"""
        from agents.cognition.learning import LearningLayerBase

        assert issubclass(LearningLayerBase, ABC)

    def test_planning_layer_has_required_methods(self):
        """PlanningLayer 应该定义必需的方法"""
        from agents.cognition.planning import PlanningLayerBase

        # 检查抽象方法
        assert hasattr(PlanningLayerBase, "generate_plan")

    def test_reasoning_layer_has_required_methods(self):
        """ReasoningLayer 应该定义必需的方法"""
        from agents.cognition.reasoning import ReasoningLayerBase

        assert hasattr(ReasoningLayerBase, "generate_action")

    def test_learning_layer_has_required_methods(self):
        """LearningLayer 应该定义必需的方法"""
        from agents.cognition.learning import LearningLayerBase

        assert hasattr(LearningLayerBase, "improve")


class TestPlanningLayerInterface:
    """规划层接口测试"""

    def test_default_planning_implementation_exists(self):
        """应该有默认的规划实现"""
        from agents.cognition.planning import DefaultPlanningLayer

        planner = DefaultPlanningLayer()
        assert planner is not None

    def test_default_planning_is_subclass_of_base(self):
        """默认实现应该继承基类"""
        from agents.cognition.planning import (
            DefaultPlanningLayer,
            PlanningLayerBase,
        )

        assert issubclass(DefaultPlanningLayer, PlanningLayerBase)

    @pytest.mark.asyncio
    async def test_planning_generate_plan_signature(self):
        """generate_plan 应该有正确的签名"""
        from agents.cognition.planning import DefaultPlanningLayer

        planner = DefaultPlanningLayer()

        # 应该接受字符串任务
        result = await planner.generate_plan("test task")

        # 应该返回字典
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_planning_layer_custom_implementation(self):
        """可以自定义规划层实现"""
        from agents.cognition.planning import PlanningLayerBase

        class CustomPlanner(PlanningLayerBase):
            async def generate_plan(self, task: str) -> dict:
                return {"task": task, "custom": True}

        planner = CustomPlanner()
        result = await planner.generate_plan("custom task")

        assert result["custom"] is True


class TestReasoningLayerInterface:
    """推理层接口测试"""

    def test_default_reasoning_implementation_exists(self):
        """应该有默认的推理实现"""
        from agents.cognition.reasoning import DefaultReasoningLayer

        reasoner = DefaultReasoningLayer()
        assert reasoner is not None

    def test_default_reasoning_is_subclass_of_base(self):
        """默认实现应该继承基类"""
        from agents.cognition.reasoning import (
            DefaultReasoningLayer,
            ReasoningLayerBase,
        )

        assert issubclass(DefaultReasoningLayer, ReasoningLayerBase)

    @pytest.mark.asyncio
    async def test_reasoning_generate_action_signature(self):
        """generate_action 应该有正确的签名"""
        from agents.cognition.reasoning import DefaultReasoningLayer
        from agents.core.types import RobotObservation

        reasoner = DefaultReasoningLayer()
        plan = {"task": "test"}
        observation = RobotObservation()

        # 应该接受计划和观察
        result = await reasoner.generate_action(plan, observation)

        # 应该返回字符串
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_reasoning_layer_custom_implementation(self):
        """可以自定义推理层实现"""
        from agents.cognition.reasoning import ReasoningLayerBase
        from agents.core.types import RobotObservation

        class CustomReasoner(ReasoningLayerBase):
            async def generate_action(self, plan: dict, observation) -> str:
                return "custom_action()"

        reasoner = CustomReasoner()
        result = await reasoner.generate_action({}, RobotObservation())

        assert result == "custom_action()"


class TestLearningLayerInterface:
    """学习层接口测试"""

    def test_default_learning_implementation_exists(self):
        """应该有默认的学习实现"""
        from agents.cognition.learning import DefaultLearningLayer

        learner = DefaultLearningLayer()
        assert learner is not None

    def test_default_learning_is_subclass_of_base(self):
        """默认实现应该继承基类"""
        from agents.cognition.learning import (
            DefaultLearningLayer,
            LearningLayerBase,
        )

        assert issubclass(DefaultLearningLayer, LearningLayerBase)

    @pytest.mark.asyncio
    async def test_learning_improve_signature(self):
        """improve 应该有正确的签名"""
        from agents.cognition.learning import DefaultLearningLayer

        learner = DefaultLearningLayer()
        action = "test_action()"
        feedback = {"success": False}

        # 应该接受动作和反馈
        result = await learner.improve(action, feedback)

        # 应该返回字符串
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_learning_layer_custom_implementation(self):
        """可以自定义学习层实现"""
        from agents.cognition.learning import LearningLayerBase

        class CustomLearner(LearningLayerBase):
            async def improve(self, action: str, feedback: dict) -> str:
                return f"improved_{action}"

        learner = CustomLearner()
        result = await learner.improve("action", {"success": False})

        assert result == "improved_action"


class TestCognitionEngineWithCustomLayers:
    """使用自定义层的认知引擎测试"""

    @pytest.mark.asyncio
    async def test_cognition_engine_accepts_custom_planning_layer(self, dummy_config):
        """CognitionEngine 应该接受自定义规划层"""
        from agents.cognition.engine import CognitionEngine
        from agents.cognition.planning import PlanningLayerBase

        class CustomPlanner(PlanningLayerBase):
            async def generate_plan(self, task: str) -> dict:
                return {"custom_plan": True, "task": task}

        engine = CognitionEngine(dummy_config)
        engine.planning = CustomPlanner()

        result = await engine.think(task="test")

        assert result["plan"]["custom_plan"] is True

    @pytest.mark.asyncio
    async def test_cognition_engine_accepts_custom_reasoning_layer(self, dummy_config):
        """CognitionEngine 应该接受自定义推理层"""
        from agents.cognition.engine import CognitionEngine
        from agents.cognition.reasoning import ReasoningLayerBase
        from agents.core.types import RobotObservation

        class CustomReasoner(ReasoningLayerBase):
            async def generate_action(self, plan: dict, observation) -> str:
                return "# custom reasoning"

        engine = CognitionEngine(dummy_config)
        engine.reasoning = CustomReasoner()

        result = await engine.think(task="test")

        assert "custom reasoning" in result["action"]

    @pytest.mark.asyncio
    async def test_cognition_engine_accepts_custom_learning_layer(self, dummy_config):
        """CognitionEngine 应该接受自定义学习层"""
        from agents.cognition.engine import CognitionEngine
        from agents.cognition.learning import LearningLayerBase
        from agents.core.types import SkillResult

        class CustomLearner(LearningLayerBase):
            async def improve(self, action: str, feedback: dict) -> str:
                return f"# custom improved: {action}"

        engine = CognitionEngine(dummy_config)
        engine.learning = CustomLearner()

        await engine.think(task="test")
        result = await engine.provide_feedback(
            SkillResult(success=False, message="test")
        )

        assert "custom improved" in result


class TestLayerComposition:
    """层级组合测试"""

    @pytest.mark.asyncio
    async def test_layers_can_be_composed_in_engine(self, dummy_config):
        """应该能在引擎中灵活组合层"""
        from agents.cognition.engine import CognitionEngine
        from agents.cognition.planning import DefaultPlanningLayer
        from agents.cognition.reasoning import DefaultReasoningLayer
        from agents.cognition.learning import DefaultLearningLayer

        engine = CognitionEngine(dummy_config)

        # 替换所有默认层
        engine.planning = DefaultPlanningLayer()
        engine.reasoning = DefaultReasoningLayer()
        engine.learning = DefaultLearningLayer()

        # 应该能正常工作
        result = await engine.think(task="test")
        assert result is not None

    @pytest.mark.asyncio
    async def test_layer_independence(self, dummy_config):
        """层应该是独立的，可以单独使用"""
        from agents.cognition.planning import DefaultPlanningLayer
        from agents.cognition.reasoning import DefaultReasoningLayer
        from agents.cognition.learning import DefaultLearningLayer
        from agents.core.types import RobotObservation

        # 单独使用规划层
        planner = DefaultPlanningLayer()
        plan = await planner.generate_plan("task")
        assert plan is not None

        # 单独使用推理层
        reasoner = DefaultReasoningLayer()
        action = await reasoner.generate_action(plan, RobotObservation())
        assert action is not None

        # 单独使用学习层
        learner = DefaultLearningLayer()
        improved = await learner.improve(action, {"success": False})
        assert improved is not None
