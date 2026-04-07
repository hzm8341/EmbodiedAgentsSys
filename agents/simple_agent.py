"""
agents/simple_agent.py - 简化接口快速开始

提供 SimpleAgent 类，用户可以用最少的代码创建并运行代理。
支持从预设加载或使用自定义配置和提供者。
"""

from typing import Optional
from .config.manager import ConfigManager
from .config.schemas import AgentConfigSchema
from .core.types import SkillResult
from .core.agent_loop import RobotAgentLoop


class SimpleAgent:
    """简化的代理接口，支持快速开始"""

    def __init__(
        self,
        config: AgentConfigSchema,
        llm_provider=None,
        perception_provider=None,
        executor=None,
    ):
        """
        初始化 SimpleAgent

        Args:
            config: 代理配置对象
            llm_provider: LLM 提供者（可选，使用默认值）
            perception_provider: 感知提供者（可选，使用默认值）
            executor: 执行器（可选，使用默认值）
        """
        self.config = config

        # 使用提供的提供者或创建默认值
        self.perception = perception_provider or self._create_default_perception_provider()
        self.cognition = llm_provider or self._create_default_llm_provider()
        self.execution = executor or self._create_default_executor()
        self.feedback = self._create_default_feedback()

        # 初始化代理循环
        self.loop = RobotAgentLoop(
            llm_provider=self.cognition,
            perception_provider=self.perception,
            executor=self.execution,
            config=config,
        )

    @classmethod
    def from_preset(cls, preset_name: str) -> "SimpleAgent":
        """
        从预设创建 SimpleAgent

        Args:
            preset_name: 预设名称（如 'default', 'vla_plus'）

        Returns:
            SimpleAgent: 代理实例
        """
        config = ConfigManager.load_preset(preset_name)
        return cls(config)

    async def run_task(self, task_description: str) -> SkillResult:
        """
        执行任务

        Args:
            task_description: 任务描述

        Returns:
            SkillResult: 任务执行结果
        """
        # 存储任务描述用于后续使用
        self._current_task = task_description

        # 执行一步循环
        result = await self.loop.step()

        return result

    def _create_default_perception_provider(self):
        """创建默认感知提供者"""
        class DefaultPerceptionProvider:
            async def get_observation(self):
                """获取虚拟观察"""
                from .core.types import RobotObservation
                return RobotObservation()

        return DefaultPerceptionProvider()

    def _create_default_llm_provider(self):
        """创建默认 LLM 提供者"""
        class DefaultLLMProvider:
            async def generate_action(self, observation):
                """生成虚拟动作"""
                return "default_action"

        return DefaultLLMProvider()

    def _create_default_executor(self):
        """创建默认执行器"""
        class DefaultExecutor:
            async def execute(self, action):
                """执行虚拟动作"""
                return SkillResult(success=True, message="Action executed")

        return DefaultExecutor()

    def _create_default_feedback(self):
        """创建默认反馈系统"""
        class DefaultFeedback:
            async def log_result(self, result):
                """记录结果"""
                pass

        return DefaultFeedback()
