"""Message compression and compaction strategies."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


class MicroCompressor:
    """Minimal message compression via truncation and content filtering."""

    def compress_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Apply all compression strategies to a message.

        Args:
            msg: Message dictionary to compress.

        Returns:
            Compressed message.
        """
        msg = self.strip_images(msg)
        msg = self.truncate_long_content(msg)
        return msg

    def strip_images(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Remove image content from message.

        Args:
            msg: Message dictionary.

        Returns:
            Message with image content removed.
        """
        content = msg.get("content")
        if isinstance(content, list):
            filtered = [
                item
                for item in content
                if not (isinstance(item, dict) and "image" in item.get("type", ""))
            ]
            return {**msg, "content": filtered}
        return msg

    def truncate_long_content(
        self, msg: dict[str, Any], max_chars: int = 2000
    ) -> dict[str, Any]:
        """Truncate long string content.

        Args:
            msg: Message dictionary.
            max_chars: Maximum characters to keep (default 2000).

        Returns:
            Message with truncated content.
        """
        content = msg.get("content")
        if isinstance(content, str) and len(content) > max_chars:
            return {**msg, "content": content[:max_chars] + " [truncated]"}
        return msg


@dataclass
class CompactionStats:
    """Statistics about message compaction."""

    messages_before: int
    messages_after: int
    tokens_before: int
    tokens_after: int


class AutoCompactor:
    """Automatic message compaction with statistics tracking."""

    def __init__(self, micro: MicroCompressor | None = None) -> None:
        """Initialize auto compactor.

        Args:
            micro: MicroCompressor instance (creates default if None).
        """
        self._micro = micro or MicroCompressor()
        self._stats = CompactionStats(0, 0, 0, 0)

    async def compact_if_needed(
        self, messages: list[dict[str, Any]], should_compress: bool
    ) -> list[dict[str, Any]]:
        """Compact messages if compression is needed.

        Args:
            messages: List of message dictionaries.
            should_compress: Whether to apply compression.

        Returns:
            Original or compressed message list.
        """
        if not should_compress:
            return messages
        return [self._micro.compress_message(msg) for msg in messages]

    def get_stats(self) -> CompactionStats:
        """Get compaction statistics.

        Returns:
            CompactionStats dataclass with metrics.
        """
        return self._stats
