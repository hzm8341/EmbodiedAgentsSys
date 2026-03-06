#!/usr/bin/env python3
"""
测试机械臂控制Skills
"""
import sys
import asyncio
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

# 导入Skills
from skills.arm_control.motion_skill import MotionSkill
from skills.arm_control.gripper_skill import GripperSkill, SkillStatus
from skills.arm_control.joint_skill import JointSkill

# 统一使用同一个SkillStatus
from skills.arm_control.gripper_skill import SkillStatus


async def test_motion_skill():
    """测试运动控制Skill"""
    print("\n--- Testing MotionSkill ---")
    
    skill = MotionSkill()
    
    # 测试1: 方向移动
    print("Test 1: Move forward 0.2m")
    result = await skill.execute("move", direction="forward", distance=0.2)
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Result: {result.output}")
    
    # 测试2: 移动到预设位置
    print("Test 2: Move to 'home'")
    result = await skill.execute("move_to", target="home")
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Result: {result.output}")
    
    # 测试3: 相对移动
    print("Test 3: Move relative [0.1, 0, 0, 0, 0, 0]")
    result = await skill.execute("move_relative", position=[0.1, 0, 0, 0, 0, 0])
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Result: {result.output}")
    
    print("✓ All MotionSkill tests passed!")


async def test_gripper_skill():
    """测试夹爪控制Skill"""
    print("\n--- Testing GripperSkill ---")
    
    skill = GripperSkill()
    
    # 测试1: 打开夹爪
    print("Test 1: Open gripper")
    result = await skill.execute("open")
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Position: {result.output['position']}")
    
    # 测试2: 关闭夹爪
    print("Test 2: Close gripper")
    result = await skill.execute("close")
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Position: {result.output['position']}")
    
    # 测试3: 设置指定位置
    print("Test 3: Set position to 0.5")
    result = await skill.execute("set_position", position=0.5)
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Position: {result.output['position']}")
    
    print("✓ All GripperSkill tests passed!")


async def test_joint_skill():
    """测试关节运动Skill"""
    print("\n--- Testing JointSkill ---")
    
    skill = JointSkill(config={"joint_count": 6})
    
    # 测试1: 关节角度移动
    print("Test 1: Move joints to [0.1, 0.2, 0.3, 0.0, -0.1, 0.0]")
    result = await skill.execute("move_j", positions=[0.1, 0.2, 0.3, 0.0, -0.1, 0.0])
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Positions: {result.output['positions']}")
    
    # 测试2: 相对移动
    print("Test 2: Relative move [0.1, 0, 0, 0, 0, 0]")
    result = await skill.execute("move_j_relative", positions=[0.1, 0, 0, 0, 0, 0])
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Positions: {result.output['positions']}")
    
    # 测试3: 单一关节移动
    print("Test 3: Move joint 2 to 0.5")
    result = await skill.execute("move_single_joint", joint_index=2, angle=0.5)
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Positions: {result.output['positions']}")
    
    print("✓ All JointSkill tests passed!")


async def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("Running Arm Control Skills Tests")
    print("="*50)
    
    try:
        await test_motion_skill()
        await test_gripper_skill()
        await test_joint_skill()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50 + "\n")
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
