"""
Task 1.2: 测试 agents/config/manager.py - 统一配置管理

RED 阶段：编写失败的测试
目标：验证 ConfigManager 的配置加载和管理功能
"""

import pytest
import os
import tempfile


class TestConfigManagerLoadPreset:
    """ConfigManager 预设加载测试"""

    def test_config_manager_load_preset_default(self):
        """可以加载默认预设"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.load_preset("default")
        assert config is not None
        assert hasattr(config, 'agent_name')

    def test_config_manager_load_preset_vla_plus(self):
        """可以加载 vla_plus 预设"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.load_preset("vla_plus")
        assert config is not None
        # 应该继承或包含基础配置
        assert hasattr(config, 'agent_name') or hasattr(config, 'llm_model')

    def test_config_manager_load_invalid_preset(self):
        """加载不存在的预设应该抛出异常"""
        from agents.config.manager import ConfigManager

        with pytest.raises((FileNotFoundError, IOError, Exception)):
            ConfigManager.load_preset("nonexistent_preset")


class TestConfigManagerEnvironmentOverride:
    """ConfigManager 环境变量覆盖测试"""

    def test_config_manager_environment_override_llm_model(self):
        """环境变量可以覆盖 LLM 模型配置"""
        from agents.config.manager import ConfigManager

        # 设置环境变量
        os.environ['AGENT_LLM_MODEL'] = 'gpt-4'

        try:
            config = ConfigManager.load_preset("default")
            assert config.llm_model == 'gpt-4'
        finally:
            # 清理
            if 'AGENT_LLM_MODEL' in os.environ:
                del os.environ['AGENT_LLM_MODEL']

    def test_config_manager_environment_override_max_steps(self):
        """环境变量可以覆盖 max_steps"""
        from agents.config.manager import ConfigManager

        os.environ['AGENT_MAX_STEPS'] = '50'

        try:
            config = ConfigManager.load_preset("default")
            # 应该被覆盖为 50 或作为字符串 '50'
            assert str(config.max_steps) == '50' or config.max_steps == 50
        finally:
            if 'AGENT_MAX_STEPS' in os.environ:
                del os.environ['AGENT_MAX_STEPS']

    def test_config_manager_multiple_environment_overrides(self):
        """多个环境变量可以同时覆盖配置"""
        from agents.config.manager import ConfigManager

        os.environ['AGENT_LLM_MODEL'] = 'gpt-4'
        os.environ['AGENT_AGENT_NAME'] = 'custom_agent'

        try:
            config = ConfigManager.load_preset("default")
            assert config.llm_model == 'gpt-4'
            assert config.agent_name == 'custom_agent'
        finally:
            for key in ['AGENT_LLM_MODEL', 'AGENT_AGENT_NAME']:
                if key in os.environ:
                    del os.environ[key]


class TestConfigManagerValidation:
    """ConfigManager 配置验证测试"""

    def test_config_manager_validation_invalid_max_steps(self):
        """无效的 max_steps 应该抛出异常"""
        from agents.config.manager import ConfigManager

        with pytest.raises((ValueError, Exception)):
            ConfigManager.create(agent_name="test", max_steps=-1)

    def test_config_manager_validation_valid_config(self):
        """有效配置应该通过验证"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.create(
            agent_name="test",
            max_steps=100,
            llm_model="qwen"
        )

        assert config.agent_name == "test"
        assert config.max_steps == 100

    def test_config_manager_validation_required_field(self):
        """必需字段缺失应该抛出异常"""
        from agents.config.manager import ConfigManager

        # agent_name 可能是必需的
        with pytest.raises((TypeError, ValueError)):
            ConfigManager.create()  # 不提供任何参数


class TestConfigManagerYAMLLoading:
    """ConfigManager YAML 文件加载测试"""

    def test_config_manager_load_yaml(self, temp_config_yaml):
        """可以从 YAML 文件加载配置"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.load_yaml(temp_config_yaml)
        assert config.agent_name == "test_agent"
        assert config.max_steps == 100
        assert config.llm_model == "qwen"

    def test_config_manager_load_yaml_file_not_found(self):
        """加载不存在的 YAML 文件应该抛出异常"""
        from agents.config.manager import ConfigManager

        with pytest.raises((FileNotFoundError, IOError, Exception)):
            ConfigManager.load_yaml("/path/that/does/not/exist.yaml")

    def test_config_manager_load_yaml_invalid_format(self):
        """加载格式不正确的 YAML 应该抛出异常"""
        from agents.config.manager import ConfigManager

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [[[")
            f.flush()
            temp_file = f.name

        try:
            # 应该抛出 YAML 解析错误或其他异常
            with pytest.raises(Exception):
                ConfigManager.load_yaml(temp_file)
        finally:
            os.unlink(temp_file)


class TestConfigManagerCreate:
    """ConfigManager 直接创建测试"""

    def test_config_manager_create_from_kwargs(self):
        """可以从关键字参数创建配置"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.create(
            agent_name="my_agent",
            max_steps=50,
            llm_model="gpt-4"
        )

        assert config.agent_name == "my_agent"
        assert config.max_steps == 50
        assert config.llm_model == "gpt-4"

    def test_config_manager_create_with_defaults(self):
        """创建配置时应该使用默认值"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.create(agent_name="test")
        assert config.agent_name == "test"
        assert hasattr(config, 'max_steps')  # 应该有默认值
        assert hasattr(config, 'llm_model')  # 应该有默认值


class TestConfigManagerIntegration:
    """ConfigManager 集成测试"""

    def test_config_manager_load_and_override(self, temp_config_yaml):
        """可以加载文件后用环境变量覆盖"""
        from agents.config.manager import ConfigManager

        os.environ['AGENT_LLM_MODEL'] = 'gpt-4'

        try:
            config = ConfigManager.load_yaml(temp_config_yaml)
            # 如果支持环境变量覆盖，应该被覆盖为 gpt-4
            assert config.llm_model == 'gpt-4'
        finally:
            if 'AGENT_LLM_MODEL' in os.environ:
                del os.environ['AGENT_LLM_MODEL']

    def test_config_manager_preserves_all_fields(self):
        """ConfigManager 应该保留配置的所有字段"""
        from agents.config.manager import ConfigManager

        config = ConfigManager.create(
            agent_name="complete_config",
            max_steps=200,
            llm_model="claude",
            perception_enabled=False
        )

        assert config.agent_name == "complete_config"
        assert config.max_steps == 200
        assert config.llm_model == "claude"
        assert config.perception_enabled is False
