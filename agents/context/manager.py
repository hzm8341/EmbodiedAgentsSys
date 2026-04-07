"""Context management orchestration."""
from __future__ import annotations
from typing import Any
from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import AutoCompactor, MicroCompressor


class ContextManager:
    """Orchestrates context budget tracking and compression.

    Combines budget checking with automatic compression when context
    window usage becomes critical.
    """

    def __init__(self, max_tokens: int = 100_000) -> None:
        """Initialize context manager.

        Args:
            max_tokens: Maximum tokens allowed in context (default 100,000).
        """
        self._budget = ContextBudget(max_tokens=max_tokens)
        self._compactor = AutoCompactor(MicroCompressor())

    async def process(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process messages with compression if needed.

        Args:
            messages: List of message dictionaries.

        Returns:
            Original messages if below critical threshold, else compressed.
        """
        should_compress = self._budget.should_compress(messages)
        return await self._compactor.compact_if_needed(messages, should_compress)

    def get_status(self, messages: list[dict[str, Any]]) -> BudgetStatus:
        """Get current budget status for messages.

        Args:
            messages: List of message dictionaries.

        Returns:
            BudgetStatus indicating OK, WARNING, or CRITICAL.
        """
        return self._budget.check_budget(messages)
