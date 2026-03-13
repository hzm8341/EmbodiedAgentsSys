# agents/utils/performance.py
"""性能优化工具

提供异步缓存、批处理等性能优化功能。
"""

import asyncio
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json

T = TypeVar('T')


class AsyncCache:
    """异步缓存

    提供基于时间的异步缓存功能。
    """

    def __init__(self, ttl_seconds: float = 60.0):
        """初始化缓存

        Args:
            ttl_seconds: 缓存过期时间（秒）
        """
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl_seconds

    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            "args": str(args),
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._ttl):
                return value
            else:
                del self._cache[key]
        return None

    async def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self._cache[key] = (value, datetime.now())

    async def delete(self, key: str) -> None:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]

    async def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def cached(self, func: Callable) -> Callable:
        """缓存装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = self._make_key(*args, **kwargs)
            cached_value = await self.get(key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            await self.set(key, result)
            return result
        return wrapper


class BatchProcessor:
    """批处理器

    用于批量处理任务，减少调度开销。
    """

    def __init__(self, batch_size: int = 10, timeout: float = 0.1):
        """初始化批处理器

        Args:
            batch_size: 批处理大小
            timeout: 超时时间（秒）
        """
        self.batch_size = batch_size
        self.timeout = timeout
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processing = False

    async def add(self, item: Any) -> Any:
        """添加任务并等待结果"""
        future = asyncio.Future()
        await self._queue.put((item, future))
        return await future

    async def process(self, handler: Callable[[list], list]) -> None:
        """处理队列中的任务

        Args:
            handler: 处理函数，接收列表，返回列表
        """
        if self._processing:
            return

        self._processing = True

        try:
            while True:
                batch = []
                futures = []

                # 收集批次
                try:
                    item, future = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self.timeout
                    )
                    batch.append(item)
                    futures.append(future)
                except asyncio.TimeoutError:
                    break

                # 尝试收集更多
                while len(batch) < self.batch_size:
                    try:
                        item, future = await asyncio.wait_for(
                            self._queue.get(),
                            timeout=0.01
                        )
                        batch.append(item)
                        futures.append(future)
                    except asyncio.TimeoutError:
                        break

                # 处理批次
                if batch:
                    results = await handler(batch)
                    for future, result in zip(futures, results):
                        if not future.done():
                            future.set_result(result)

        finally:
            self._processing = False


class RateLimiter:
    """速率限制器

    限制函数调用频率。
    """

    def __init__(self, max_calls: int, period: float):
        """初始化速率限制器

        Args:
            max_calls: 最大调用次数
            period: 时间周期（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self._calls: list = []

    async def acquire(self) -> None:
        """获取调用许可"""
        now = datetime.now()

        # 清理过期的调用记录
        self._calls = [
            t for t in self._calls
            if now - t < timedelta(seconds=self.period)
        ]

        if len(self._calls) >= self.max_calls:
            # 需要等待
            oldest = self._calls[0]
            wait_time = self.period - (now - oldest).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                now = datetime.now()
                self._calls = [
                    t for t in self._calls
                    if now - t < timedelta(seconds=self.period)
                ]

        self._calls.append(now)

    def limited(self, func: Callable) -> Callable:
        """速率限制装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper


# 全局缓存实例
_global_cache: Optional[AsyncCache] = None


def get_cache(ttl_seconds: float = 60.0) -> AsyncCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = AsyncCache(ttl_seconds=ttl_seconds)
    return _global_cache
