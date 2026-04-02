import asyncio
import time
import pytest
from agents.cache import cached, CacheRegistry


class TestCachedDecorator:
    def test_async_function_returns_result(self):
        @cached(ttl=60)
        async def fetch(x: int) -> int:
            return x * 2
        result = asyncio.run(fetch(3))
        assert result == 6

    def test_caches_result_on_second_call(self):
        call_count = 0
        @cached(ttl=60)
        async def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x
        asyncio.run(expensive(1))
        asyncio.run(expensive(1))
        assert call_count == 1

    def test_different_args_call_function_separately(self):
        call_count = 0
        @cached(ttl=60)
        async def fn(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x
        asyncio.run(fn(1))
        asyncio.run(fn(2))
        assert call_count == 2

    def test_expired_entry_calls_function_again(self):
        call_count = 0
        @cached(ttl=0)
        async def fn() -> int:
            nonlocal call_count
            call_count += 1
            return 42
        asyncio.run(fn())
        time.sleep(0.01)
        asyncio.run(fn())
        assert call_count == 2

    def test_cache_clear_forces_recompute(self):
        call_count = 0
        @cached(ttl=60)
        async def fn() -> int:
            nonlocal call_count
            call_count += 1
            return 1
        asyncio.run(fn())
        fn.cache_clear()
        asyncio.run(fn())
        assert call_count == 2

    def test_kwargs_are_part_of_cache_key(self):
        call_count = 0
        @cached(ttl=60)
        async def fn(x: int = 0) -> int:
            nonlocal call_count
            call_count += 1
            return x
        asyncio.run(fn(x=1))
        asyncio.run(fn(x=2))
        assert call_count == 2


class TestCacheRegistry:
    def test_register_and_invalidate(self):
        registry = CacheRegistry()
        call_count = 0
        @cached(ttl=60)
        async def fn() -> int:
            nonlocal call_count
            call_count += 1
            return 1
        registry.register("fn", fn)
        asyncio.run(fn())
        registry.invalidate("fn")
        asyncio.run(fn())
        assert call_count == 2

    def test_invalidate_all(self):
        registry = CacheRegistry()
        counts = {"a": 0, "b": 0}
        @cached(ttl=60)
        async def fn_a() -> int:
            counts["a"] += 1
            return 1
        @cached(ttl=60)
        async def fn_b() -> int:
            counts["b"] += 1
            return 2
        registry.register("a", fn_a)
        registry.register("b", fn_b)
        asyncio.run(fn_a())
        asyncio.run(fn_b())
        registry.invalidate_all()
        asyncio.run(fn_a())
        asyncio.run(fn_b())
        assert counts["a"] == 2
        assert counts["b"] == 2

    def test_get_stats_returns_dict(self):
        registry = CacheRegistry()
        stats = registry.get_stats()
        assert isinstance(stats, dict)
