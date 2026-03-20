"""
端到端语音示教 Agent 测试

覆盖链路：
- 文本级“语音指令” → VoiceCommand 语义解析
- MotionSkill / GripperSkill 执行动作
- VoiceTeachingAgent 统一封装与状态查询
"""

import os
import asyncio

os.environ.setdefault("AGENTS_DOCS_BUILD", "1")

from examples.voice_teaching_agent import VoiceTeachingAgent


def _run(agent: VoiceTeachingAgent, text: str):
    """帮助函数：在同步测试中运行异步 execute。"""
    return asyncio.run(agent.execute(text))


def test_voice_teaching_basic_motion_forward():
    """L1 基础运动指令：向前移动。"""
    agent = VoiceTeachingAgent()

    result = _run(agent, "向前20厘米")

    assert result.success is True
    assert result.action_taken == "motion_move"

    status = agent.get_status()
    motion_pos = status["motion_position"]
    # 初始位置为 [0.0, -0.5, 0.3, ...]，向前移动后 x 应该大于 0
    assert isinstance(motion_pos, list)
    assert motion_pos[0] > 0.0


def test_voice_teaching_gripper_open_and_close():
    """L2 复合动作指令：夹爪打开 / 关闭。"""
    agent = VoiceTeachingAgent()

    # 打开夹爪
    open_result = _run(agent, "把夹爪打开")
    assert open_result.success is True
    assert open_result.action_taken == "gripper_open"
    status = agent.get_status()
    assert status["gripper_position"] == 0.0

    # 关闭夹爪
    close_result = _run(agent, "关闭夹爪")
    assert close_result.success is True
    assert close_result.action_taken == "gripper_close"
    status = agent.get_status()
    assert status["gripper_position"] > 0.0


def test_voice_teaching_task_level_transfer():
    """L3 任务级指令：把零件拿到拍照位置。"""
    agent = VoiceTeachingAgent()

    result = _run(agent, "把零件拿到拍照位置")

    assert result.success is True
    # VoiceCommand 会保留原始中文 source/target
    assert result.action_taken == "transfer_零件_to_拍照位置"
    assert result.details["source"] == "零件"
    assert result.details["target"] == "拍照位置"

