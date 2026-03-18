# agents/events/bus.py
"""Event Bus 事件总线

提供事件发布/订阅功能，支持组件间的松耦合通信。
支持分布式多机器人协作（ROS2话题桥接）。
"""

from enum import Enum
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json


class EventPriority(Enum):
    """事件优先级"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """事件数据类"""

    type: str  # 事件类型
    source: str  # 事件源
    data: Any = None  # 事件数据
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"Event({self.type}, {self.source}, {self.timestamp})"


class EventBus:
    """事件总线

    支持事件的发布和订阅，采用观察者模式。
    """

    def __init__(self):
        """初始化事件总线"""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._priority_subscribers: Dict[str, List[tuple]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数，签名为 callback(event: Event)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_priority(
        self, event_type: str, callback: Callable, priority: EventPriority
    ) -> None:
        """订阅带优先级的事件

        Args:
            event_type: 事件类型
            callback: 回调函数
            priority: 优先级
        """
        if event_type not in self._priority_subscribers:
            self._priority_subscribers[event_type] = []
        self._priority_subscribers[event_type].append((priority, callback))
        # 按优先级排序
        self._priority_subscribers[event_type].sort(
            key=lambda x: x[0].value, reverse=True
        )

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消订阅

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    async def publish(self, event: Event) -> None:
        """发布事件

        Args:
            event: 事件对象
        """
        # 先处理优先级订阅者
        if event.type in self._priority_subscribers:
            for priority, callback in self._priority_subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Error in priority subscriber: {e}")

        # 再处理普通订阅者
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Error in subscriber: {e}")

    def publish_sync(self, event: Event) -> None:
        """同步发布事件（在异步上下文中使用）

        Args:
            event: 事件对象
        """
        # 先处理优先级订阅者
        if event.type in self._priority_subscribers:
            for priority, callback in self._priority_subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in priority subscriber: {e}")

        # 再处理普通订阅者
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in subscriber: {e}")

    def clear(self, event_type: Optional[str] = None) -> None:
        """清除订阅

        Args:
            event_type: 事件类型，为 None 时清除所有
        """
        if event_type is None:
            self._subscribers.clear()
            self._priority_subscribers.clear()
        else:
            self._subscribers.pop(event_type, None)
            self._priority_subscribers.pop(event_type, None)

    def get_subscribers(self, event_type: str) -> int:
        """获取订阅者数量"""
        count = len(self._subscribers.get(event_type, []))
        count += len(self._priority_subscribers.get(event_type, []))
        return count


# 全局事件总线实例
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def reset_event_bus() -> None:
    """重置全局事件总线"""
    global _global_bus
    _global_bus = None


class DistributedEventBus(EventBus):
    """分布式事件总线

    扩展 EventBus，支持跨 ROS2 节点的事件广播。
    用于多机器人协作场景。
    """

    def __init__(self, ros_node=None, namespace: str = "/agents/events"):
        """初始化分布式事件总线

        Args:
            ros_node: ROS2 节点实例
            namespace: ROS2 话题命名空间
        """
        super().__init__()
        self._ros_node = ros_node
        self._namespace = namespace
        self._publisher = None

        if ros_node:
            self._setup_ros_bridge()

    def _setup_ros_bridge(self) -> None:
        """设置 ROS2 话题桥接"""
        try:
            from std_msgs.msg import String

            self._publisher = self._ros_node.create_publisher(
                String, f"{self._namespace}/broadcast", 10
            )
            self._ros_node.create_subscription(
                String,
                f"{self._namespace}/broadcast",
                self._on_remote_event,
                10,
            )
        except ImportError:
            pass

    def _on_remote_event(self, msg) -> None:
        """处理远程事件"""
        try:
            data = json.loads(msg.data)
            remote_event = Event(
                type=data.get("type", ""),
                source=data.get("source", "remote"),
                data=data.get("data"),
            )
            asyncio.create_task(self.publish(remote_event))
        except Exception:
            pass

    async def publish(self, event: Event) -> None:
        """发布事件 (含 ROS2 广播)

        Args:
            event: 事件对象
        """
        await super().publish(event)

        if self._publisher:
            try:
                from std_msgs.msg import String

                msg = String(
                    data=json.dumps({
                        "type": event.type,
                        "source": event.source,
                        "data": str(event.data),
                    })
                )
                self._publisher.publish(msg)
            except Exception:
                pass
