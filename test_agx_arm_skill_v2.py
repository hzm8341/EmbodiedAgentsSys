#!/usr/bin/env python3
"""
测试 agx-arm-codegen Skill 功能

验证:
1. 解析 SKILL.md 配置
2. 生成代码
3. 代码验证
4. Skill 管理器
5. 多种场景

注意: 此测试不依赖 ROS 环境
"""

import os

os.environ["SKILL_CHECK"] = "1"

import asyncio
import sys
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


# ============================================================
# 简化依赖
# ============================================================


class SkillStatus:
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class SkillResult:
    status: str
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillMetadata:
    name: str
    description: str
    inputs: Dict[str, type] = field(default_factory=dict)
    outputs: Dict[str, type] = field(default_factory=dict)
    tags: list = field(default_factory=list)


class BaseSkill:
    metadata: SkillMetadata

    def __init__(self, **kwargs):
        pass

    async def execute(self, **kwargs) -> SkillResult:
        raise NotImplementedError

    async def validate_inputs(self, **kwargs) -> bool:
        raise NotImplementedError


# ============================================================
# 解析器
# ============================================================


@dataclass
class OpenClawSkillConfig:
    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)
    references: Dict[str, str] = field(default_factory=dict)
    when_to_use: List[str] = field(default_factory=list)
    safety_notes: List[str] = field(default_factory=list)


class OpenClawSkillParser:
    @staticmethod
    def parse(skill_dir: str) -> OpenClawSkillConfig:
        skill_path = Path(skill_dir)
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")

        content = skill_md.read_text()
        config = OpenClawSkillParser._parse_frontmatter(content)
        config.rules = OpenClawSkillParser._parse_rules(content)
        config.when_to_use = OpenClawSkillParser._parse_when_to_use(content)
        config.safety_notes = OpenClawSkillParser._parse_safety_notes(content)

        references_dir = skill_path / "references"
        if references_dir.exists():
            for ref_file in references_dir.glob("*.md"):
                config.references[ref_file.stem] = ref_file.read_text()

        return config

    @staticmethod
    def _parse_frontmatter(content: str) -> OpenClawSkillConfig:
        pattern = r"^---\n(.*?)\n---"
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            raise ValueError("Invalid SKILL.md format: missing frontmatter")
        frontmatter = yaml.safe_load(match.group(1))
        return OpenClawSkillConfig(
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
            metadata=frontmatter.get("metadata", {}),
        )

    @staticmethod
    def _parse_rules(content: str) -> List[str]:
        rules = []
        pattern = r"##\s*生成代码规则\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            rule_section = match.group(1)
            lines = rule_section.split("\n")
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

    @staticmethod
    def _parse_when_to_use(content: str) -> List[str]:
        when_to_use = []
        pattern = r"##\s*何时使用本技能\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            section = match.group(1)
            for line in section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    when_to_use.append(line.lstrip("- ").strip())
        return when_to_use

    @staticmethod
    def _parse_safety_notes(content: str) -> List[str]:
        safety_notes = []
        pattern = r"##\s*安全注意事项\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            section = match.group(1)
            for line in section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    safety_notes.append(line.lstrip("- ").strip())
        return safety_notes


# ============================================================
# 代码验证器
# ============================================================


class CodeValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []


class CodeValidator:
    RISKY_PATTERNS = [
        ("move_js", "move_js 是快速响应模式，请谨慎使用"),
        ("move_mit", "MIT 模式是高风险操作"),
    ]

    @staticmethod
    def validate(code: str) -> CodeValidationResult:
        result = CodeValidationResult()

        if "pyAgxArm" not in code:
            result.errors.append("缺少 pyAgxArm 导入")

        if "def main" not in code:
            result.errors.append("缺少 main 函数")

        if "robot.enable" not in code:
            result.warnings.append("缺少 enable 调用")

        for pattern, warning in CodeValidator.RISKY_PATTERNS:
            if pattern in code:
                result.warnings.append(f"风险: {warning}")

        if result.errors:
            result.is_valid = False

        return result


