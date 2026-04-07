"""
agents/config/schemas.py - 配置 Schema（使用 Pydantic 验证）

定义配置的数据结构和验证规则
"""

from pydantic import BaseModel, Field, validator
from typing import Optional


class AgentConfigSchema(BaseModel):
    """代理配置 Schema"""
    agent_name: str
    max_steps: int = Field(100, ge=1, description="最大步数（必须 >= 1）")
    llm_model: str = "qwen"
    perception_enabled: bool = True

    class Config:
        extra = 'allow'  # 允许额外字段

    @validator('max_steps')
    def validate_max_steps(cls, v):
        """验证 max_steps >= 1"""
        if v < 1:
            raise ValueError("max_steps must be >= 1")
        return v


class PerceptionConfigSchema(BaseModel):
    """感知配置 Schema"""
    vision_model: str = "sam3"
    enabled: bool = True

    class Config:
        extra = 'allow'


class CognitionConfigSchema(BaseModel):
    """认知配置 Schema"""
    llm_provider: str = "ollama"
    code_generation_enabled: bool = True
    memory_size: int = 8000

    class Config:
        extra = 'allow'


class ExecutionConfigSchema(BaseModel):
    """执行配置 Schema"""
    robot_type: str = "simulated"
    gripper_enabled: bool = True

    class Config:
        extra = 'allow'
