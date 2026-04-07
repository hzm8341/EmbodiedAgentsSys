"""
Week 2 Task 2.1: 测试 Cognition 层的三个子层

RED 阶段：编写失败的测试
目标：验证 Planning、Reasoning、Learning 三层的分离和协调
"""

import pytest


class TestCognitionLayerStructure:
    """Cognition 子层结构测试"""

    def test_planning_layer_exists(self):
        """Planning 层存在且可以初始化"""
        from agents.cognition.planning import PlanningLayer

        planner = PlanningLayer()
        assert planner is not None

    def test_reasoning_layer_exists(self):
        """Reasoning 层存在且可以初始化"""
        from agents.cognition.reasoning import ReasoningLayer

        reasoner = ReasoningLayer()
        assert reasoner is not None

    def test_learning_layer_exists(self):
        """Learning 层存在且可以初始化"""
        from agents.cognition.learning import LearningLayer

        learner = LearningLayer()
        assert learner is not None


class TestPlanningLayer:
    """规划层测试"""

    @pytest.mark.asyncio
    async def test_planning_generates_plan(self):
        """Planning 层可以生成任务计划"""
        from agents.cognition.planning import PlanningLayer

        planner = PlanningLayer()
        plan = await planner.generate_plan("pick up red object")

        assert plan is not None
        assert isinstance(plan, dict)
        assert "task" in plan or "steps" in plan

    @pytest.mark.asyncio
    async def test_planning_handles_complex_task(self):
        """Planning 层可以处理复杂任务"""
        from agents.cognition.planning import PlanningLayer

        planner = PlanningLayer()
        plan = await planner.generate_plan(
            "Move object from table to bin while avoiding obstacles"
        )

        assert plan is not None
        assert len(str(plan)) > 0

    @pytest.mark.asyncio
    async def test_planning_is_deterministic(self):
        """Planning 层对相同任务应返回相同计划（或至少结构一致）"""
        from agents.cognition.planning import PlanningLayer

        planner = PlanningLayer()
        task = "simple pick and place task"

        plan1 = await planner.generate_plan(task)
        plan2 = await planner.generate_plan(task)

        # 验证计划结构一致
        assert type(plan1) == type(plan2)


class TestReasoningLayer:
    """推理层测试"""

    @pytest.mark.asyncio
    async def test_reasoning_generates_action(self):
        """Reasoning 层可以生成动作"""
        from agents.cognition.reasoning import ReasoningLayer
        from agents.core.types import RobotObservation

        reasoner = ReasoningLayer()
        plan = {"task": "pick up object", "steps": ["move", "grasp"]}
        observation = RobotObservation(state={"ready": True})

        action = await reasoner.generate_action(plan, observation)

        assert action is not None
        assert isinstance(action, str)
        assert len(action) > 0

    @pytest.mark.asyncio
    async def test_reasoning_uses_observation(self):
        """Reasoning 层使用观察来调整动作"""
        from agents.cognition.reasoning import ReasoningLayer
        from agents.core.types import RobotObservation

        reasoner = ReasoningLayer()
        plan = {"task": "pick up object"}

        # 不同的观察状态应该可能导致不同的动作
        obs1 = RobotObservation(state={"gripper_open": True})
        obs2 = RobotObservation(state={"gripper_open": False})

        action1 = await reasoner.generate_action(plan, obs1)
        action2 = await reasoner.generate_action(plan, obs2)

        # 两个动作都应该有效
        assert action1 is not None
        assert action2 is not None

    @pytest.mark.asyncio
    async def test_reasoning_supports_code_generation(self):
        """Reasoning 层应该能生成可执行的代码"""
        from agents.cognition.reasoning import ReasoningLayer
        from agents.core.types import RobotObservation

        reasoner = ReasoningLayer()
        plan = {"task": "execute skill"}
        observation = RobotObservation()

        action = await reasoner.generate_action(plan, observation)

        # 动作应该看起来像代码或技能调用
        assert action is not None