# ============================================================
# 代码生成器
# ============================================================


class CodeGenerator:
    @staticmethod
    def generate_template(description: str, robot_type: str = "nero") -> str:
        return f'''#!/usr/bin/env python3
"""
Generated by agx-arm-codegen Skill
Description: {description}
Robot: {robot_type}
"""

import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory


def wait_motion_done(robot, timeout: float = 3.0, poll_interval: float = 0.01) -> bool:
    start_t = time.monotonic()
    while True:
        status = robot.get_arm_status()
        if status is not None and getattr(status.msg, "motion_status", None) == 0:
            return True
        if time.monotonic() - start_t > timeout:
            return False
        time.sleep(poll_interval)


def main():
    robot_cfg = create_agx_arm_config(
        robot="{robot_type}",
        comm="can",
        channel="can0",
        interface="socketcan",
    )
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()
    
    time.sleep(1)
    robot.set_normal_mode()
    time.sleep(1)
    
    while not robot.enable():
        time.sleep(0.01)
    
    robot.set_speed_percent(80)
    
    # === 用户请求: {description} ===
    robot.set_motion_mode(robot.MOTION_MODE.J)
    robot.move_j([0.0] * 7)
    wait_motion_done(robot)


if __name__ == "__main__":
    main()
'''


# ============================================================
# Skill 实现
# ============================================================


class AgxArmCodeGenSkill(BaseSkill):
    def __init__(
        self, skill_dir: str = None, llm_client=None, validate_code: bool = True
    ):
        if skill_dir is None:
            skill_dir = "/media/hzm/data_disk/ros-agents/skills/agx_arm_codegen"

        self.config = OpenClawSkillParser.parse(skill_dir)
        self.llm_client = llm_client
        self.validate_code = validate_code

        self.metadata = SkillMetadata(
            name=self.config.name,
            description=self.config.description,
            inputs={"user_description": str},
            outputs={"generated_code": str},
            tags=["codegen", "robotics", "arm"],
        )

    async def validate_inputs(self, **kwargs) -> bool:
        return "user_description" in kwargs

    async def execute(
        self, user_description: str, robot_type: str = "nero"
    ) -> SkillResult:
        try:
            prompt = self._build_prompt(user_description)

            if self.llm_client:
                response = await self.llm_client.generate(prompt)
                code = self._extract_code(response)
            else:
                code = CodeGenerator.generate_template(user_description, robot_type)

            validation = None
            if self.validate_code:
                validation = CodeValidator.validate(code)

            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={
                    "generated_code": code,
                    "description": user_description,
                    "validation": {
                        "is_valid": validation.is_valid if validation else True,
                        "errors": validation.errors if validation else [],
                        "warnings": validation.warnings if validation else [],
                    },
                },
                metadata={
                    "skill_name": self.config.name,
                    "rules_applied": len(self.config.rules),
                },
            )
        except Exception as e:
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    def _build_prompt(self, user_description: str) -> str:
        rules_text = "\n".join(f"- {rule}" for rule in self.config.rules)
        api_ref = self.config.references.get("pyagxarm-api", "")
        return f"""生成 pyAgxArm 代码。用户描述: {user_description}"""

    def _extract_code(self, response: str) -> str:
        pattern = r"```python\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()


# ============================================================
# Skill 管理器
# ============================================================


class OpenClawSkillManager:
    def __init__(self, skills_base_dir: str = None):
        if skills_base_dir is None:
            skills_base_dir = "/media/hzm/data_disk/ros-agents/skills"
        self.skills_base_dir = Path(skills_base_dir)
        self.loaded_skills: Dict[str, OpenClawSkillConfig] = {}

    def discover_skills(self) -> List[str]:
        if not self.skills_base_dir.exists():
            return []
        skills = []
        for item in self.skills_base_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skills.append(item.name)
        return skills

    def load_skill(self, skill_name: str) -> OpenClawSkillConfig:
        skill_dir = self.skills_base_dir / skill_name
        config = OpenClawSkillParser.parse(str(skill_dir))
        self.loaded_skills[skill_name] = config
        return config

    def get_skill_instance(
        self, skill_name: str, llm_client=None
    ) -> AgxArmCodeGenSkill:
        if skill_name not in self.loaded_skills:
            self.load_skill(skill_name)
        skill_dir = str(self.skills_base_dir / skill_name)
        return AgxArmCodeGenSkill(skill_dir=skill_dir, llm_client=llm_client)


