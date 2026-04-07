from __future__ import annotations
import asyncio
import functools
import time
from typing import Any, Callable


def cached(ttl: float) -> Callable:
    """Decorator: cache an async function's result for ttl seconds."""
    def decorator(func: Callable) -> Callable:
        _cache: dict[tuple, tuple[Any, float]] = {}
        _lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            if key in _cache:
                result, expires_at = _cache[key]
                if now < expires_at:
                    return result
            async with _lock:
                if key in _cache:
                    result, expires_at = _cache[key]
                    if now < expires_at:
                        return result
                result = await func(*args, **kwargs)
                _cache[key] = (result, now + ttl)
            return result

        def cache_clear() -> None:
            _cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator


class CacheRegistry:
    """Track named caches and invalidate them collectively."""

    def __init__(self) -> None:
        self._caches: dict[str, Any] = {}

    def register(self, name: str, cache_fn: Any) -> None:
        self._caches[name] = cache_fn

    def invalidate(self, name: str) -> None:
        if name in self._caches:
            fn = self._caches[name]
            if hasattr(fn, "cache_clear"):
                fn.cache_clear()

    def invalidate_all(self) -> None:
        for fn in self._caches.values():
            if hasattr(fn, "cache_clear"):
                fn.cache_clear()

    def get_stats(self) -> dict[str, Any]:
        return {"registered": list(self._caches.keys())}
