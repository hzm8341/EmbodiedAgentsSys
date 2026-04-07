"""
周 2 第 2.3 任务：测试反馈循环子系统

RED 阶段：编写失败的测试
目标：验证独立的反馈循环系统
"""

import pytest


class TestFeedbackLoopStructure:
    """反馈循环结构测试"""

    def test_feedback_loop_exists(self):
        """反馈循环存在且可以初始化"""
        from agents.feedback.loop import FeedbackLoop

        feedback_loop = FeedbackLoop()
        assert feedback_loop is not None

    def test_feedback_logger_exists(self):
        """反馈记录器存在"""
        from agents.feedback.logger import FeedbackLogger

        logger = FeedbackLogger()
        assert logger is not None

    def test_feedback_analyzer_exists(self):
        """反馈分析器存在"""
        from agents.feedback.analyzer import FeedbackAnalyzer

        analyzer = FeedbackAnalyzer()
        assert analyzer is not None


class TestFeedbackLogging:
    """反馈记录测试"""

    @pytest.mark.asyncio
    async def test_feedback_logger_records_result(self):
        """反馈记录器可以记录执行结果"""
        from agents.feedback.logger import FeedbackLogger
        from agents.core.types import SkillResult

        logger = FeedbackLogger()
        result = SkillResult(success=True, message="Task completed")

        await logger.log_result(result)

        # 应该有记录存储
        assert len(logger.history) > 0

    @pytest.mark.asyncio
    async def test_feedback_logger_tracks_history(self):
        """反馈记录器应该追踪历史"""
        from agents.feedback.logger import FeedbackLogger
        from agents.core.types import SkillResult

        logger = FeedbackLogger()

        # 记录多个结果
        for i in range(3):
            result = SkillResult(success=i % 2 == 0, message=f"Task {i}")
            await logger.log_result(result)

        # 应该追踪所有记录
        assert len(logger.history) == 3

    @pytest.mark.asyncio
    async def test_feedback_logger_stores_metadata(self):
        """反馈记录器应该存储元数据"""
        from agents.feedback.logger import FeedbackLogger
        from agents.core.types import SkillResult

        logger = FeedbackLogger()
        result = SkillResult(success=True, message="Test", data={"steps": 5})

        await logger.log_result(result)

        # 历史记录应该包含完整信息
        recorded = logger.history[0]
        assert recorded["success"] is True
        assert recorded["data"]["steps"] == 5


class TestFeedbackAnalysis:
    """反馈分析测试"""

    @pytest.mark.asyncio
    async def test_feedback_analyzer_analyzes_single_result(self):
        """反馈分析器可以分析单个结果"""
        from agents.feedback.analyzer import FeedbackAnalyzer
        from agents.core.types import SkillResult

        analyzer = FeedbackAnalyzer()
        result = SkillResult(success=True, message="Success")

        analysis = await analyzer.analyze(result)

        assert analysis is not None
        assert isinstance(analysis, dict)

    @pytest.mark.asyncio
    async def test_feedback_analyzer_computes_success_rate(self):
        """反馈分析器可以计算成功率"""
        from agents.feedback.analyzer import FeedbackAnalyzer
        from agents.core.types import SkillResult

        analyzer = FeedbackAnalyzer()

        # 记录混合的结果
        results = [
            SkillResult(success=True, message="Success 1"),
            SkillResult(success=False, message="Failure 1"),
            SkillResult(success=True, message="Success 2"),
        ]

        analysis_list = [await analyzer.analyze(r) for r in results]
        success_count = sum(1 for a in analysis_list if a.get("success"))

        assert success_count == 2

    @pytest.mark.asyncio
    async def test_feedback_analyzer_identifies_patterns(self):
        """反馈分析器可以识别模式"""
        from agents.feedback.analyzer import FeedbackAnalyzer
        from agents.core.types import SkillResult

        analyzer = FeedbackAnalyzer()

        # 多个相似的失败
        results = [
            SkillResult(success=False, message="Gripper failed"),
            SkillResult(success=False, message="Gripper timeout"),
            SkillResult(success=True, message="Success"),
        ]

        patterns = await analyzer.identify_patterns(results)

        assert patterns is not None
        assert isinstance(patterns, dict)


