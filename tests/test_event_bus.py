# tests/test_event_bus.py
"""EventBus 事件总线测试"""
import pytest
import asyncio
from datetime import datetime


def test_event_creation():
    """验证事件创建"""
    from agents.events.bus import Event, EventPriority

    event = Event(
        type="skill.started",
        source="grasp_skill",
        data={"object": "cube"}
    )

    assert event.type == "skill.started"
    assert event.source == "grasp_skill"
    assert event.data == {"object": "cube"}
    assert event.priority == EventPriority.NORMAL
    assert isinstance(event.timestamp, datetime)


def test_event_priority():
    """验证事件优先级"""
    from agents.events.bus import Event, EventPriority

    event_low = Event(type="test", source="test", priority=EventPriority.LOW)
    event_normal = Event(type="test", source="test", priority=EventPriority.NORMAL)
    event_high = Event(type="test", source="test", priority=EventPriority.HIGH)
    event_critical = Event(type="test", source="test", priority=EventPriority.CRITICAL)

    assert event_low.priority == EventPriority.LOW
    assert event_normal.priority == EventPriority.NORMAL
    assert event_high.priority == EventPriority.HIGH
    assert event_critical.priority == EventPriority.CRITICAL


def test_event_bus_subscribe():
    """验证事件订阅"""
    from agents.events.bus import EventBus, Event

    bus = EventBus()
    callback_called = []

    def callback(event: Event):
        callback_called.append(event)

    bus.subscribe("test.event", callback)

    assert bus.get_subscribers("test.event") == 1


def test_event_bus_unsubscribe():
    """验证取消订阅"""
    from agents.events.bus import EventBus, Event

    bus = EventBus()
    callback_called = []

    def callback(event: Event):
        callback_called.append(event)

    bus.subscribe("test.event", callback)
    bus.unsubscribe("test.event", callback)

    assert bus.get_subscribers("test.event") == 0


@pytest.mark.asyncio
async def test_event_bus_publish():
    """验证事件发布"""
    from agents.events.bus import EventBus, Event

    bus = EventBus()
    received_events = []

    async def callback(event: Event):
        received_events.append(event)

    bus.subscribe("robot.moved", callback)

    event = Event(type="robot.moved", source="test", data={"position": [1, 2, 3]})
    await bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].data == {"position": [1, 2, 3]}


def test_event_bus_publish_sync():
    """验证同步事件发布"""
    from agents.events.bus import EventBus, Event

    bus = EventBus()
    received_events = []

    def callback(event: Event):
        received_events.append(event)

    bus.subscribe("robot.moved", callback)

    event = Event(type="robot.moved", source="test", data={"position": [1, 2, 3]})
    bus.publish_sync(event)

    assert len(received_events) == 1


def test_event_bus_priority_subscribers():
    """验证优先级订阅"""
    from agents.events.bus import EventBus, Event, EventPriority

    bus = EventBus()
    call_order = []

    def low_priority(event: Event):
        call_order.append("low")

    def high_priority(event: Event):
        call_order.append("high")

    bus.subscribe_priority("test.event", low_priority, EventPriority.LOW)
    bus.subscribe_priority("test.event", high_priority, EventPriority.HIGH)

    event = Event(type="test.event", source="test")
    bus.publish_sync(event)

    # 高优先级先执行
    assert call_order == ["high", "low"]


def test_event_bus_clear():
    """验证清除订阅"""
    from agents.events.bus import EventBus, Event

    bus = EventBus()

    def callback1(event: Event):
        pass

    def callback2(event: Event):
        pass

    bus.subscribe("event1", callback1)
    bus.subscribe("event2", callback2)

    # 清除单个
    bus.clear("event1")
    assert bus.get_subscribers("event1") == 0
    assert bus.get_subscribers("event2") == 1

    # 清除所有
    bus.clear()
    assert bus.get_subscribers("event2") == 0


def test_get_event_bus():
    """验证全局事件总线"""
    from agents.events.bus import get_event_bus, reset_event_bus

    reset_event_bus()

    bus1 = get_event_bus()
    bus2 = get_event_bus()

    assert bus1 is bus2
