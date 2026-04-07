#!/usr/bin/env python3
"""
测试视觉感知Skills
"""
import sys
import asyncio
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

from skills.vision.perception_skill import PerceptionSkill, SkillStatus


async def test_perception_skill():
    """测试视觉感知Skill"""
    print("\n--- Testing PerceptionSkill ---")
    
    skill = PerceptionSkill(config={"confidence_threshold": 0.5})
    
    # 测试1: 目标检测
    print("Test 1: Detect objects in image")
    result = await skill.execute("detect", image="mock_image", classes=[])
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Detected {result.output['count']} objects")
    for det in result.output['detections']:
        print(f"    - {det['class_name']}: {det['confidence']:.2f}")
    
    # 测试2: 3D定位
    print("Test 2: Localize objects in 3D")
    result = await skill.execute("localize", image="mock_image")
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Localized {result.output['count']} objects")
    for loc in result.output['localizations']:
        pos = loc['position']
        print(f"    - {loc['class_id']}: x={pos['x']:.3f}, y={pos['y']:.3f}, z={pos['z']:.3f}")
    
    # 测试3: 分类
    print("Test 3: Classify object")
    result = await skill.execute("classify", image="mock_image", roi=[100, 100, 200, 200])
    assert result.status == SkillStatus.SUCCESS, f"Failed: {result.error}"
    print(f"  ✓ Top match: {result.output['top_match']['class_name']}")
    
    # 测试4: 便捷方法
    print("Test 4: Convenience method - detect_workpieces")
    result = await skill.detect_workpieces("mock_image")
    assert result.status == SkillStatus.SUCCESS
    print(f"  ✓ Detected {result.output['count']} workpieces")
    
    print("✓ All PerceptionSkill tests passed!")


async def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("Running Vision Perception Skills Tests")
    print("="*50)
    
    try:
        await test_perception_skill()
        
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
