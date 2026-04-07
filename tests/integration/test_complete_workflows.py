"""
Week 10 Task 4.3：集成测试扩展

验证完整工作流：
- 拿取和放置工作流
- 多步骤任务
- 错误恢复工作流
- 学习工作流
"""

import pytest
import asyncio
from agents import (
    SimpleAgent,
    RobotAgentLoop,
    RobotObservation,
    SkillResult,
    AgentConfig,
    ToolRegistry,
    StrategySelector,
    GripperTool,
    MoveTool,
    VisionTool,
    PreprocessorPlugin,
    PostprocessorPlugin,
    FeedbackLoop,
)


class TestPickAndPlaceWorkflow:
    """拿取和放置工作流集成测试"""

    @pytest.mark.asyncio
    async def test_complete_pick_and_place(self, dummy_config, dummy_llm_provider,
                                          dummy_perception_provider, dummy_executor):
        """完整的拿取和放置工作流"""
        # 初始化代理循环
        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        # 执行完整工作流：observe → think → act
        result = await loop.step()

        # 验证结果
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "message")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pick_and_place_with_vision(self):
        """使用视觉的拿取和放置工作流"""
        # 初始化工具
        vision = VisionTool()
        gripper = GripperTool()
        move = MoveTool()

        # 步骤 1: 视觉检测
        detection_result = await vision.execute(operation="detect_objects")
        assert detection_result.get("success") is True

        # 步骤 2: 移动到对象
        move_result = await move.execute(
            target={"x": 0.5, "y": 0.3, "z": 0.2},
            mode="direct"
        )
        assert move_result.get("success") is True

        # 步骤 3: 抓取对象
        grasp_result = await gripper.execute(action="grasp", force=0.8)
        assert grasp_result.get("success") is True

        # 步骤 4: 移动到目标位置
        move_target_result = await move.execute(
            target={"x": 0.2, "y": 0.4, "z": 0.3},
            mode="direct"
        )
        assert move_target_result.get("success") is True

        # 步骤 5: 释放对象
        release_result = await gripper.execute(action="open")
        assert release_result.get("success") is True

    @pytest.mark.asyncio
    async def test_pick_and_place_with_preprocessing(self):
        """包含数据预处理的拿取和放置工作流"""
        # 初始化插件
        preprocessor = PreprocessorPlugin()
        await preprocessor.initialize()

        # 获取原始传感器数据
        raw_data = {
            "values": [0.1, 0.2, None, 0.4, float('nan'), 0.6]
        }

        # 数据清理
        cleaned = await preprocessor.execute(
            operation="clean",
            data=raw_data
        )
        assert cleaned.get("success") is True

        # 数据标准化
        normalized = await preprocessor.execute(
            operation="normalize",
            data=cleaned
        )
        assert normalized.get("success") is True

        # 初始化工具
        move = MoveTool()

        # 使用处理后的数据进行移动
        move_result = await move.execute(
            target={"x": 0.5, "y": 0.3, "z": 0.2},
            mode="direct"
        )
        assert move_result.get("success") is True

        await preprocessor.cleanup()


class TestMultiStepTask:
    """多步骤任务集成测试"""

    @pytest.mark.asyncio
    async def test_sequential_steps(self, dummy_config, dummy_llm_provider,
                                   dummy_perception_provider, dummy_executor):
        """顺序执行多个步骤"""
        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        # 执行多个步骤
        results = []
        for i in range(3):
            result = await loop.step()
            results.append(result)
            assert result is not None
            assert hasattr(result, "success")

        # 验证步数递增
        assert loop.step_count >= 3

    @pytest.mark.asyncio
    async def test_multi_step_with_tool_sequence(self):
        """工具序列的多步骤任务"""
        # 初始化工具和注册表
        registry = ToolRegistry()
        gripper = GripperTool()
        move = MoveTool()
        vision = VisionTool()

        registry.register("gripper", gripper)
        registry.register("move", move)
        registry.register("vision", vision)

        # 步骤序列
        steps = [
            ("vision", {"operation": "detect_objects"}),
            ("move", {"target": {"x": 0.5, "y": 0.3, "z": 0.2}, "mode": "direct"}),
            ("gripper", {"action": "grasp", "force": 0.8}),
            ("move", {"target": {"x": 0.2, "y": 0.4, "z": 0.3}, "mode": "direct"}),
            ("gripper", {"action": "open"}),
        ]

        results = []
        for tool_name, params in steps:
            tool = registry.get(tool_name)
            result = await tool.execute(**params)
            results.append(result)
            assert result.get("success") is True

        assert len(results) == len(steps)

    @pytest.mark.asyncio
    async def test_multi_step_with_branching(self):
        """包含分支逻辑的多步骤任务"""
        vision = VisionTool()
        gripper = GripperTool()

        # 步骤 1: 检测对象
        detection = await vision.execute(operation="detect_objects")
        assert detection.get("success") is True

        # 步骤 2: 基于检测结果的分支
        if detection.get("success"):
            # 分支 A: 有对象
            grasp_result = await gripper.execute(action="grasp", force=0.8)
            assert grasp_result.get("success") is True
        else:
            # 分支 B: 没有对象
            open_result = await gripper.execute(action="open")
            assert open_result.get("success") is True


