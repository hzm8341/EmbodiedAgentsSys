#!/usr/bin/env python3
"""
测试机械臂控制Skills - 带调试
"""
import sys
import asyncio
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

# 导入Skills
from skills.arm_control.motion_skill import MotionSkill, SkillStatus


async def test_motion_skill():
    """测试运动控制Skill"""
    print("\n--- Testing MotionSkill ---")
    
    skill = MotionSkill()
    
    # 测试1: 方向移动
    print("Test 1: Move forward 0.2m")
    try:
        result = await skill.execute("move", direction="forward", distance=0.2)
        print(f"  Status: {result.status}")
        print(f"  Output: {result.output}")
        print(f"  Error: {result.error}")
        print(f"  Metadata: {result.metadata}")
        assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
        print(f"  ✓ Result: {result.output}")
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    print("✓ All MotionSkill tests passed!")


async def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("Running Arm Control Skills Tests")
    print("="*50)
    
    try:
        await test_motion_skill()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
