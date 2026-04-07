#!/usr/bin/env python3
"""
测试GripperSkill - 带调试
"""
import sys
import asyncio
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

from skills.arm_control.gripper_skill import GripperSkill, SkillStatus


async def test_gripper():
    print("--- Testing GripperSkill ---")
    
    skill = GripperSkill()
    
    print("Test 1: Open gripper")
    result = await skill.execute("open")
    print(f"  Status: {result.status}")
    print(f"  Status type: {type(result.status)}")
    print(f"  SkillStatus.SUCCESS: {SkillStatus.SUCCESS}")
    print(f"  SkillStatus.SUCCESS type: {type(SkillStatus.SUCCESS)}")
    print(f"  Output: {result.output}")
    print(f"  Error: {result.error}")
    
    # Check comparison
    print(f"  Are they equal? {result.status == SkillStatus.SUCCESS}")
    if result.status != SkillStatus.SUCCESS:
        print(f"  Difference: {result.status} vs {SkillStatus.SUCCESS}")


if __name__ == "__main__":
    asyncio.run(test_gripper())
