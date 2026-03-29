"""飞书（Lark）消息渠道（需要 lark-oapi>=1.3）。"""
from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING

from .base import BaseChannel

if TYPE_CHECKING:
    from .bus import MessageBus

logger = logging.getLogger(__name__)

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest,
        CreateMessageRequestBody,
        ReplyMessageRequest,
        ReplyMessageRequestBody,
    )
    _HAS_LARK = True
except ImportError:
    _HAS_LARK = False


class FeishuChannel(BaseChannel):
    """通过飞书机器人收发消息。

    需要安装: pip install lark-oapi>=1.3
    """

    def __init__(
        self,
        bus: "MessageBus",
        app_id: str,
        app_secret: str,
        allow_from: list[str] | None = None,
        send_progress: bool = True,
    ):
        if not _HAS_LARK:
            raise ImportError("lark-oapi not installed. Run: pip install lark-oapi>=1.3")
        super().__init__(bus, allow_from)
        self._app_id = app_id
        self._app_secret = app_secret
        self.send_progress = send_progress
        self._client: lark.Client | None = None
        self._webhook_server = None

    async def start(self) -> None:
        """初始化飞书 Client，启动 Webhook 服务。"""
        self._client = (
            lark.Client.builder()
            .app_id(self._app_id)
            .app_secret(self._app_secret)
            .log_level(lark.LogLevel.INFO)
            .build()
        )
        await self._start_outbound_loop()
        logger.info("FeishuChannel started (polling/webhook mode)")

    async def stop(self) -> None:
        await self._stop_outbound_loop()
        logger.info("FeishuChannel stopped")

    async def send(self, chat_id: str, text: str) -> None:
        """发送文本消息到飞书会话。"""
        if self._client is None:
            return
        body = CreateMessageRequestBody.builder() \
            .receive_id(chat_id) \
            .msg_type("text") \
            .content(json.dumps({"text": text[:4000]})) \
            .build()
        req = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(body) \
            .build()
        try:
            resp = self._client.im.v1.message.create(req)
            if not resp.success():
                logger.error("Feishu send failed: %s %s", resp.code, resp.msg)
        except Exception as exc:
            logger.error("Feishu send error: %s", exc)

    async def handle_webhook_event(self, event_data: dict) -> None:
        """处理飞书 Webhook 推送事件（供 HTTP 服务器调用）。"""
        from agents.channels.events import InboundMessage
        try:
            sender_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id", "")
            chat_id = event_data.get("message", {}).get("chat_id", "")
            content_str = event_data.get("message", {}).get("content", "{}")
            content = json.loads(content_str) if isinstance(content_str, str) else content_str
            text = content.get("text", "")
            if not self.is_allowed(sender_id):
                return
            msg = InboundMessage(
                content=text,
                chat_id=chat_id,
                sender_id=sender_id,
                channel="feishu",
            )
            await self.bus.publish_inbound(msg)
        except Exception as exc:
            logger.error("FeishuChannel webhook error: %s", exc)
