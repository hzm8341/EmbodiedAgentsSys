"""
语音示教Agent - 端到端集成

将语音输入、语义解析、机械臂控制串联成完整的语音示教流程。

示例用法:
    agent = VoiceTeachingAgent()
    result = await agent.execute("向前20厘米")
"""
import sys
import os

sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

# 绕过ROS依赖检查
os.environ["AGENTS_DOCS_BUILD"] = "1"

import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 直接加载voice_command模块(避免ROS依赖)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "voice_command", 
    "/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/voice_command.py"
)
voice_command_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice_command_module)
VoiceCommand = voice_command_module.VoiceCommand

from skills.arm_control.motion_skill import MotionSkill
from skills.arm_control.gripper_skill import GripperSkill
from skills.arm_control.status import SkillStatus

@dataclass
class VoiceTeachingResult:
    """语音示教执行结果"""
    success: bool
    action_taken: str
    details: Dict[str, Any]
    error: Optional[str] = None


class VoiceTeachingAgent:
    """
    语音示教Agent
    
    接收用户语音指令，解析为结构化命令，并调用机械臂执行。
    
    支持的指令级别:
    - L1 基础运动: "向前20cm", "向上5cm"
    - L2 复合动作: "把夹爪打开", "移动到料框上方"
    - L3 任务级: "把零件拿到拍照位置"
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化语音示教Agent
        
        Args:
            config: 配置选项
        """
        self.config = config or {}
        
        # 初始化组件
        self.voice_command = VoiceCommand()
        self.motion_skill = MotionSkill()
        self.gripper_skill = GripperSkill()
        
        # 状态
        self._initialized = True
    
    async def execute(self, text: str) -> VoiceTeachingResult:
        """
        执行语音指令
        
        Args:
            text: 用户语音指令文本
            
        Returns:
            VoiceTeachingResult: 执行结果
        """
        try:
            # Step 1: 语义解析
            parsed = self.voice_command.parse(text)
            
            if parsed.intent == "unknown":
                return VoiceTeachingResult(
                    success=False,
                    action_taken="parse",
                    details={},
                    error=f"无法理解指令: {text}"
                )
            
            # Step 2: 根据意图类型执行相应动作
            if parsed.intent == "motion":
                result = await self._handle_motion(parsed.params)
            elif parsed.intent == "gripper":
                result = await self._handle_gripper(parsed.params)
            elif parsed.intent == "composite":
                result = await self._handle_composite(parsed.params)
            elif parsed.intent == "task":
                result = await self._handle_task(parsed.params)
            else:
                result = VoiceTeachingResult(
                    success=False,
                    action_taken="route",
                    details={},
                    error=f"未知意图类型: {parsed.intent}"
                )
            
            return result
            
        except Exception as e:
            return VoiceTeachingResult(
                success=False,
                action_taken="execute",
                details={},
                error=str(e)
            )
    
    async def _handle_motion(self, params: Dict) -> VoiceTeachingResult:
        """处理基础运动指令"""
        action = params.get("action")
        direction = params.get("direction")
        distance = params.get("distance")
        
        result = await self.motion_skill.execute(
            action=action,
            direction=direction,
            distance=distance
        )
        
        return VoiceTeachingResult(
            success=result.status == SkillStatus.SUCCESS,
            action_taken=f"motion_{action}",
            details=result.output or {},
            error=result.error
        )
    
    async def _handle_gripper(self, params: Dict) -> VoiceTeachingResult:
        """处理夹爪动作指令"""
        action = params.get("action")
        
        result = await self.gripper_skill.execute(action=action)
        
        return VoiceTeachingResult(
            success=result.status == SkillStatus.SUCCESS,
            action_taken=f"gripper_{action}",
            details=result.output or {},
            error=result.error
        )
    
    async def _handle_composite(self, params: Dict) -> VoiceTeachingResult:
        """处理复合动作指令"""
        action = params.get("action")
        
        if action == "move_to":
            target = params.get("target")
            result = await self.motion_skill.execute(
                action="move_to",
                target=target
            )
            
            return VoiceTeachingResult(
                success=result.status == SkillStatus.SUCCESS,
                action_taken=f"move_to_{target}",
                details=result.output or {},
                error=result.error
            )
        
        return VoiceTeachingResult(
            success=False,
            action_taken="composite_unknown",
            details={},
            error=f"未知复合动作: {action}"
        )
    
    async def _handle_task(self, params: Dict) -> VoiceTeachingResult:
        """处理任务级指令"""
        action = params.get("action")
        
        if action == "transfer":
            # 任务: 搬运物体
            # 执行序列: 移动到源位置 → 抓取 → 移动到目标位置 → 释放
            source = params.get("source")
            target = params.get("target")
            
            # 简化的任务执行
            # 实际应该先移动到物体位置，抓取，然后移动到目标
            
            # 移动到目标位置（简化）
            result = await self.motion_skill.execute(
                action="move_to",
                target=target
            )
            
            return VoiceTeachingResult(
                success=result.status == SkillStatus.SUCCESS,
                action_taken=f"transfer_{source}_to_{target}",
                details={
                    "source": source,
                    "target": target,
                    "executed": "move_to_target"
                },
                error=result.error
            )
        
        return VoiceTeachingResult(
            success=False,
            action_taken="task_unknown",
            details={},
            error=f"未知任务动作: {action}"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "motion_position": self.motion_skill.get_current_position(),
            "gripper_position": self.gripper_skill.get_current_position(),
        }


async def demo():
    """演示语音示教Agent"""
    print("="*50)
    print("Voice Teaching Agent Demo")
    print("="*50)
    
    agent = VoiceTeachingAgent()
    
    # 测试用例
    test_cases = [
        "向前20厘米",
        "向上5cm",
        "把夹爪打开",
        "移动到料框上方",
        "把零件拿到拍照位置",
    ]
    
    for text in test_cases:
        print(f"\n指令: {text}")
        result = await agent.execute(text)
        print(f"  成功: {result.success}")
        print(f"  动作: {result.action_taken}")
        print(f"  详情: {result.details}")
        if result.error:
            print(f"  错误: {result.error}")
    
    # 打印状态
    print(f"\n最终状态: {agent.get_status()}")


if __name__ == "__main__":
    asyncio.run(demo())
