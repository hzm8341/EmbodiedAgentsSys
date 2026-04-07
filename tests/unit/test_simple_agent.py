"""
Task 1.3: 测试 agents/simple_agent.py - 快速开始接口

RED 阶段：编写失败的测试
目标：验证 SimpleAgent 的简化接口和易用性
"""

import pytest


class TestSimpleAgentInitialization:
    """SimpleAgent 初始化测试"""

    def test_simple_agent_from_preset(self):
        """可以从预设创建 SimpleAgent"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")
        assert agent is not None
        assert hasattr(agent, 'config')

    def test_simple_agent_from_preset_vla_plus(self):
        """可以从 vla_plus 预设创建 SimpleAgent"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("vla_plus")
        assert agent is not None

    def test_simple_agent_initialization_with_config(self, dummy_config):
        """可以用配置初始化 SimpleAgent"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent(dummy_config)
        assert agent is not None
        assert agent.config == dummy_config

    def test_simple_agent_initialization_with_providers(self, dummy_config, dummy_llm_provider,
                                                        dummy_perception_provider, dummy_executor):
        """可以用自定义提供者初始化 SimpleAgent"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        assert agent is not None
        assert agent.config == dummy_config


class TestSimpleAgentComposability:
    """SimpleAgent 组件化测试"""

    def test_simple_agent_has_all_subsystems(self):
        """SimpleAgent 应该封装所有必需的子系统"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")

        # 验证所有子系统都已初始化
        assert hasattr(agent, 'perception')
        assert hasattr(agent, 'cognition')
        assert hasattr(agent, 'execution')
        assert hasattr(agent, 'feedback')
        assert hasattr(agent, 'loop')

    def test_simple_agent_perception_is_callable(self):
        """SimpleAgent 的感知提供者应该可调用"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")
        assert agent.perception is not None
        assert hasattr(agent.perception, 'get_observation')

    def test_simple_agent_cognition_is_callable(self):
        """SimpleAgent 的认知引擎应该可调用"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")
        assert agent.cognition is not None

    def test_simple_agent_execution_is_callable(self):
        """SimpleAgent 的执行器应该可调用"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")
        assert agent.execution is not None
        assert hasattr(agent.execution, 'execute')

    def test_simple_agent_loop_is_initialized(self):
        """SimpleAgent 的循环应该被初始化"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")
        assert agent.loop is not None
        assert hasattr(agent.loop, 'step')


class TestSimpleAgentTaskExecution:
    """SimpleAgent 任务执行测试"""

    @pytest.mark.asyncio
    async def test_simple_agent_run_task(self, dummy_config, dummy_llm_provider,
                                         dummy_perception_provider, dummy_executor):
        """SimpleAgent 可以运行任务"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        result = await agent.run_task("test task")
        assert result is not None
        assert hasattr(result, 'success')

    @pytest.mark.asyncio
    async def test_simple_agent_run_task_returns_result(self, dummy_config, dummy_llm_provider,
                                                         dummy_perception_provider, dummy_executor):
        """SimpleAgent 的 run_task 应该返回结果对象"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        result = await agent.run_task("pick up the cube")
        assert result.success is True
        assert hasattr(result, 'message')

    @pytest.mark.asyncio
    async def test_simple_agent_multiple_tasks(self, dummy_config, dummy_llm_provider,
                                                dummy_perception_provider, dummy_executor):
        """SimpleAgent 可以连续运行多个任务"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        result1 = await agent.run_task("task 1")
        assert result1.success is True

        result2 = await agent.run_task("task 2")
        assert result2.success is True


class TestSimpleAgentEaseOfUse:
    """SimpleAgent 易用性测试"""

    def test_simple_agent_minimal_code(self):
        """SimpleAgent 应该支持最少代码初始化"""
        # 这测试 SimpleAgent 可以用最少的代码创建
        # 用户代码：
        # agent = SimpleAgent.from_preset("default")
        # await agent.run_task("task")

        from agents.simple_agent import SimpleAgent

        # 应该能用一行代码创建
        agent = SimpleAgent.from_preset("default")
        assert agent is not None

        # 应该能用一行代码运行
        assert hasattr(agent, 'run_task')

    def test_simple_agent_from_preset_is_idiomatic(self):
        """SimpleAgent.from_preset 应该是习惯用法"""
        from agents.simple_agent import SimpleAgent

        # 这应该是创建代理的标准方式
        agent = SimpleAgent.from_preset("default")

        # 不需要知道内部细节
        assert agent is not None

        # 不需要手动组装子系统
        assert agent.perception is not None
        assert agent.cognition is not None
        assert agent.execution is not None


class TestSimpleAgentPresets:
    """SimpleAgent 预设测试"""

    def test_simple_agent_supports_default_preset(self):
        """SimpleAgent 应该支持 default 预设"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")
        assert agent is not None

    def test_simple_agent_supports_vla_plus_preset(self):
        """SimpleAgent 应该支持 vla_plus 预设"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("vla_plus")
        assert agent is not None

    def test_simple_agent_supports_multiple_presets(self):
        """SimpleAgent 应该支持多个预设"""
        from agents.simple_agent import SimpleAgent

        presets = ["default", "vla_plus"]

        for preset in presets:
            try:
                agent = SimpleAgent.from_preset(preset)
                assert agent is not None
            except FileNotFoundError:
                # 某些预设可能不存在，这是可以接受的
                pass


class TestSimpleAgentIntegration:
    """SimpleAgent 集成测试"""

    @pytest.mark.asyncio
    async def test_simple_agent_full_workflow(self):
        """SimpleAgent 应该支持完整的工作流"""
        from agents.simple_agent import SimpleAgent

        # 创建代理
        agent = SimpleAgent.from_preset("default")

        # 运行任务
        result = await agent.run_task("example task")

        # 验证结果
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'message')

    def test_simple_agent_config_accessible(self):
        """SimpleAgent 的配置应该可访问"""
        from agents.simple_agent import SimpleAgent

        agent = SimpleAgent.from_preset("default")

        # 用户应该能访问配置
        assert agent.config is not None
        assert hasattr(agent.config, 'agent_name')
