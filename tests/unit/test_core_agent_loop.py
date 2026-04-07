"""
Task 1.1: 测试 agents/core/agent_loop.py - 代理主循环

RED 阶段：编写失败的测试
目标：验证 RobotAgentLoop 的基本功能
"""

import pytest


class TestRobotAgentLoopInitialization:
    """RobotAgentLoop 初始化测试"""

    @pytest.mark.asyncio
    async def test_agent_loop_initialization(self, dummy_config, dummy_llm_provider,
                                              dummy_perception_provider, dummy_executor):
        """RobotAgentLoop 可以初始化"""
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        assert loop is not None
        assert loop.config == dummy_config
        assert loop.step_count == 0

    @pytest.mark.asyncio
    async def test_agent_loop_has_required_attributes(self, dummy_config, dummy_llm_provider,
                                                       dummy_perception_provider, dummy_executor):
        """RobotAgentLoop 应该有所需的属性"""
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        assert hasattr(loop, 'llm_provider')
        assert hasattr(loop, 'perception_provider')
        assert hasattr(loop, 'executor')
        assert hasattr(loop, 'config')
        assert hasattr(loop, 'step_count')


class TestRobotAgentLoopBasicCycle:
    """RobotAgentLoop 基本循环测试"""

    @pytest.mark.asyncio
    async def test_agent_loop_basic_cycle(self, dummy_config, dummy_llm_provider,
                                          dummy_perception_provider, dummy_executor):
        """代理循环可以执行基本的 observe-think-act 周期"""
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        # 执行一步
        result = await loop.step()

        # 验证所有提供者都被调用了
        assert dummy_perception_provider.called is True
        assert dummy_llm_provider.called is True
        assert dummy_executor.called is True

        # 验证返回结果
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_agent_loop_increments_step_count(self, dummy_config, dummy_llm_provider,
                                                     dummy_perception_provider, dummy_executor):
        """代理循环应该增加步数计数"""
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        assert loop.step_count == 0

        await loop.step()
        assert loop.step_count == 1

        await loop.step()
        assert loop.step_count == 2

    @pytest.mark.asyncio
    async def test_agent_loop_respects_max_steps(self, dummy_config, dummy_llm_provider,
                                                  dummy_perception_provider, dummy_executor):
        """代理循环应该遵守 max_steps 限制"""
        from agents.core.agent_loop import RobotAgentLoop

        dummy_config.max_steps = 2

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        # 执行两步
        result1 = await loop.step()
        assert result1.success is True

        result2 = await loop.step()
        assert result2.success is True

        # 第三步应该失败（超过 max_steps）
        result3 = await loop.step()
        assert result3.success is False
        assert "Max steps" in result3.message or "max" in result3.message.lower()


class TestRobotAgentLoopDataFlow:
    """RobotAgentLoop 数据流测试"""

    @pytest.mark.asyncio
    async def test_agent_loop_passes_observation_to_llm(self, dummy_config, dummy_llm_provider,
                                                         dummy_perception_provider, dummy_executor):
        """代理循环应该将观察传递给 LLM"""
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        await loop.step()

        # 验证 LLM 被调用（最好的话应该传递了观察）
        # 由于使用的是 mock，我们只能验证它被调用了
        assert dummy_llm_provider.generate_action.called

    @pytest.mark.asyncio
    async def test_agent_loop_passes_action_to_executor(self, dummy_config, dummy_llm_provider,
                                                         dummy_perception_provider, dummy_executor):
        """代理循环应该将动作传递给执行器"""
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        await loop.step()

        # 验证执行器被调用
        assert dummy_executor.execute.called


class TestRobotAgentLoopNoROS2:
    """验证 RobotAgentLoop 不依赖 ROS2"""

    @pytest.mark.asyncio
    async def test_agent_loop_no_ros2_dependency(self, dummy_config, dummy_llm_provider,
                                                  dummy_perception_provider, dummy_executor):
        """RobotAgentLoop 不应该依赖 ROS2"""
        import sys

        # 清除任何 ROS2 导入
        for key in list(sys.modules.keys()):
            if 'ros' in key.lower() or 'rclpy' in key.lower():
                del sys.modules[key]

        # 导入并创建循环
        from agents.core.agent_loop import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        # 验证 ROS2 没有被导入
        assert 'rclpy' not in sys.modules
        for key in sys.modules.keys():
            if 'rclpy' in key:
                pytest.fail(f"Found ROS2 import: {key}")

        # 循环应该可以初始化和运行
        assert loop is not None
        result = await loop.step()
        assert result is not None
