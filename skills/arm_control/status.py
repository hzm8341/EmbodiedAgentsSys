"""
共享的SkillStatus枚举定义

这个模块定义了所有Skills使用的统一SkillStatus枚举，
避免由于多个枚举定义导致的比较问题。
"""
from enum import Enum


class SkillStatus(Enum):
    """Skill执行状态 - 统一枚举定义"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