class TestFeedbackLoopIntegration:
    """反馈循环集成测试"""

    @pytest.mark.asyncio
    async def test_feedback_loop_receives_result(self):
        """反馈循环可以接收执行结果"""
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        loop = FeedbackLoop()
        result = SkillResult(success=True, message="Test completed")

        await loop.receive_feedback(result)

        # 应该被处理
        assert loop is not None

    @pytest.mark.asyncio
    async def test_feedback_loop_logs_and_analyzes(self):
        """反馈循环应该记录和分析反馈"""
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        loop = FeedbackLoop()

        # 提供多个反馈
        for i in range(3):
            result = SkillResult(
                success=i % 2 == 0,
                message=f"Task {i}",
                data={"iteration": i}
            )
            await loop.receive_feedback(result)

        # 应该有记录
        assert loop.get_feedback_count() >= 3

    @pytest.mark.asyncio
    async def test_feedback_loop_generates_insights(self):
        """反馈循环可以生成洞察"""
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        loop = FeedbackLoop()

        # 提供反馈
        for i in range(5):
            result = SkillResult(success=i < 3, message=f"Attempt {i}")
            await loop.receive_feedback(result)

        # 获取洞察
        insights = loop.get_insights()

        assert insights is not None
        assert isinstance(insights, dict)

    @pytest.mark.asyncio
    async def test_feedback_loop_supports_callbacks(self):
        """反馈循环支持回调函数"""
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        loop = FeedbackLoop()
        callback_called = False

        async def on_feedback(result):
            nonlocal callback_called
            callback_called = True

        loop.register_callback(on_feedback)

        result = SkillResult(success=True, message="Test")
        await loop.receive_feedback(result)

        assert callback_called is True


class TestFeedbackIntegrationWithCognition:
    """反馈与认知层集成测试"""

    @pytest.mark.asyncio
    async def test_cognition_engine_uses_feedback_loop(self, dummy_config):
        """认知引擎可以使用反馈循环"""
        from agents.cognition.engine import CognitionEngine
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        engine = CognitionEngine(dummy_config)
        feedback_loop = FeedbackLoop()

        # 执行认知步骤
        result = await engine.think(task="test")
        assert result is not None

        # 提供反馈
        skill_result = SkillResult(success=True, message="Action executed")
        await feedback_loop.receive_feedback(skill_result)

        assert feedback_loop.get_feedback_count() > 0

    @pytest.mark.asyncio
    async def test_feedback_improves_learning(self, dummy_config):
        """反馈应该改进学习层"""
        from agents.cognition.engine import CognitionEngine
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        engine = CognitionEngine(dummy_config)
        feedback_loop = FeedbackLoop()

        # 第一次思考
        result1 = await engine.think(task="task 1")
        assert result1 is not None

        # 提供失败反馈
        await feedback_loop.receive_feedback(
            SkillResult(success=False, message="Failed")
        )

        # 提供改进建议
        improvement = await engine.learning.improve(
            result1["action"],
            {"success": False, "error": "Gripper issue"}
        )
        assert improvement is not None

    @pytest.mark.asyncio
    async def test_feedback_loop_full_cycle(self, dummy_config):
        """完整的反馈循环：执行 -> 记录 -> 分析 -> 改进"""
        from agents.cognition.engine import CognitionEngine
        from agents.feedback.loop import FeedbackLoop
        from agents.core.types import SkillResult

        engine = CognitionEngine(dummy_config)
        feedback_loop = FeedbackLoop()

        # 执行多个循环
        for i in range(3):
            # 执行思考
            result = await engine.think(task=f"task_{i}")

            # 模拟执行和获得反馈
            success = i < 2  # 前两个成功，最后一个失败
            skill_result = SkillResult(
                success=success,
                message=f"Task {i} {'completed' if success else 'failed'}"
            )

            # 记录反馈
            await feedback_loop.receive_feedback(skill_result)

            # 如果失败，改进
            if not success:
                await engine.learning.improve(
                    result["action"],
                    {"success": False, "iteration": i}
                )

        # 获取洞察
        insights = feedback_loop.get_insights()
        assert insights is not None
