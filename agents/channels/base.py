"""BaseChannel — 消息渠道抽象基类。"""
from __future__ import annotations
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseChannel(ABC):
    """所有消息渠道的抽象基类。

    子类需实现 start() / stop() / send() 三个方法。
    渠道通过 MessageBus 与 AgentLoop 通信：
      - 入站：收到外部消息 → put InboundMessage 到 bus.inbound
      - 出站：从 bus.outbound 取消息 → 发送到外部平台
    """

    def __init__(self, bus: Any, allow_from: list[str] | None = None):
        """
        Args:
            bus: MessageBus 实例
            allow_from: 允许的发送者白名单，None 表示不限制
        """
        self.bus = bus
        self.allow_from = allow_from or []
        self._running = False
        self._outbound_task: Optional[asyncio.Task] = None

    def is_allowed(self, sender_id: str) -> bool:
        """检查发送者是否在白名单中。空白名单允许所有人。"""
        if not self.allow_from:
            return True
        return "*" in self.allow_from or sender_id in self.allow_from

    @abstractmethod
    async def start(self) -> None:
        """启动渠道（开始监听入站消息）。"""

    @abstractmethod
    async def stop(self) -> None:
        """停止渠道。"""

    @abstractmethod
    async def send(self, chat_id: str, text: str) -> None:
        """发送消息到指定 chat_id。"""

    async def _outbound_loop(self) -> None:
        """持续从 bus.outbound 取消息并发送，在 start() 中作为后台任务启动。"""
        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_outbound(), timeout=1.0
                )
                await self.send(msg.chat_id, msg.content)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.error("outbound send error: %s", exc)

    async def _start_outbound_loop(self) -> None:
        self._running = True
        self._outbound_task = asyncio.create_task(self._outbound_loop())

    async def _stop_outbound_loop(self) -> None:
        self._running = False
        if self._outbound_task:
            self._outbound_task.cancel()
            try:
                await self._outbound_task
            except asyncio.CancelledError:
                pass
