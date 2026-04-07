#!/usr/bin/env python3
"""
测试机械臂控制Skills - 调试版
"""
import sys
import asyncio
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

from skills.arm_control.motion_skill import MotionSkill
from skills.arm_control.gripper_skill import GripperSkill, SkillStatus
from skills.arm_control.joint_skill import JointSkill


async def test_motion_skill():
    print("\n--- Testing MotionSkill ---")
    
    skill = MotionSkill()
    
    # 测试1: 方向移动
    print("Test 1: Move forward 0.2m")
    result = await skill.execute("move", direction="forward", distance=0.2)
    print(f"  result.status = {result.status}")
    print(f"  result.status.__class__ = {result.status.__class__}")
    print(f"  SkillStatus.SUCCESS = {SkillStatus.SUCCESS}")
    print(f"  SkillStatus.SUCCESS.__class__ = {SkillStatus.SUCCESS.__class__}")
    print(f"  Equal? {result.status == SkillStatus.SUCCESS}")
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}, status={result.status}"
    print(f"  ✓ Result: {result.output}")


if __name__ == "__main__":
    asyncio.run(test_motion_skill())
