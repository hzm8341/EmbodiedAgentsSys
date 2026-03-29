"""测试消息渠道基础设施。"""
import asyncio
import pytest

from agents.channels.bus import MessageBus
from agents.channels.events import InboundMessage, OutboundMessage


# ─── MessageBus 测试 ───────────────────────────────────────────────────

def test_message_bus_publish_and_consume_inbound():
    async def _run():
        bus = MessageBus()
        msg = InboundMessage(content="hello", chat_id="123", sender_id="u1", channel="test")
        await bus.publish_inbound(msg)
        received = await asyncio.wait_for(bus.consume_inbound(), timeout=1.0)
        assert received.content == "hello"
        assert received.sender_id == "u1"
    asyncio.run(_run())


def test_message_bus_publish_and_consume_outbound():
    async def _run():
        bus = MessageBus()
        msg = OutboundMessage(chat_id="123", channel="test", content="reply")
        await bus.publish_outbound(msg)
        received = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
        assert received.content == "reply"
    asyncio.run(_run())


def test_message_bus_multiple_inbound():
    async def _run():
        bus = MessageBus()
        for i in range(3):
            await bus.publish_inbound(
                InboundMessage(content=f"msg{i}", chat_id="c", sender_id="u", channel="t")
            )
        texts = []
        for _ in range(3):
            m = await asyncio.wait_for(bus.consume_inbound(), timeout=1.0)
            texts.append(m.content)
        assert texts == ["msg0", "msg1", "msg2"]
    asyncio.run(_run())


# ─── BaseChannel 白名单测试 ────────────────────────────────────────────

from agents.channels.base import BaseChannel


class _DummyChannel(BaseChannel):
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def send(self, chat_id: str, text: str) -> None: pass


def test_base_channel_allow_from_empty_allows_all():
    bus = MessageBus()
    ch = _DummyChannel(bus, allow_from=[])
    assert ch.is_allowed("anyone") is True


def test_base_channel_allow_from_whitelist():
    bus = MessageBus()
    ch = _DummyChannel(bus, allow_from=["alice", "bob"])
    assert ch.is_allowed("alice") is True
    assert ch.is_allowed("charlie") is False


def test_base_channel_allow_from_wildcard():
    bus = MessageBus()
    ch = _DummyChannel(bus, allow_from=["*"])
    assert ch.is_allowed("anyone") is True


# ─── TelegramChannel import guard 测试 ────────────────────────────────

def test_telegram_channel_import_guard():
    """无 telegram 依赖时应抛 ImportError。"""
    import sys
    # 若实际有安装则跳过
    if "telegram" in sys.modules:
        pytest.skip("python-telegram-bot is installed, skipping import guard test")
    with pytest.raises(ImportError, match="python-telegram-bot"):
        from agents.channels.telegram_channel import TelegramChannel
        bus = MessageBus()
        TelegramChannel(bus, token="fake")


# ─── FeishuChannel import guard 测试 ──────────────────────────────────

def test_feishu_channel_import_guard():
    """无 lark-oapi 依赖时应抛 ImportError。"""
    import sys
    if "lark_oapi" in sys.modules:
        pytest.skip("lark-oapi is installed, skipping import guard test")
    with pytest.raises(ImportError, match="lark-oapi"):
        from agents.channels.feishu_channel import FeishuChannel
        bus = MessageBus()
        FeishuChannel(bus, app_id="x", app_secret="y")