# ============================================================
# 测试用例
# ============================================================


async def test_parser():
    """测试 1: SKILL.md 解析"""
    print("\n" + "=" * 60)
    print("测试 1: SKILL.md 解析")
    print("=" * 60)

    skill_dir = "/media/hzm/data_disk/ros-agents/skills/agx_arm_codegen"
    config = OpenClawSkillParser.parse(skill_dir)

    print(f"Name: {config.name}")
    print(f"Description: {config.description[:50]}...")
    print(f"Rules: {len(config.rules)}")
    print(f"When to use: {len(config.when_to_use)} items")
    print(f"Safety notes: {len(config.safety_notes)} items")
    print(f"References: {list(config.references.keys())}")

    assert config.name == "agx-arm-codegen"
    assert len(config.rules) > 0
    assert len(config.when_to_use) > 0
    assert len(config.safety_notes) > 0

    print("✓ 解析成功")
    return config


async def test_code_generator():
    """测试 2: 代码生成器"""
    print("\n" + "=" * 60)
    print("测试 2: 代码生成器")
    print("=" * 60)

    code = CodeGenerator.generate_template("移动到 HOME", "nero")

    print(f"代码长度: {len(code)}")
    print(f"包含 pyAgxArm: {'pyAgxArm' in code}")
    print(f"包含 main: {'def main' in code}")
    print(f"包含 enable: {'robot.enable' in code}")
    print(f"包含 wait_motion_done: {'wait_motion_done' in code}")

    assert "pyAgxArm" in code
    assert "def main" in code
    assert "robot.enable" in code

    print("✓ 代码生成成功")


async def test_code_validator():
    """测试 3: 代码验证器"""
    print("\n" + "=" * 60)
    print("测试 3: 代码验证器")
    print("=" * 60)

    # 测试有效代码
    valid_code = """import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

def main():
    robot_cfg = create_agx_arm_config(robot="nero")
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()
    while not robot.enable():
        time.sleep(0.01)
    robot.set_normal_mode()
"""

    result = CodeValidator.validate(valid_code)
    print(f"有效代码验证: valid={result.is_valid}, errors={result.errors}")
    assert result.is_valid == True

    # 测试无效代码
    invalid_code = """def main():
    print("hello")
"""
    result2 = CodeValidator.validate(invalid_code)
    print(f"无效代码验证: valid={result2.is_valid}, errors={result2.errors}")
    assert result2.is_valid == False

    # 测试风险代码
    risky_code = """from pyAgxArm import create_agx_arm_config

def main():
    robot.move_js([0,0,0,0,0,0,0])
"""
    result3 = CodeValidator.validate(risky_code)
    print(f"风险代码验证: warnings={result3.warnings}")
    assert len(result3.warnings) > 0

    print("✓ 代码验证成功")


async def test_skill_execution():
    """测试 4: Skill 执行"""
    print("\n" + "=" * 60)
    print("测试 4: Skill 执行")
    print("=" * 60)

    skill = AgxArmCodeGenSkill(validate_code=True)

    descriptions = [
        "让机械臂移动到 HOME 位置",
        "控制机械臂抓取物体",
        "画一个圆形轨迹",
    ]

    for desc in descriptions:
        result = await skill.execute(desc, robot_type="nero")

        print(f"\n描述: {desc}")
        print(f"状态: {result.status}")

        assert result.status == SkillStatus.SUCCESS

        validation = result.output.get("validation", {})
        print(f"验证: valid={validation.get('is_valid')}")

        code = result.output.get("generated_code", "")
        print(f"代码长度: {len(code)}")

    print("\n✓ Skill 执行成功")


