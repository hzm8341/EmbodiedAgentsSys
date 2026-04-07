"""
Week 10 Task 4.1：性能优化测试

验证性能优化目标：
- 初始化时间 < 50ms
- 单步执行 < 100ms
- 内存占用 < 50MB
- 支持 10+ 并发任务
"""

import pytest
import time
import asyncio
import tracemalloc


class TestInitializationOptimization:
    """初始化性能优化"""

    def test_core_types_fast_init(self):
        """RobotObservation 快速初始化 < 10ms"""
        from agents.core.types import RobotObservation

        start = time.time()
        obs = RobotObservation()
        elapsed = (time.time() - start) * 1000

        assert elapsed < 10, f"Init took {elapsed:.2f}ms, expected < 10ms"

    def test_config_manager_init(self):
        """ConfigManager 快速初始化 < 20ms"""
        from agents.config.manager import ConfigManager

        start = time.time()
        config = ConfigManager.create(agent_name="test")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 20, f"Init took {elapsed:.2f}ms, expected < 20ms"

    def test_simple_agent_init(self):
        """SimpleAgent 初始化 < 50ms"""
        from agents import SimpleAgent

        start = time.time()
        agent = SimpleAgent.from_preset("default")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"Init took {elapsed:.2f}ms, expected < 50ms"


class TestExecutionOptimization:
    """执行性能优化"""

    @pytest.mark.asyncio
    async def test_single_step_latency(self, dummy_config, dummy_llm_provider,
                                       dummy_perception_provider, dummy_executor):
        """单步执行 < 100ms"""
        from agents import RobotAgentLoop

        loop = RobotAgentLoop(
            llm_provider=dummy_llm_provider,
            perception_provider=dummy_perception_provider,
            executor=dummy_executor,
            config=dummy_config
        )

        start = time.time()
        result = await loop.step()
        elapsed = (time.time() - start) * 1000

        assert elapsed < 100, f"Step took {elapsed:.2f}ms, expected < 100ms"
        assert result is not None

    @pytest.mark.asyncio
    async def test_tool_execution_speed(self):
        """工具执行快速"""
        from agents import GripperTool

        tool = GripperTool()

        start = time.time()
        result = await tool.execute(action="open")
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"Execution took {elapsed:.2f}ms, expected < 50ms"
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_plugin_execution_speed(self):
        """插件执行快速"""
        from agents import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        data = {"values": [1.0, 2.0, 3.0, 4.0, 5.0]}

        start = time.time()
        result = await plugin.execute(operation="normalize", data=data)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 50, f"Execution took {elapsed:.2f}ms, expected < 50ms"
        assert result.get("success") is True


class TestMemoryOptimization:
    """内存优化"""

    def test_simple_agent_memory(self):
        """SimpleAgent 内存占用 < 15MB"""
        from agents import SimpleAgent

        tracemalloc.start()
        agent = SimpleAgent.from_preset("default")
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 15, f"Memory peak: {peak_mb:.1f}MB, expected < 15MB"

    def test_tool_memory_efficiency(self):
        """工具内存占用 < 5MB"""
        from agents import GripperTool, MoveTool, VisionTool

        tracemalloc.start()
        gripper = GripperTool()
        move = MoveTool()
        vision = VisionTool()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 5, f"Memory peak: {peak_mb:.1f}MB, expected < 5MB"

    def test_plugin_memory_efficiency(self):
        """插件内存占用 < 5MB"""
        from agents import PreprocessorPlugin, PostprocessorPlugin, VisualizationPlugin

        tracemalloc.start()
        prep = PreprocessorPlugin()
        post = PostprocessorPlugin()
        viz = VisualizationPlugin()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 5, f"Memory peak: {peak_mb:.1f}MB, expected < 5MB"


class TestConcurrencyOptimization:
    """并发优化"""

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self, dummy_config, dummy_llm_provider,
                                              dummy_perception_provider, dummy_executor):
        """支持 10 个并发代理"""
        from agents import SimpleAgent
        import asyncio

        async def run_agent(idx: int):
            agent = SimpleAgent(
                config=dummy_config,
                llm_provider=dummy_llm_provider,
                perception_provider=dummy_perception_provider,
                executor=dummy_executor
            )
            return await agent.run_task(f"task_{idx}")

        start = time.time()
        tasks = [run_agent(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        assert len(results) == 10
        assert all(r is not None for r in results)
        assert elapsed < 10.0, f"10 concurrent tasks took {elapsed:.3f}s, expected < 10s"

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """支持并发工具调用"""
        from agents import GripperTool
        import asyncio

        async def call_tool(idx: int):
            tool = GripperTool()
            return await tool.execute(action="open")

        start = time.time()
        tasks = [call_tool(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        assert len(results) == 20
        assert all(r.get("success") for r in results)
        assert elapsed < 5.0, f"20 concurrent calls took {elapsed:.3f}s, expected < 5s"


class TestBatchProcessing:
    """批处理优化"""

    @pytest.mark.asyncio
    async def test_batch_preprocessing(self):
        """批处理数据预处理"""
        from agents import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        # 批处理多个数据集
        datasets = [
            {"values": [1.0, 2.0, 3.0]},
            {"values": [4.0, 5.0, 6.0]},
            {"values": [7.0, 8.0, 9.0]},
        ]

        start = time.time()
        results = []
        for data in datasets:
            result = await plugin.execute(operation="normalize", data=data)
            results.append(result)
        elapsed = time.time() - start

        assert len(results) == 3
        assert all(r.get("success") for r in results)
        assert elapsed < 1.0, f"Batch processing took {elapsed:.3f}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_batch_postprocessing(self):
        """批处理结果后处理"""
        from agents import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        # 批处理多个结果
        results_list = [
            {"detections": [{"id": i, "confidence": 0.9}]}
            for i in range(10)
        ]

        start = time.time()
        processed = []
        for result in results_list:
            processed_result = await plugin.execute(
                operation="format",
                data=result
            )
            processed.append(processed_result)
        elapsed = time.time() - start

        assert len(processed) == 10
        assert all(r.get("success") for r in processed)
        assert elapsed < 1.0, f"Batch processing took {elapsed:.3f}s, expected < 1s"


class TestCachingEffectiveness:
    """缓存有效性"""

    @pytest.mark.asyncio
    async def test_preprocessor_cache_speedup(self):
        """预处理器缓存加速"""
        from agents import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        data = {"values": [1.0, 2.0, 3.0, 4.0, 5.0]}

        # 第一次调用（无缓存）
        start = time.time()
        result1 = await plugin.execute(operation="normalize", data=data)
        time1 = time.time() - start

        # 第二次调用（有缓存）
        start = time.time()
        result2 = await plugin.execute(operation="normalize", data=data)
        time2 = time.time() - start

        # 缓存应该更快
        assert result2.get("from_cache") is True
        assert time2 < time1, f"Cached call {time2*1000:.2f}ms should be faster than {time1*1000:.2f}ms"

    @pytest.mark.asyncio
    async def test_config_cache_speedup(self):
        """配置缓存加速"""
        from agents.config.manager import ConfigManager

        # 第一次加载
        start = time.time()
        config1 = ConfigManager.create(agent_name="test")
        time1 = time.time() - start

        # 第二次加载（应该使用缓存）
        start = time.time()
        config2 = ConfigManager.create(agent_name="test")
        time2 = time.time() - start

        # 通常第二次应该更快或相同
        assert time2 <= time1 * 1.2, "Cached load should be similar or faster"
