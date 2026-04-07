"""
agents/core/agent_loop.py - 核心代理循环（纯 Python，无 ROS2 依赖）

实现基本的 observe-think-act 循环：
1. 观察：从感知系统获取状态
2. 思考：LLM 生成动作
3. 执行：执行器执行动作
4. 反馈：记录结果
"""

from typing import Optional
from .types import RobotObservation, SkillResult, AgentConfig


class RobotAgentLoop:
    """
    核心代理循环

    实现基本的 observe-think-act-reflect 循环。
    不依赖 ROS2，可在纯 Python 环境运行。
    """

    def __init__(self, llm_provider, perception_provider, executor, config: AgentConfig):
        """
        初始化代理循环

        Args:
            llm_provider: LLM 提供者（生成动作）
            perception_provider: 感知提供者（获取观察）
            executor: 执行器（执行动作）
            config: 代理配置
        """
        self.llm_provider = llm_provider
        self.perception_provider = perception_provider
        self.executor = executor
        self.config = config
        self.step_count = 0

    async def step(self) -> SkillResult:
        """
        执行一步 observe-think-act 循环

        Returns:
            SkillResult: 执行结果

        Flow:
            1. 检查是否超过最大步数
            2. 获取观察（感知）
            3. 生成动作（LLM）
            4. 执行动作
            5. 增加步数计数
            6. 返回结果
        """
        # 检查步数限制
        if self.step_count >= self.config.max_steps:
            return SkillResult(
                success=False,
                message="Max steps exceeded"
            )

        # 步骤 1：观察
        observation = await self.perception_provider.get_observation()

        # 步骤 2：思考 - 生成动作
        action = await self.llm_provider.generate_action(observation)

        # 步骤 3：执行
        result = await self.executor.execute(action)

        # 步骤 4：更新步数
        self.step_count += 1

        # 步骤 5：返回结果
        return result
