"""Telegram 消息渠道（需要 python-telegram-bot>=21.0）。"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from .base import BaseChannel

if TYPE_CHECKING:
    from .bus import MessageBus

logger = logging.getLogger(__name__)

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    _HAS_TELEGRAM = True
except ImportError:
    _HAS_TELEGRAM = False


class TelegramChannel(BaseChannel):
    """通过 Telegram Bot 收发消息。

    需要安装: pip install python-telegram-bot>=21.0
    """

    def __init__(
        self,
        bus: "MessageBus",
        token: str,
        allow_from: list[str] | None = None,
        send_progress: bool = True,
    ):
        if not _HAS_TELEGRAM:
            raise ImportError(
                "python-telegram-bot not installed. Run: pip install python-telegram-bot>=21.0"
            )
        super().__init__(bus, allow_from)
        self._token = token
        self.send_progress = send_progress
        self._app: Application | None = None

    async def start(self) -> None:
        """启动 Telegram Bot 监听。"""
        from agents.channels.events import InboundMessage

        self._app = Application.builder().token(self._token).build()

        async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            if update.message is None:
                return
            sender_id = str(update.effective_user.id)
            if not self.is_allowed(sender_id):
                logger.warning("Telegram: rejected message from %s", sender_id)
                return
            msg = InboundMessage(
                content=update.message.text or "",
                chat_id=str(update.effective_chat.id),
                sender_id=sender_id,
                channel="telegram",
            )
            await self.bus.publish_inbound(msg)

        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await self._start_outbound_loop()
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("TelegramChannel started")

    async def stop(self) -> None:
        await self._stop_outbound_loop()
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        logger.info("TelegramChannel stopped")

    async def send(self, chat_id: str, text: str) -> None:
        if self._app is None:
            return
        await self._app.bot.send_message(chat_id=int(chat_id), text=text[:4096])
