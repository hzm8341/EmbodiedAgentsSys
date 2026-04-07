"""Context budget tracking and status management."""
from __future__ import annotations
from enum import Enum
from typing import Any


class BudgetStatus(str, Enum):
    """Enumeration for context budget status levels."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class ContextBudget:
    """Tracks context window usage and budget status.

    Provides token estimation, budget checking, and status reporting
    for managing context window constraints.
    """

    def __init__(
        self,
        max_tokens: int = 100_000,
        warning_threshold: float = 0.80,
        critical_threshold: float = 0.95,
    ) -> None:
        """Initialize context budget tracker.

        Args:
            max_tokens: Maximum tokens allowed in context.
            warning_threshold: Ratio at which to issue warning (default 0.80).
            critical_threshold: Ratio at which to mark critical (default 0.95).
        """
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens in message list.

        Args:
            messages: List of message dictionaries.

        Returns:
            Approximate token count.
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Rough heuristic: 4 chars per token
                total += max(1, len(content) // 4)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total += max(1, len(item.get("text", "")) // 4)
                    elif isinstance(item, dict) and "image" in item.get("type", ""):
                        # Estimate images as ~1000 tokens
                        total += 1000
        return total

    def check_budget(self, messages: list[dict[str, Any]]) -> BudgetStatus:
        """Check budget status for message list.

        Args:
            messages: List of message dictionaries.

        Returns:
            BudgetStatus indicating OK, WARNING, or CRITICAL.
        """
        ratio = self.estimate_tokens(messages) / self.max_tokens
        if ratio >= self.critical_threshold:
            return BudgetStatus.CRITICAL
        if ratio >= self.warning_threshold:
            return BudgetStatus.WARNING
        return BudgetStatus.OK

    def should_warn(self, messages: list[dict[str, Any]]) -> bool:
        """Check if warning should be issued.

        Args:
            messages: List of message dictionaries.

        Returns:
            True if status is WARNING or CRITICAL.
        """
        return self.check_budget(messages) in (BudgetStatus.WARNING, BudgetStatus.CRITICAL)

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """Check if compression is needed.

        Args:
            messages: List of message dictionaries.

        Returns:
            True if status is CRITICAL.
        """
        return self.check_budget(messages) == BudgetStatus.CRITICAL