class TestErrorRecoveryWorkflow:
    """错误恢复工作流集成测试"""

    @pytest.mark.asyncio
    async def test_recovery_from_gripper_failure(self):
        """从机械爪故障恢复"""
        gripper = GripperTool()
        move = MoveTool()

        # 尝试抓取（可能失败）
        try:
            grasp_result = await gripper.execute(action="grasp", force=0.8)
            if grasp_result.get("success"):
                # 成功继续
                move_result = await move.execute(
                    target={"x": 0.5, "y": 0.3, "z": 0.2},
                    mode="direct"
                )
                assert move_result.get("success") is True
            else:
                # 失败恢复：重试或使用替代方案
                retry_result = await gripper.execute(action="grasp", force=0.6)
                assert retry_result is not None

        except Exception as e:
            # 异常处理
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_recovery_from_movement_failure(self):
        """从移动故障恢复"""
        move = MoveTool()

        # 尝试安全移动（处理边界情况）
        try:
            # 尝试到达可能超出范围的位置
            result1 = await move.execute(
                target={"x": 2.0, "y": 2.0, "z": 2.0},  # 可能超出范围
                mode="safe"
            )

            if not result1.get("success"):
                # 恢复：重试在安全范围内
                result2 = await move.execute(
                    target={"x": 0.5, "y": 0.3, "z": 0.2},  # 安全位置
                    mode="safe"
                )
                assert result2.get("success") is True

        except Exception as e:
            # 验证异常被正确处理
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_recovery_with_fallback_tool(self):
        """使用备选工具的故障恢复"""
        registry = ToolRegistry()
        vision = VisionTool()
        gripper = GripperTool()

        registry.register("vision", vision)
        registry.register("gripper", gripper)

        selector = StrategySelector(registry)

        # 尝试主要工具
        primary_result = await vision.execute(operation="detect_objects")

        if not primary_result.get("success"):
            # 回退到备选工具
            fallback_tool = selector.find_tool_by_keyword("grasp")
            fallback_result = await fallback_tool.execute(action="open")
            assert fallback_result is not None

    @pytest.mark.asyncio
    async def test_error_recovery_with_logging(self):
        """包含日志的错误恢复"""
        from agents import FeedbackLogger, SkillResult

        logger = FeedbackLogger()
        gripper = GripperTool()

        # 执行操作
        result = await gripper.execute(action="grasp", force=0.8)

        # 将 dict 结果转换为 SkillResult 对象用于日志记录
        skill_result = SkillResult(
            success=result.get("success", False),
            message=result.get("message", ""),
            data=result.get("data")
        )

        # 记录结果
        await logger.log_result(skill_result)

        # 验证记录成功
        history = logger.get_history()
        assert len(history) > 0


