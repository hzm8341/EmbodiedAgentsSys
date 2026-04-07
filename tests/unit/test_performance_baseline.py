"""
任务 1.3：性能基线测试

建立性能基准线：
- 初始化时间：< 100ms
- 单步执行时间：< 1s
- 内存占用：< 50MB
- 并发性能：支持 10+ 并发任务
"""

import pytest
import time
import asyncio
import tracemalloc
from typing import List


class TestInitializationPerformance:
    """初始化性能测试"""

    def test_simple_agent_initialization_time(self):
        """SimpleAgent 初始化时间 < 100ms"""
        from agents import SimpleAgent

        start = time.time()
        agent = SimpleAgent.from_preset("default")
        elapsed = time.time() - start

        # 目标：< 100ms
        assert elapsed < 0.1, f"Initialization took {elapsed:.3f}s, expected < 0.1s"
        assert agent is not None

    def test_config_manager_load_time(self):
        """ConfigManager 加载时间 < 50ms"""
        from agents import ConfigManager

        start = time.time()
        config = ConfigManager.create(agent_name="perf_test")
        elapsed = time.time() - start

        # 目标：< 50ms
        assert elapsed < 0.05, f"Config load took {elapsed:.3f}s, expected < 0.05s"
        assert config is not None

    def test_cognition_engine_initialization(self):
        """CognitionEngine 初始化 < 50ms"""
        from agents import CognitionEngine, AgentConfig

        config = AgentConfig(agent_name="test")
        start = time.time()
        engine = CognitionEngine(config)
        elapsed = time.time() - start

        # 目标：< 50ms
        assert elapsed < 0.05, f"Engine init took {elapsed:.3f}s, expected < 0.05s"
        assert engine is not None


class TestExecutionPerformance:
    """执行性能测试"""

    @pytest.mark.asyncio
    async def test_single_step_execution_time(self, dummy_config, dummy_llm_provider,
                                              dummy_perception_provider, dummy_executor):
        """单步执行时间 < 1s"""
        from agents import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        start = time.time()
        result = await loop.step()
        elapsed = time.time() - start

        # 目标：< 1s
        assert elapsed < 1.0, f"Step execution took {elapsed:.3f}s, expected < 1s"
        assert result is not None

    @pytest.mark.asyncio
    async def test_task_execution_time(self, dummy_config, dummy_llm_provider,
                                       dummy_perception_provider, dummy_executor):
        """任务执行时间 < 5s（包括多步）"""
        from agents import SimpleAgent

        agent = SimpleAgent(
            config=dummy_config,
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor
        )

        start = time.time()
        result = await agent.run_task("test task")
        elapsed = time.time() - start

        # 目标：< 5s
        assert elapsed < 5.0, f"Task execution took {elapsed:.3f}s, expected < 5s"
        assert result is not None


class TestMemoryPerformance:
    """内存性能测试"""

    def test_simple_agent_memory_footprint(self):
        """SimpleAgent 内存占用 < 20MB"""
        from agents import SimpleAgent

        tracemalloc.start()
        agent = SimpleAgent.from_preset("default")
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 转换为 MB
        peak_mb = peak / 1024 / 1024

        # 目标：< 20MB
        assert peak_mb < 20, f"Memory peak: {peak_mb:.1f}MB, expected < 20MB"

    def test_cognition_engine_memory_footprint(self):
        """CognitionEngine 内存占用 < 10MB"""
        from agents import CognitionEngine, AgentConfig

        tracemalloc.start()
        config = AgentConfig(agent_name="test")
        engine = CognitionEngine(config)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 转换为 MB
        peak_mb = peak / 1024 / 1024

        # 目标：< 10MB
        assert peak_mb < 10, f"Memory peak: {peak_mb:.1f}MB, expected < 10MB"

    @pytest.mark.asyncio
    async def test_feedback_loop_memory_efficiency(self):
        """FeedbackLoop 不造成内存泄漏"""
        from agents import FeedbackLoop, SkillResult

        tracemalloc.start()

        # 创建并使用 feedback loop
        loop = FeedbackLoop()
        for i in range(10):
            result = SkillResult(success=True, message=f"test_{i}")
            await loop.receive_feedback(result)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024

        # 目标：< 5MB（10 个简单结果）
        assert peak_mb < 5, f"Memory peak: {peak_mb:.1f}MB, expected < 5MB"


class TestConcurrencyPerformance:
    """并发性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_agent_creation(self):
        """支持 10+ 并发代理创建"""
        from agents import SimpleAgent
        import asyncio

        async def create_agent(index: int) -> SimpleAgent:
            return SimpleAgent.from_preset("default")

        start = time.time()
        tasks = [create_agent(i) for i in range(15)]
        agents = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # 应该快速完成
        assert len(agents) == 15
        assert elapsed < 2.0, f"Creating 15 agents took {elapsed:.3f}s, expected < 2s"

    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, dummy_config, dummy_llm_provider,
                                             dummy_perception_provider, dummy_executor):
        """支持 10+ 并发任务"""
        from agents import SimpleAgent
        import asyncio

        async def execute_task(index: int):
            agent = SimpleAgent(
                config=dummy_config,
                llm_provider=dummy_llm_provider,
                perception_provider=dummy_perception_provider,
                executor=dummy_executor
            )
            return await agent.run_task(f"task_{index}")

        start = time.time()
        tasks = [execute_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # 应该支持并发
        assert len(results) == 10
        assert elapsed < 10.0, f"10 concurrent tasks took {elapsed:.3f}s, expected < 10s"


class TestPerformanceMetrics:
    """性能指标记录"""

    def test_collect_baseline_metrics(self, capsys):
        """收集性能基线数据"""
        import time
        from agents import SimpleAgent, ConfigManager

        metrics = {}

        # 记录配置加载时间
        start = time.time()
        config = ConfigManager.create(agent_name="baseline")
        metrics['config_load_ms'] = (time.time() - start) * 1000

        # 记录代理初始化时间
        start = time.time()
        agent = SimpleAgent.from_preset("default")
        metrics['agent_init_ms'] = (time.time() - start) * 1000

        # 打印指标
        print("\n" + "=" * 50)
        print("PERFORMANCE BASELINE METRICS")
        print("=" * 50)
        for key, value in metrics.items():
            print(f"  {key}: {value:.2f}ms")
        print("=" * 50)

        # 验证所有指标在目标范围内
        assert metrics['config_load_ms'] < 50, "Config load > 50ms"
        assert metrics['agent_init_ms'] < 100, "Agent init > 100ms"
