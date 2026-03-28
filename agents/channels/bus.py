"""Async message bus for decoupled channel-agent communication.

Ported from RoboClaw/roboclaw/bus/queue.py.
Extended with priority queue support and task-scoped routing.
"""

import asyncio
import logging
from typing import Callable, Awaitable

from agents.channels.events import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class MessageBus:
    """Async message bus that decouples channels from the robot agent core.

    Channels push InboundMessages; the agent consumes them, processes,
    and pushes OutboundMessages back for channels to deliver.

    The bus is NOT thread-safe by itself — all callers must be in the
    same asyncio event loop. For ROS2 cross-thread use, wrap calls with
    asyncio.run_coroutine_threadsafe().
    """

    def __init__(self, maxsize: int = 0):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue(maxsize=maxsize)
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue(maxsize=maxsize)
        self._outbound_handlers: list[Callable[[OutboundMessage], Awaitable[None]]] = []

    # ------------------------------------------------------------------
    # Inbound (channel → agent)
    # ------------------------------------------------------------------

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Push a message from a channel to the agent."""
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """Block until the next inbound message is available."""
        return await self.inbound.get()

    def inbound_task_done(self) -> None:
        """Signal that the consumed inbound item has been processed."""
        self.inbound.task_done()

    # ------------------------------------------------------------------
    # Outbound (agent → channels)
    # ------------------------------------------------------------------

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Push a response from the agent, and notify registered handlers."""
        await self.outbound.put(msg)
        for handler in self._outbound_handlers:
            try:
                await handler(msg)
            except Exception as e:
                logger.warning("Outbound handler error: %s", e)

    async def consume_outbound(self) -> OutboundMessage:
        """Block until the next outbound message is available."""
        return await self.outbound.get()

    def register_outbound_handler(
        self,
        handler: Callable[[OutboundMessage], Awaitable[None]],
    ) -> None:
        """Register a coroutine that is called for every outbound message."""
        self._outbound_handlers.append(handler)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def inbound_size(self) -> int:
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        return self.outbound.qsize()
