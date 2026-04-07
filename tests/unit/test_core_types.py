"""
Task 1.1: 测试 agents/core/ 纯 Python 核心

RED 阶段：编写失败的测试
目标：验证基础类型定义（RobotObservation、SkillResult、AgentConfig）
"""

import pytest
import sys


class TestRobotObservation:
    """RobotObservation 基础类型测试"""

    def test_robot_observation_creation(self):
        """RobotObservation 可以创建"""
        from agents.core.types import RobotObservation

        obs = RobotObservation(
            image=None,
            state={"joint_0": 0.5},
            gripper={"position": 0.8},
            timestamp=1000.0
        )

        assert obs.state["joint_0"] == 0.5
        assert obs.timestamp == 1000.0

    def test_robot_observation_default_timestamp(self):
        """RobotObservation 如果不提供 timestamp，应该使用当前时间"""
        from agents.core.types import RobotObservation

        obs = RobotObservation(state={})
        assert obs.timestamp > 0

    def test_robot_observation_empty_state(self):
        """RobotObservation 可以有空状态"""
        from agents.core.types import RobotObservation

        obs = RobotObservation()
        assert obs.state == {}
        assert obs.gripper == {}


class TestSkillResult:
    """SkillResult 基础类型测试"""

    def test_skill_result_success(self):
        """SkillResult 可以表示成功"""
        from agents.core.types import SkillResult

        result = SkillResult(
            success=True,
            message="Task completed",
            data={"xyz": [1, 2, 3]}
        )

        assert result.success is True
        assert result.message == "Task completed"
        assert result.data["xyz"] == [1, 2, 3]

    def test_skill_result_failure(self):
        """SkillResult 可以表示失败"""
        from agents.core.types import SkillResult

        result = SkillResult(
            success=False,
            message="Failed to reach target"
        )

        assert result.success is False
        assert "reach target" in result.message

    def test_skill_result_with_complex_data(self):
        """SkillResult 可以包含复杂的数据结构"""
        from agents.core.types import SkillResult

        data = {
            "trajectory": [[0, 0, 0], [1, 1, 1]],
            "execution_time": 2.5,
            "forces": {"fx": 1.2, "fy": 0.3}
        }

        result = SkillResult(success=True, message="ok", data=data)
        assert result.data["trajectory"][1][0] == 1
        assert result.data["execution_time"] == 2.5


class TestAgentConfig:
    """AgentConfig 配置类型测试"""

    def test_agent_config_creation(self):
        """AgentConfig 可以创建"""
        from agents.core.types import AgentConfig

        config = AgentConfig(
            agent_name="test_agent",
            max_steps=100,
            llm_model="qwen",
            perception_enabled=True
        )

        assert config.agent_name == "test_agent"
        assert config.max_steps == 100
        assert config.llm_model == "qwen"

    def test_agent_config_default_values(self):
        """AgentConfig 有合理的默认值"""
        from agents.core.types import AgentConfig

        config = AgentConfig(agent_name="default")
        assert config.max_steps == 100  # 默认值
        assert config.llm_model == "qwen"  # 默认值
        assert config.perception_enabled is True  # 默认值

    def test_agent_config_validation_max_steps(self):
        """AgentConfig 应该验证 max_steps >= 1"""
        from agents.core.types import AgentConfig

        with pytest.raises((ValueError, Exception)):
            AgentConfig(agent_name="test", max_steps=-1)

        with pytest.raises((ValueError, Exception)):
            AgentConfig(agent_name="test", max_steps=0)

        # 正常值应该通过
        config = AgentConfig(agent_name="test", max_steps=1)
        assert config.max_steps == 1


class TestCoreNoROS2Dependency:
    """验证 core 模块不依赖 ROS2"""

    def test_core_types_no_ros2_import(self):
        """agents.core.types 模块不应该导入 ROS2"""
        # 清除任何现有的 ROS2 导入
        for key in list(sys.modules.keys()):
            if 'ros' in key.lower() or 'rclpy' in key.lower():
                del sys.modules[key]

        # 导入 core 模块
        from agents.core import types

        # 验证 ROS2 没有被导入
        assert 'rclpy' not in sys.modules
        for key in sys.modules.keys():
            if 'rclpy' in key:
                pytest.fail(f"Found ROS2 import: {key}")

    def test_core_types_can_be_imported_standalone(self):
        """agents.core.types 可以独立导入（不需要 ROS2）"""
        # 不应该抛出导入错误
        from agents.core.types import RobotObservation, SkillResult, AgentConfig

        assert RobotObservation is not None
        assert SkillResult is not None
        assert AgentConfig is not None