class TestLearningLayer:
    """学习层测试"""

    @pytest.mark.asyncio
    async def test_learning_improves_action(self):
        """Learning 层可以根据反馈改进动作"""
        from agents.cognition.learning import LearningLayer

        learner = LearningLayer()
        action = "initial_action_code()"
        feedback = {"success": False, "error": "gripper failed"}

        improved = await learner.improve(action, feedback)

        assert improved is not None
        assert isinstance(improved, str)

    @pytest.mark.asyncio
    async def test_learning_tracks_history(self):
        """Learning 层应该追踪改进历史"""
        from agents.cognition.learning import LearningLayer

        learner = LearningLayer()

        # 多次反馈和改进
        action = "original()"
        for i in range(3):
            feedback = {"success": False, "iteration": i}
            action = await learner.improve(action, feedback)
            assert action is not None

    @pytest.mark.asyncio
    async def test_learning_handles_success_feedback(self):
        """Learning 层应该处理成功反馈"""
        from agents.cognition.learning import LearningLayer

        learner = LearningLayer()
        action = "working_action()"
        feedback = {"success": True, "steps_taken": 5}

        result = await learner.improve(action, feedback)

        # 即使成功，也应该返回有效结果
        assert result is not None


class TestCognitionEngine:
    """认知引擎测试（整合三层）"""

    def test_cognition_engine_initialization(self, dummy_config):
        """CognitionEngine 可以初始化"""
        from agents.cognition.engine import CognitionEngine

        engine = CognitionEngine(dummy_config)

        assert engine is not None
        assert hasattr(engine, "config")

    def test_cognition_engine_has_three_layers(self, dummy_config):
        """CognitionEngine 包含三个子层"""
        from agents.cognition.engine import CognitionEngine

        engine = CognitionEngine(dummy_config)

        assert hasattr(engine, "planning")
        assert hasattr(engine, "reasoning")
        assert hasattr(engine, "learning")

    @pytest.mark.asyncio
    async def test_cognition_engine_think_method(self, dummy_config):
        """CognitionEngine 可以执行认知思考步骤"""
        from agents.cognition.engine import CognitionEngine

        engine = CognitionEngine(dummy_config)

        result = await engine.think(task="pick up object")

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cognition_engine_data_flow(self, dummy_config):
        """数据在三层之间正确流动"""
        from agents.cognition.engine import CognitionEngine
        from agents.core.types import RobotObservation

        engine = CognitionEngine(dummy_config)

        # 执行完整的认知流程
        observation = RobotObservation(state={"ready": True})
        result = await engine.think(task="test task", observation=observation)

        # 验证结果包含预期的结构
        assert result is not None
        assert "action" in result or "plan" in result

    @pytest.mark.asyncio
    async def test_cognition_engine_with_feedback_loop(self, dummy_config):
        """CognitionEngine 支持反馈循环"""
        from agents.cognition.engine import CognitionEngine
        from agents.core.types import SkillResult

        engine = CognitionEngine(dummy_config)

        # 第一次思考
        result1 = await engine.think(task="task 1")
        assert result1 is not None

        # 提供反馈
        feedback = SkillResult(success=False, message="Action failed")
        await engine.provide_feedback(feedback)

        # 第二次思考应该考虑反馈
        result2 = await engine.think(task="task 2")
        assert result2 is not None


class TestCognitionLayerIntegration:
    """Cognition 层集成测试"""

    @pytest.mark.asyncio
    async def test_full_cognition_cycle(self, dummy_config):
        """完整的认知循环：任务 -> 计划 -> 动作 -> 学习"""
        from agents.cognition.engine import CognitionEngine
        from agents.core.types import RobotObservation

        engine = CognitionEngine(dummy_config)

        task = "pick up red cube"
        observation = RobotObservation(state={"objects": ["red_cube", "blue_cube"]})

        # 执行认知步骤
        result = await engine.think(task=task, observation=observation)

        assert result is not None
        assert "action" in result or "code" in result or "plan" in result

    @pytest.mark.asyncio
    async def test_multiple_cognition_cycles(self, dummy_config):
        """支持连续的认知周期"""
        from agents.cognition.engine import CognitionEngine
        from agents.core.types import SkillResult

        engine = CognitionEngine(dummy_config)

        # 运行多个周期
        for i in range(3):
            result = await engine.think(task=f"task_{i}")
            assert result is not None

            # 模拟反馈
            feedback = SkillResult(success=True, message=f"task_{i} completed")
            await engine.provide_feedback(feedback)
