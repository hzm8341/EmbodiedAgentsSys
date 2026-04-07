"""Utilities for testing async code."""
import asyncio
import time
from typing import Any, Callable


def run_async(coro: Any) -> Any:
    """Run an async coroutine and return its result.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine.
    """
    return asyncio.run(coro)


async def assert_eventually(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition never became True",
) -> None:
    """Assert that a condition eventually becomes True within a timeout.

    Args:
        condition: Async callable that returns bool.
        timeout: Maximum time in seconds to wait.
        interval: Time in seconds between condition checks.
        message: Error message if condition times out.

    Raises:
        AssertionError: If condition doesn't become True within timeout.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await condition():
            return
        await asyncio.sleep(interval)
    raise AssertionError(message)
