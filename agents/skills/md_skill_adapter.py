"""
通用 MD Skill 适配器框架

支持:
- 任意 MD 格式的 Skill 定义
- 可插拔的解析器
- 可插拔的代码验证器
- 可插拔的代码生成器
- 动态 Skill 管理

设计原则:
- 抽象基类定义接口
- 具体实现可定制
- 配置驱动而非硬编码
"""

import os
import re
import ast
import logging
import importlib
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from agents.skills import (
    BaseSkill,
    SkillMetadata,
    SkillResult,
    SkillStatus,
    skill_registry,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# 1. 通用配置类
# ============================================================


@dataclass
class MDSkillConfig:
    """通用 MD Skill 配置"""

    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)
    references: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=dict)
    when_to_use: List[str] = field(default_factory=list)
    safety_notes: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeValidationResult:
    """代码验证结果"""

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    syntax_ok: bool = True

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)


# ============================================================
# 2. 抽象基类 (可扩展)
# ============================================================


class MDParser(ABC):
    """MD 解析器抽象基类"""

    @abstractmethod
    def parse(self, skill_dir: str) -> MDSkillConfig:
        """解析 skill 目录"""
        pass

    @abstractmethod
    def get_parser_name(self) -> str:
        """解析器名称"""
        pass


class CodeValidator(ABC):
    """代码验证器抽象基类"""

    @abstractmethod
    def validate(self, code: str) -> CodeValidationResult:
        """验证代码"""
        pass

    @abstractmethod
    def get_validator_name(self) -> str:
        """验证器名称"""
        pass


class CodeGenerator(ABC):
    """代码生成器抽象基类"""

    @abstractmethod
    def generate(self, description: str, context: Dict[str, Any]) -> str:
        """生成代码"""
        pass

    @abstractmethod
    def get_generator_name(self) -> str:
        """生成器名称"""
        pass


# ============================================================
# 3. 默认解析器 (支持 SKILL.md 格式)
# ============================================================


class SKILLMDParser(MDParser):
    """标准 SKILL.md 解析器"""

    def __init__(self, format_config: Dict[str, Any] = None):
        self.format_config = format_config or self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "frontmatter_pattern": r"^---\n(.*?)\n---",
            "rules_header": "生成代码规则",
            "when_to_use_header": "何时使用本技能",
            "safety_header": "安全注意事项",
        }

    def get_parser_name(self) -> str:
        return "SKILL.md Parser"

    def parse(self, skill_dir: str) -> MDSkillConfig:
        skill_path = Path(skill_dir)

        md_files = list(skill_path.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"No .md file found in {skill_dir}")

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            skill_md = md_files[0]

        content = skill_md.read_text()

        config = self._parse_frontmatter(content)
        config.rules = self._parse_section(content, self.format_config["rules_header"])
        config.when_to_use = self._parse_list_section(
            content, self.format_config["when_to_use_header"]
        )
        config.safety_notes = self._parse_list_section(
            content, self.format_config["safety_header"]
        )

        references_dir = skill_path / "references"
        if references_dir.exists():
            for ref_file in references_dir.glob("*.md"):
                config.references[ref_file.stem] = ref_file.read_text()

        logger.info(f"Parsed skill: {config.name}")
        return config

    def _parse_frontmatter(self, content: str) -> MDSkillConfig:
        import yaml

        pattern = self.format_config["frontmatter_pattern"]
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            raise ValueError("Invalid SKILL.md format: missing frontmatter")

        frontmatter = yaml.safe_load(match.group(1))

        return MDSkillConfig(
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
            metadata=frontmatter.get("metadata", {}),
        )

    def _parse_section(self, content: str, header: str) -> List[str]:
        rules = []

        pattern = rf"##\s*{header}\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(1)
            lines = section.split("\n")
            current_rule = ""

            for line in lines:
                if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.")):
                    if current_rule:
                        rules.append(current_rule.strip())
                    current_rule = line
                else:
                    current_rule += " " + line.strip()

            if current_rule:
                rules.append(current_rule.strip())

        return rules

    def _parse_list_section(self, content: str, header: str) -> List[str]:
        items = []

        pattern = rf"##\s*{header}\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(1)
            for line in section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    items.append(line.lstrip("- ").strip())

        return items


# ============================================================
# 4. 通用 Skill 实现
# ============================================================


