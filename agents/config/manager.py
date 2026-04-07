"""
agents/config/manager.py - 统一配置管理

支持多种配置加载方式：
1. 从预设加载 (load_preset)
2. 从 YAML 文件加载 (load_yaml)
3. 从关键字参数创建 (create)
4. 环境变量覆盖 (环境变量以 AGENT_ 开头)
"""

import os
import yaml
from pathlib import Path
from typing import Optional
from .schemas import AgentConfigSchema


class ConfigManager:
    """统一的配置加载和管理"""

    PRESETS_DIR = Path(__file__).parent / "presets"

    @classmethod
    def load_preset(cls, preset_name: str) -> AgentConfigSchema:
        """
        从预设加载配置

        Args:
            preset_name: 预设名称（如 'default', 'vla_plus'）

        Returns:
            AgentConfigSchema: 配置对象

        Raises:
            FileNotFoundError: 预设文件不存在
        """
        preset_file = cls.PRESETS_DIR / f"{preset_name}.yaml"

        if not preset_file.exists():
            raise FileNotFoundError(f"Preset not found: {preset_file}")

        config = cls.load_yaml(str(preset_file))

        # 应用环境变量覆盖
        config = cls._apply_env_overrides(config)

        return config

    @classmethod
    def load_yaml(cls, filepath: str) -> AgentConfigSchema:
        """
        从 YAML 文件加载配置

        Args:
            filepath: YAML 文件路径

        Returns:
            AgentConfigSchema: 配置对象

        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML 解析错误
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")

        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML: {e}")

        config = AgentConfigSchema(**data)
        # 应用环境变量覆盖
        config = cls._apply_env_overrides(config)
        return config

    @classmethod
    def create(cls, **kwargs) -> AgentConfigSchema:
        """
        从关键字参数创建配置

        Args:
            **kwargs: 配置参数

        Returns:
            AgentConfigSchema: 配置对象

        Raises:
            ValidationError: 参数验证失败
        """
        return AgentConfigSchema(**kwargs)

    @staticmethod
    def _apply_env_overrides(config: AgentConfigSchema) -> AgentConfigSchema:
        """
        应用环境变量覆盖

        以 AGENT_ 前缀的环境变量会覆盖对应的配置

        Args:
            config: 原始配置对象

        Returns:
            AgentConfigSchema: 被覆盖后的配置对象
        """
        for key, value in os.environ.items():
            if key.startswith('AGENT_'):
                attr_name = key[6:].lower()  # 移除 AGENT_ 前缀并转小写

                if hasattr(config, attr_name):
                    # 尝试转换类型（简单启发式）
                    try:
                        # 如果属性是 bool 类型
                        if isinstance(getattr(config, attr_name), bool):
                            value = value.lower() in ('true', '1', 'yes')
                        # 如果属性是 int 类型
                        elif isinstance(getattr(config, attr_name), int):
                            value = int(value)
                        # 否则保持为字符串
                    except (ValueError, TypeError):
                        pass  # 保持原值

                    setattr(config, attr_name, value)

        return config
