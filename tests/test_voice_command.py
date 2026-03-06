"""
测试语音命令组件

注意: 此测试不依赖 ROS 环境
"""
import os

os.environ["SKIP_ROS_CHECK"] = "1"
os.environ["AGENTS_DOCS_BUILD"] = "1"

import pytest
from agents.components.voice_command import VoiceCommand


def test_voice_command_init():
    """测试VoiceCommand组件初始化"""
    component = VoiceCommand(
        component_name="voice_command",
        trigger_topic="audio_input"
    )
    assert component.name == "voice_command"


def test_voice_command_has_process_method():
    """测试VoiceCommand组件有process方法"""
    component = VoiceCommand(
        component_name="voice_command",
        trigger_topic="audio_input"
    )
    assert hasattr(component, 'process')