async def test_mock_llm():
    """测试 5: 模拟 LLM 生成"""
    print("\n" + "=" * 60)
    print("测试 5: 模拟 LLM 生成")
    print("=" * 60)

    class MockLLMClient:
        async def generate(self, prompt):
            return """```python
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory

def main():
    robot_cfg = create_agx_arm_config(robot="nero", comm="can", channel="can0")
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()
    
    time.sleep(1)
    robot.set_normal_mode()
    time.sleep(1)
    
    while not robot.enable():
        time.sleep(0.01)
    
    robot.set_motion_mode(robot.MOTION_MODE.J)
    robot.move_j([0.0, 0.5, -0.3, 0.0, 0.0, 0.0, 0.0])
    print("Moved to position!")

if __name__ == "__main__":
    main()
```"""

    skill = AgxArmCodeGenSkill(llm_client=MockLLMClient(), validate_code=True)

    result = await skill.execute("移动到指定关节角度")

    print(f"状态: {result.status}")
    assert result.status == SkillStatus.SUCCESS

    code = result.output.get("generated_code", "")
    print(f"代码长度: {len(code)}")
    print(f"包含 move_j: {'move_j' in code}")

    validation = result.output.get("validation", {})
    print(f"验证通过: {validation.get('is_valid')}")

    print("\n✓ LLM 生成成功")


async def test_skill_manager():
    """测试 6: Skill 管理器"""
    print("\n" + "=" * 60)
    print("测试 6: Skill 管理器")
    print("=" * 60)

    manager = OpenClawSkillManager()

    # 发现 skills
    skills = manager.discover_skills()
    print(f"发现 skills: {skills}")
    assert "agx_arm_codegen" in skills

    # 加载 skill
    config = manager.load_skill("agx_arm_codegen")
    print(f"加载: {config.name}")
    assert "agx" in config.name  # 允许带连字符或下划线

    # 获取实例
    instance = manager.get_skill_instance("agx_arm_codegen")
    print(f"实例创建成功")

    # 执行
    result = await instance.execute("测试执行")
    print(f"执行状态: {result.status}")
    assert result.status == SkillStatus.SUCCESS

    print("\n✓ Skill 管理器成功")


async def test_multiple_robot_types():
    """测试 7: 多种机器人类型"""
    print("\n" + "=" * 60)
    print("测试 7: 多种机器人类型")
    print("=" * 60)

    skill = AgxArmCodeGenSkill(validate_code=False)

    robot_types = ["nero", "piper", "piper_h"]

    for robot_type in robot_types:
        result = await skill.execute("回零", robot_type=robot_type)

        assert result.status == SkillStatus.SUCCESS

        code = result.output.get("generated_code", "")
        assert f'robot="{robot_type}"' in code
        print(f"{robot_type}: OK")

    print("\n✓ 多种机器人类型成功")


async def test_validation_integration():
    """测试 8: 验证集成"""
    print("\n" + "=" * 60)
    print("测试 8: 验证集成")
    print("=" * 60)

    skill = AgxArmCodeGenSkill(validate_code=True)

    result = await skill.execute("移动机械臂")

    validation = result.output.get("validation", {})

    print(f"验证通过: {validation.get('is_valid')}")
    print(f"错误: {validation.get('errors', [])}")
    print(f"警告: {validation.get('warnings', [])}")

    assert validation.get("is_valid") == True
    assert len(validation.get("errors", [])) == 0

    print("\n✓ 验证集成成功")


async def main():
    print("=" * 60)
    print("agx-arm-codegen 完整功能测试")
    print("=" * 60)

    try:
        await test_parser()
        await test_code_generator()
        await test_code_validator()
        await test_skill_execution()
        await test_mock_llm()
        await test_skill_manager()
        await test_multiple_robot_types()
        await test_validation_integration()

        print("\n" + "=" * 60)
        print("🎉 所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