class MDSkill(BaseSkill):
    """通用 MD Skill"""

    def __init__(
        self,
        skill_dir: str,
        parser: MDParser = None,
        validator: CodeValidator = None,
        generator: CodeGenerator = None,
        llm_client=None,
        validate_code: bool = True,
        **kwargs,
    ):
        self.parser = parser or SKILLMDParser()
        self.validator = validator
        self.generator = generator
        self.llm_client = llm_client
        self.validate_code = validate_code

        self.config = self.parser.parse(skill_dir)

        self.metadata = SkillMetadata(
            name=self.config.name,
            description=self.config.description,
            inputs={"user_description": str, "context": dict},
            outputs={"generated_code": str},
            tags=self.config.metadata.get("tags", []),
        )

        self._skill_dir = skill_dir

    async def validate_inputs(self, **kwargs) -> bool:
        return "user_description" in kwargs

    async def execute(
        self, user_description: str, context: Dict[str, Any] = None
    ) -> SkillResult:
        context = context or {}

        try:
            if self.llm_client:
                code = await self._generate_with_llm(user_description)
            elif self.generator:
                code = self.generator.generate(
                    user_description, {**context, "config": self.config}
                )
            else:
                code = f"# TODO: Implement generation for {self.config.name}\n# Description: {user_description}"

            validation_result = None
            if self.validate_code and self.validator:
                validation_result = self.validator.validate(code)

            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={
                    "generated_code": code,
                    "description": user_description,
                    "context": context,
                    "validation": {
                        "is_valid": validation_result.is_valid
                        if validation_result
                        else True,
                        "errors": validation_result.errors if validation_result else [],
                        "warnings": validation_result.warnings
                        if validation_result
                        else [],
                    },
                },
                metadata={
                    "skill_name": self.config.name,
                    "parser": self.parser.get_parser_name(),
                    "validator": self.validator.get_validator_name()
                    if self.validator
                    else None,
                    "rules_count": len(self.config.rules),
                },
            )

        except Exception as e:
            logger.error(f"MDSkill execution failed: {e}")
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    async def _generate_with_llm(self, description: str) -> str:
        prompt = self._build_prompt(description)
        response = await self.llm_client.generate(prompt)
        return self._extract_code(response)

    def _build_prompt(self, description: str) -> str:
        rules_text = "\n".join(f"- {rule}" for rule in self.config.rules)

        refs_text = ""
        for name, content in self.config.references.items():
            refs_text += f"\n## {name}\n{content[:500]}..."

        prompt = f"""你是一个技能代码生成专家。

请根据用户的描述生成代码。

## 用户描述
{description}

## 生成规则
{rules_text}

## 参考资料
{refs_text}

请直接输出代码。"""

        return prompt

    def _extract_code(self, response: str) -> str:
        patterns = [
            r"```python\n(.*?)```",
            r"```\n(.*?)```",
            r"```python\r\n(.*?)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        return response.strip()


# ============================================================
# 5. Skill 管理器
# ============================================================


class MDSkillManager:
    """通用 MD Skill 管理器"""

    def __init__(
        self,
        skills_base_dir: str = None,
        parser: MDParser = None,
        validator: CodeValidator = None,
        generator: CodeGenerator = None,
    ):
        self.skills_base_dir = Path(skills_base_dir or "skills")
        self.parser = parser or SKILLMDParser()
        self.validator = validator
        self.generator = generator

        self.loaded_configs: Dict[str, MDSkillConfig] = {}
        self.skill_instances: Dict[str, MDSkill] = {}

    def discover_skills(self) -> List[str]:
        if not self.skills_base_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_base_dir}")
            return []

        skills = []
        for item in self.skills_base_dir.iterdir():
            if item.is_dir() and any(item.glob("*.md")):
                skills.append(item.name)

        logger.info(f"Discovered skills: {skills}")
        return skills

    def load_config(self, skill_name: str) -> MDSkillConfig:
        skill_dir = self.skills_base_dir / skill_name
        config = self.parser.parse(str(skill_dir))
        self.loaded_configs[skill_name] = config
        return config

    def get_skill(
        self,
        skill_name: str,
        llm_client=None,
        validator: CodeValidator = None,
        generator: CodeGenerator = None,
    ) -> MDSkill:
        if skill_name not in self.loaded_configs:
            self.load_config(skill_name)

        skill_dir = str(self.skills_base_dir / skill_name)

        instance = MDSkill(
            skill_dir=skill_dir,
            parser=self.parser,
            validator=validator or self.validator,
            generator=generator or self.generator,
            llm_client=llm_client,
        )

        self.skill_instances[skill_name] = instance
        return instance

    async def execute(
        self,
        skill_name: str,
        description: str,
        llm_client=None,
        **kwargs,
    ) -> SkillResult:
        skill = self.get_skill(skill_name, llm_client)
        return await skill.execute(description, kwargs)

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "description": config.description,
                "rules_count": len(config.rules),
                "when_to_use": config.when_to_use,
                "safety_notes": config.safety_notes,
                "references": list(config.references.keys()),
            }
            for name, config in self.loaded_configs.items()
        }


# ============================================================
# 6. 工厂函数
# ============================================================


def create_skill_manager(
    skills_dir: str = None,
    parser_config: Dict[str, Any] = None,
) -> MDSkillManager:
    parser = SKILLMDParser(parser_config) if parser_config else None
    return MDSkillManager(skills_base_dir=skills_dir, parser=parser)


def register_mdskill(
    name: str,
    description: str = "",
    tags: List[str] = None,
):
    """装饰器: 注册 MD Skill"""

    def decorator(skill_class: Type[MDSkill]):
        @skill_registry.register(name, description, tags or [])
        class RegisteredSkill(skill_class):
            pass

        return skill_class

    return decorator
