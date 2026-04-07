#!/usr/bin/env python3
"""
独立测试VoiceCommand组件核心逻辑
"""
import sys
import os
import re

# 添加路径
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

# 直接读取并执行模块代码
exec(open('/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/voice_command.py').read())


def test_voice_command_init():
    """测试组件初始化"""
    vc = VoiceCommand(component_name="voice_command", trigger_topic="audio_input")
    assert vc.name == "voice_command"
    assert vc.trigger_topic == "audio_input"
    print("✓ test_voice_command_init PASSED")


def test_parse_motion_forward():
    """测试基础运动指令 - 向前"""
    vc = VoiceCommand()
    result = vc.parse("向前20厘米")
    assert result.intent == "motion"
    assert result.params["direction"] == "forward"
    assert abs(result.params["distance"] - 0.2) < 0.001
    assert result.confidence > 0.9
    print(f"✓ test_parse_motion_forward PASSED: {result.params}")


def test_parse_motion_up():
    """测试基础运动指令 - 向上"""
    vc = VoiceCommand()
    result = vc.parse("向上5cm")
    assert result.intent == "motion"
    assert result.params["direction"] == "up"
    assert abs(result.params["distance"] - 0.05) < 0.001
    print(f"✓ test_parse_motion_up PASSED: {result.params}")


def test_parse_motion_mm():
    """测试基础运动指令 - 毫米单位"""
    vc = VoiceCommand()
    result = vc.parse("向后50毫米")
    assert result.intent == "motion"
    assert result.params["direction"] == "backward"
    assert abs(result.params["distance"] - 0.05) < 0.001
    print(f"✓ test_parse_motion_mm PASSED: {result.params}")


def test_parse_gripper_open():
    """测试夹爪动作 - 打开"""
    vc = VoiceCommand()
    result = vc.parse("把夹爪打开")
    assert result.intent == "gripper"
    assert result.params["action"] == "open"
    print(f"✓ test_parse_gripper_open PASSED: {result.params}")


def test_parse_gripper_close():
    """测试夹爪动作 - 关闭"""
    vc = VoiceCommand()
    result = vc.parse("关闭夹爪")
    assert result.intent == "gripper"
    assert result.params["action"] == "close"
    print(f"✓ test_parse_gripper_close PASSED: {result.params}")


def test_parse_move_to_position():
    """测试移动到预设位置"""
    vc = VoiceCommand()
    result = vc.parse("移动到料框上方")
    assert result.intent == "composite"
    assert result.params["action"] == "move_to"
    assert result.params["target"] == "bin"
    print(f"✓ test_parse_move_to_position PASSED: {result.params}")


def test_parse_task_level():
    """测试任务级指令"""
    vc = VoiceCommand()
    result = vc.parse("把零件拿到拍照位置")
    assert result.intent == "task"
    assert result.params["action"] == "transfer"
    assert result.params["source"] == "零件"
    assert result.params["target"] == "拍照位置"
    print(f"✓ test_parse_task_level PASSED: {result.params}")


def test_parse_task_level_2():
    """测试任务级指令 - 变体"""
    vc = VoiceCommand()
    result = vc.parse("把托盘放到产线上")
    assert result.intent == "task"
    assert result.params["action"] == "transfer"
    print(f"✓ test_parse_task_level_2 PASSED: {result.params}")


def test_parse_unknown():
    """测试无法解析的指令"""
    vc = VoiceCommand()
    result = vc.parse("你好")
    assert result.intent == "unknown"
    assert result.confidence == 0.0
    print(f"✓ test_parse_unknown PASSED")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("Running VoiceCommand Component Tests")
    print("="*50 + "\n")
    
    tests = [
        test_voice_command_init,
        test_parse_motion_forward,
        test_parse_motion_up,
        test_parse_motion_mm,
        test_parse_gripper_open,
        test_parse_gripper_close,
        test_parse_move_to_position,
        test_parse_task_level,
        test_parse_task_level_2,
        test_parse_unknown,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*50 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
