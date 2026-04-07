"""
agents/core/types.py - 基础类型定义（纯 Python，无 ROS2 依赖）

定义代理系统的核心数据类型：
- RobotObservation: 机器人观察
- SkillResult: 技能执行结果
- AgentConfig: 代理配置
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class RobotObservation:
    """
    机器人观察数据

    包含环境的完整状态快照：图像、机器人状态、夹爪状态等
    """
    image: Optional[Any] = None
    state: Dict[str, float] = field(default_factory=dict)
    gripper: Dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        """在创建后设置默认 timestamp"""
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class SkillResult:
    """
    技能执行结果

    表示技能执行的成功/失败及相关数据
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """确保 data 字段初始化"""
        if self.data is None:
            self.data = {}


@dataclass
class AgentConfig:
    """
    代理配置

    控制代理的行为参数
    """
    agent_name: str
    max_steps: int = 100
    llm_model: str = "qwen"
    perception_enabled: bool = True

    def __post_init__(self):
        """验证配置的有效性"""
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")