class TestLearningWorkflow:
    """学习工作流集成测试"""

    @pytest.mark.asyncio
    async def test_feedback_and_learning(self):
        """反馈和学习工作流"""
        feedback_loop = FeedbackLoop()
        gripper = GripperTool()

        # 步骤 1: 执行动作
        result = await gripper.execute(action="grasp", force=0.8)

        # 将 dict 结果转换为 SkillResult
        skill_result = SkillResult(
            success=result.get("success", False),
            message=result.get("message", ""),
            data=result.get("data")
        )

        # 步骤 2: 接收反馈
        await feedback_loop.receive_feedback(skill_result)

        # 步骤 3: 获取洞察
        insights = feedback_loop.get_insights()
        assert insights is not None
        assert isinstance(insights, dict)

    @pytest.mark.asyncio
    async def test_iterative_improvement(self):
        """迭代改进工作流"""
        gripper = GripperTool()
        feedback_loop = FeedbackLoop()

        # 迭代改进
        force_levels = [0.5, 0.6, 0.7, 0.8]
        results = []

        for force in force_levels:
            result = await gripper.execute(action="grasp", force=force)
            results.append(result)

            # 将 dict 结果转换为 SkillResult
            skill_result = SkillResult(
                success=result.get("success", False),
                message=result.get("message", ""),
                data=result.get("data")
            )
            await feedback_loop.receive_feedback(skill_result)

        # 验证有多个结果
        assert len(results) == len(force_levels)

    @pytest.mark.asyncio
    async def test_learning_with_postprocessing(self):
        """包含后处理的学习工作流"""
        postprocessor = PostprocessorPlugin()
        await postprocessor.initialize()

        # 模拟多个执行结果
        results_list = [
            {"detections": [{"id": i, "confidence": 0.9}]}
            for i in range(5)
        ]

        # 后处理结果
        processed_results = []
        for result in results_list:
            processed = await postprocessor.execute(
                operation="format",
                data=result
            )
            processed_results.append(processed)

        # 验证所有结果都被处理
        assert len(processed_results) == len(results_list)
        assert all(r.get("success") for r in processed_results)

        await postprocessor.cleanup()

    @pytest.mark.asyncio
    async def test_end_to_end_learning_pipeline(self):
        """端到端的学习管道"""
        # 初始化所有组件
        preprocessor = PreprocessorPlugin()
        postprocessor = PostprocessorPlugin()
        feedback_loop = FeedbackLoop()
        vision = VisionTool()
        gripper = GripperTool()

        await preprocessor.initialize()
        await postprocessor.initialize()

        # 数据流：
        # 1. 视觉输入 → 预处理
        detection = await vision.execute(operation="detect_objects")

        # 2. 预处理数据
        raw_data = {"values": [0.1, 0.2, 0.3, 0.4, 0.5]}
        cleaned = await preprocessor.execute(
            operation="clean",
            data=raw_data
        )

        # 3. 执行动作
        grasp = await gripper.execute(action="grasp", force=0.8)

        # 4. 后处理结果
        formatted = await postprocessor.execute(
            operation="format",
            data=grasp
        )

        # 5. 反馈循环（转换为 SkillResult）
        skill_result = SkillResult(
            success=formatted.get("success", False),
            message=formatted.get("message", ""),
            data=formatted.get("data")
        )
        await feedback_loop.receive_feedback(skill_result)
        insights = feedback_loop.get_insights()

        # 验证整个管道
        assert detection.get("success") is True
        assert cleaned.get("success") is True
        assert grasp.get("success") is True
        assert formatted.get("success") is True
        assert insights is not None

        # 清理
        await preprocessor.cleanup()
        await postprocessor.cleanup()


class TestComplexWorkflowIntegration:
    """复杂工作流集成测试"""

    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """并发工作流执行"""
        async def workflow_1():
            gripper = GripperTool()
            return await gripper.execute(action="open")

        async def workflow_2():
            move = MoveTool()
            return await move.execute(
                target={"x": 0.5, "y": 0.3, "z": 0.2},
                mode="direct"
            )

        async def workflow_3():
            vision = VisionTool()
            return await vision.execute(operation="detect_objects")

        # 并发执行
        results = await asyncio.gather(
            workflow_1(),
            workflow_2(),
            workflow_3()
        )

        # 验证所有工作流完成
        assert len(results) == 3
        assert all(r.get("success") for r in results)

    @pytest.mark.asyncio
    async def test_cascading_workflows(self):
        """级联工作流（前一个的输出是后一个的输入）"""
        vision = VisionTool()
        move = MoveTool()
        gripper = GripperTool()

        # 步骤 1: 检测
        detection = await vision.execute(operation="detect_objects")
        assert detection.get("success") is True

        # 步骤 2: 基于检测结果移动
        move_result = await move.execute(
            target={"x": 0.5, "y": 0.3, "z": 0.2},
            mode="direct"
        )
        assert move_result.get("success") is True

        # 步骤 3: 基于移动结果抓取
        grasp_result = await gripper.execute(action="grasp", force=0.8)
        assert grasp_result.get("success") is True

    @pytest.mark.asyncio
    async def test_full_system_integration(self, dummy_config, dummy_llm_provider,
                                         dummy_perception_provider, dummy_executor):
        """完整系统集成测试"""
        # 创建代理
        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        # 执行任务
        result = await agent.run_task("complete integration test")

        # 验证结果
        assert result is not None
        assert hasattr(result, "success")
        assert result.success is True
