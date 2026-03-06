"""
OpenClaw Skill Adapter for EmbodiedAgents

将 OpenClaw 格式的 skill 集成到我们的 Skills 框架中。

支持:
- 解析 SKILL.md 定义
- 根据自然语言生成代码
- 与现有 Components 集成
- 代码验证
- 动态 Skill 管理
"""

import os
import re
import ast
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

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
# 数据类定义
# ============================================================


@dataclass
class OpenClawSkillConfig:
    """OpenClaw Skill 配置"""

    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)
    references: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=dict)
    when_to_use: List[str] = field(default_factory=list)
    safety_notes: List[str] = field(default_factory=list)


class CodeValidationResult:
    """代码验证结果"""

    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.syntax_ok: bool = True

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)


# ============================================================
# 解析器
# ============================================================


class OpenClawSkillParser:
    """解析 OpenClaw 格式的 SKILL.md"""

    @staticmethod
    def parse(skill_dir: str) -> OpenClawSkillConfig:
        """
        解析 skill 目录

        Args:
            skill_dir: skill 目录路径

        Returns:
            OpenClawSkillConfig
        """
        skill_path = Path(skill_dir)

        # 读取 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")

        content = skill_md.read_text()

        # 解析 YAML frontmatter
        config = OpenClawSkillParser._parse_frontmatter(content)

        # 解析各种规则
        config.rules = OpenClawSkillParser._parse_rules(content)
        config.when_to_use = OpenClawSkillParser._parse_when_to_use(content)
        config.safety_notes = OpenClawSkillParser._parse_safety_notes(content)

        # 读取 references
        references_dir = skill_path / "references"
        if references_dir.exists():
            for ref_file in references_dir.glob("*.md"):
                config.references[ref_file.stem] = ref_file.read_text()

        logger.info(f"Parsed skill: {config.name} with {len(config.rules)} rules")
        return config

    @staticmethod
    def _parse_frontmatter(content: str) -> OpenClawSkillConfig:
        """解析 YAML frontmatter"""
        import yaml

        # 提取 frontmatter
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
        """解析生成代码规则"""
        rules = []

        # 提取 ## 生成代码规则 后的内容
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
        """解析何时使用"""
        when_to_use = []

        pattern = r"##\s*何时使用本技能\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(1)
            # 提取列表项
            for line in section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    when_to_use.append(line.lstrip("- ").strip())

        return when_to_use

    @staticmethod
    def _parse_safety_notes(content: str) -> List[str]:
        """解析安全注意事项"""
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


class CodeValidator:
    """验证生成的代码"""

    # 必需导入
    REQUIRED_IMPORTS = ["time", "pyAgxArm"]

    # 必需函数
    REQUIRED_FUNCTIONS = ["main"]

    # 推荐包含
    RECOMMENDED_PATTERNS = [
        "create_agx_arm_config",
        "AgxArmFactory.create_arm",
        "robot.connect",
        "robot.enable",
        "robot.set_normal_mode",
    ]

    # 高风险模式 (需要警告)
    RISKY_PATTERNS = [
        ("move_js", "move_js 是快速响应模式，请谨慎使用"),
        ("move_mit", "MIT 模式是高风险操作，请确保了解后果"),
        ("electronic_emergency_stop", "这是急停操作"),
    ]

    @staticmethod
    def validate(code: str) -> CodeValidationResult:
        """验证代码"""
        result = CodeValidationResult()

        # 1. 语法检查
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.syntax_ok = False
            result.add_error(f"语法错误: {e}")
            return result

        # 2. 检查必需导入
        for imp in CodeValidator.REQUIRED_IMPORTS:
            if imp not in code:
                result.add_warning(f"建议导入: {imp}")

        # 3. 检查必需函数
        for func in CodeValidator.REQUIRED_FUNCTIONS:
            if f"def {func}" not in code:
                result.add_error(f"缺少必需函数: {func}")

        # 4. 检查推荐模式
        for pattern in CodeValidator.RECOMMENDED_PATTERNS:
            if pattern not in code:
                result.add_warning(f"建议添加: {pattern}")

        # 5. 检查风险模式
        for pattern, warning in CodeValidator.RISKY_PATTERNS:
            if pattern in code:
                result.add_warning(f"高风险: {warning}")

        # 6. 检查必需的运动序列
        if "robot.enable()" not in code and "robot.enable()" not in code.replace(
            " ", ""
        ):
            result.add_error("缺少 robot.enable() 调用")

        if "robot.set_normal_mode()" not in code:
            result.add_warning("建议显式设置 normal 模式")

        return result


# ============================================================
# 代码生成器
# ============================================================


class CodeGenerator:
    """代码生成器"""

    @staticmethod
    def generate_template(
        description: str,
        robot_type: str = "nero",
        include_disable: bool = False,
    ) -> str:
        """生成基础模板代码"""

        template = f'''#!/usr/bin/env python3
"""
Generated by agx-arm-codegen Skill
Description: {description}
Robot: {robot_type}
"""

import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory


def wait_motion_done(robot, timeout: float = 3.0, poll_interval: float = 0.01) -> bool:
    """等待运动完成
    
    Args:
        robot: 机械臂实例
        timeout: 超时时间(秒)
        poll_interval: 轮询间隔(秒)
    
    Returns:
        bool: 运动是否成功完成
    """
    start_t = time.monotonic()
    while True:
        status = robot.get_arm_status()
        if status is not None and getattr(status.msg, "motion_status", None) == 0:
            return True
        if time.monotonic() - start_t > timeout:
            return False
        time.sleep(poll_interval)


def main():
    """主函数"""
    # ===== 1. 连接机械臂 =====
    robot_cfg = create_agx_arm_config(
        robot="{robot_type}",      # 机型: nero / piper / piper_h / piper_l
        comm="can",
        channel="can0",
        interface="socketcan",
    )
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()
    
    # ===== 2. 模式切换 =====
    # 模式切换前后建议 1s 延时
    time.sleep(1)
    robot.set_normal_mode()  # 普通模式 (单臂控制)
    # robot.set_master_mode()  # 主模式
    # robot.set_slave_mode()   # 从模式
    time.sleep(1)
    
    # ===== 3. 使能 =====
    while not robot.enable():
        time.sleep(0.01)
    
    # 设置速度 (0-100)
    robot.set_speed_percent(80)
    
    # ===== 4. 用户请求: {description} =====
    # TODO: 根据用户描述添加具体的运动代码
    #
    # 运动模式:
    # - J 模式 (关节): robot.set_motion_mode(robot.MOTION_MODE.J)
    # - P 模式 (点到点): robot.set_motion_mode(robot.MOTION_MODE.P)
    # - L 模式 (直线): robot.set_motion_mode(robot.MOTION_MODE.L)
    # - C 模式 (圆弧): robot.set_motion_mode(robot.MOTION_MODE.C)
    # - JS 模式 (快速响应，慎用): robot.set_motion_mode(robot.MOTION_MODE.JS)
    # - MIT 模式 (高级，慎用): robot.set_motion_mode(robot.MOTION_MODE.MIT)
    #
    # 关节运动 (弧度):
    #   robot.set_motion_mode(robot.MOTION_MODE.J)
    #   robot.move_j([j1, j2, j3, j4, j5, j6, j7])  # Nero 7轴
    #
    # 笛卡尔运动 (位置: 米, 姿态: 弧度):
    #   robot.set_motion_mode(robot.MOTION_MODE.P)
    #   robot.move_p([x, y, z, roll, pitch, yaw])
    #
    # 直线运动:
    #   robot.set_motion_mode(robot.MOTION_MODE.L)
    #   robot.move_l([x, y, z, roll, pitch, yaw])
    #
    # 圆弧运动:
    #   robot.set_motion_mode(robot.MOTION_MODE.C)
    #   robot.move_c(start_pose, mid_pose, end_pose)
    #
    # 等待运动完成:
    #   wait_motion_done(robot, timeout=3.0)
    
    # ===== 示例: 回零位 =====
    robot.set_motion_mode(robot.MOTION_MODE.J)
    robot.move_j([0.0] * 7)  # Nero 7轴
    wait_motion_done(robot)
    
    # ===== 5. 结束 =====
    time.sleep(0.5)
'''
        if include_disable:
            template += """
    # 可选: 完成后失能
    while not robot.disable():
        time.sleep(0.01)
"""

        template += """

if __name__ == "__main__":
    main()
"""
        return template

    @staticmethod
    def generate_joint_motion(joints: List[float], robot_type: str = "nero") -> str:
        """生成关节运动代码片段"""
        return f"""    # 关节运动
    robot.set_motion_mode(robot.MOTION_MODE.J)
    robot.move_j({joints})
    wait_motion_done(robot)
"""

    @staticmethod
    def generate_cartesian_motion(pose: List[float], robot_type: str = "nero") -> str:
        """生成笛卡尔运动代码片段"""
        return f"""    # 笛卡尔直线运动
    robot.set_motion_mode(robot.MOTION_MODE.L)
    robot.move_l({pose})  # [x, y, z, roll, pitch, yaw] (米, 弧度)
    wait_motion_done(robot)
"""

    @staticmethod
    def generate_sequential_motion(
        motions: List[Dict[str, Any]], robot_type: str = "nero"
    ) -> str:
        """生成顺序运动代码片段"""
        code = "    # 顺序执行多个动作\n"
        for i, motion in enumerate(motions):
            motion_type = motion.get("type", "joint")
            if motion_type == "joint":
                code += f"""    # 动作 {i + 1}: 关节运动
    robot.set_motion_mode(robot.MOTION_MODE.J)
    robot.move_j({motion.get("values")})
    wait_motion_done(robot)

"""
            elif motion_type == "cartesian":
                code += f"""    # 动作 {i + 1}: 笛卡尔运动
    robot.set_motion_mode(robot.MOTION_MODE.L)
    robot.move_l({motion.get("values")})
    wait_motion_done(robot)

"""
        return code


# ============================================================
# Skill 实现
# ============================================================


class AgxArmCodeGenSkill(BaseSkill):
    """
    pyAgxArm 机械臂代码生成 Skill

    根据用户自然语言描述，生成可执行的 pyAgxArm 控制代码。
    """

    def __init__(
        self,
        skill_dir: str = None,
        llm_client=None,
        validate_code: bool = True,
        **kwargs,
    ):
        super().__init__()

        # 加载 skill 配置
        if skill_dir is None:
            skill_dir = (
                "/media/hzm/data_disk/openclaw_robot_control/skill/agx_arm_codegen"
            )

        self.config = OpenClawSkillParser.parse(skill_dir)
        self.llm_client = llm_client
        self.validate_code = validate_code

        # 存储 metadata
        self.metadata = SkillMetadata(
            name=self.config.name,
            description=self.config.description,
            inputs={"user_description": str, "robot_type": str},
            outputs={"generated_code": str, "validation": dict},
            tags=["codegen", "robotics", "arm", "pyagxarm"],
        )

    async def validate_inputs(self, **kwargs) -> bool:
        return "user_description" in kwargs

    async def execute(
        self, user_description: str, robot_type: str = "nero"
    ) -> SkillResult:
        """
        根据用户描述生成代码

        Args:
            user_description: 用户自然语言描述
            robot_type: 机器人类型 (nero, piper, etc.)

        Returns:
            SkillResult with generated code
        """
        try:
            # 构建 prompt
            prompt = self._build_prompt(user_description)

            # 如果有 LLM 客户端，使用它生成
            if self.llm_client:
                logger.info("Using LLM to generate code")
                response = await self.llm_client.generate(prompt)
                code = self._extract_code(response)
            else:
                # 否则使用模板生成
                logger.info("Using template to generate code")
                code = CodeGenerator.generate_template(
                    description=user_description, robot_type=robot_type
                )

            # 验证代码
            validation_result = None
            if self.validate_code:
                validation_result = CodeValidator.validate(code)
                logger.info(
                    f"Validation: valid={validation_result.is_valid}, "
                    f"errors={len(validation_result.errors)}, "
                    f"warnings={len(validation_result.warnings)}"
                )

            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={
                    "generated_code": code,
                    "description": user_description,
                    "robot_type": robot_type,
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
                    "rules_applied": len(self.config.rules),
                    "when_to_use": self.config.when_to_use,
                    "safety_notes": self.config.safety_notes,
                },
            )

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    def _build_prompt(self, user_description: str) -> str:
        """构建生成代码的 prompt"""

        # 添加规则
        rules_text = "\n".join(f"- {rule}" for rule in self.config.rules)

        # 添加 API 参考
        api_ref = self.config.references.get("pyagxarm-api", "")

        # 添加安全注意事项
        safety_text = ""
        if self.config.safety_notes:
            safety_text = "\n## 安全注意事项\n" + "\n".join(
                f"- {note}" for note in self.config.safety_notes
            )

        prompt = f"""你是一个机械臂控制代码生成专家。

请根据用户的描述生成可执行的 pyAgxArm 控制代码。

## 用户描述
{user_description}

## 生成规则
{rules_text}

## API 参考
{api_ref}
{safety_text}

## 要求
1. 生成完整可运行的 Python 脚本
2. 包含所有必要的 import
3. 添加注释说明每个步骤
4. 包含安全提醒
5. 确保代码符合上述规则

请直接输出生成的代码，不要包含其他解释。"""

        return prompt

    def _extract_code(self, response: str) -> str:
        """从 LLM 响应中提取代码"""
        # 尝试提取 markdown 代码块
        patterns = [
            r"```python\n(.*?)```",
            r"```\n(.*?)```",
            r"```python\r\n(.*?)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        # 如果没有代码块，尝试找到 Python 代码
        # 移除可能的解释文本
        lines = response.split("\n")
        code_lines = []
        in_code = False

        for line in lines:
            if "import " in line or "from " in line:
                in_code = True
            if in_code:
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines)

        # 如果都没有，返回整个响应
        return response.strip()


# ============================================================
# Skill 管理器
# ============================================================


class OpenClawSkillManager:
    """
    OpenClaw Skill 管理器

    功能:
    - 动态加载 skill 目录
    - 管理多个 skill 实例
    - 提供统一的调用接口
    """

    def __init__(self, skills_base_dir: str = None):
        """
        初始化管理器

        Args:
            skills_base_dir: skills 根目录
        """
        if skills_base_dir is None:
            skills_base_dir = "/media/hzm/data_disk/openclaw_robot_control/skill"

        self.skills_base_dir = Path(skills_base_dir)
        self.loaded_skills: Dict[str, OpenClawSkillConfig] = {}
        self.skill_instances: Dict[str, AgxArmCodeGenSkill] = {}

    def discover_skills(self) -> List[str]:
        """发现所有可用的 skills"""
        if not self.skills_base_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_base_dir}")
            return []

        skills = []
        for item in self.skills_base_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skills.append(item.name)

        logger.info(f"Discovered skills: {skills}")
        return skills

    def load_skill(self, skill_name: str) -> OpenClawSkillConfig:
        """加载 skill 配置"""
        skill_dir = self.skills_base_dir / skill_name
        config = OpenClawSkillParser.parse(str(skill_dir))
        self.loaded_skills[skill_name] = config
        return config

    def get_skill_instance(
        self, skill_name: str, llm_client=None, validate: bool = True
    ) -> AgxArmCodeGenSkill:
        """获取 skill 实例"""
        # 如果未加载，先加载
        if skill_name not in self.loaded_skills:
            self.load_skill(skill_name)

        # 创建实例
        skill_dir = str(self.skills_base_dir / skill_name)
        instance = AgxArmCodeGenSkill(
            skill_dir=skill_dir, llm_client=llm_client, validate_code=validate
        )

        self.skill_instances[skill_name] = instance
        return instance

    async def execute(self, skill_name: str, description: str, **kwargs) -> SkillResult:
        """执行 skill"""
        instance = self.get_skill_instance(skill_name, kwargs.get("llm_client"))
        return await instance.execute(description, **kwargs)

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        """列出所有已加载的 skills"""
        return {
            name: {
                "description": config.description,
                "rules_count": len(config.rules),
                "when_to_use": config.when_to_use,
                "safety_notes": config.safety_notes,
            }
            for name, config in self.loaded_skills.items()
        }


# ============================================================
# 注册 Skill
# ============================================================


def register_agx_arm_skill():
    """注册 agx-arm-codegen skill"""

    @skill_registry.register(
        "agx-arm-codegen",
        description="生成 pyAgxArm 机械臂控制代码",
        tags=["robotics", "arm", "codegen", "agilex"],
    )
    class RegisteredAgxArmSkill(AgxArmCodeGenSkill):
        pass

    return RegisteredAgxArmSkill


# 自动注册
register_agx_arm_skill()


# ============================================================
# 便捷函数
# ============================================================


async def generate_arm_code(
    description: str,
    llm_client=None,
    skill_dir: str = None,
    robot_type: str = "nero",
    validate: bool = True,
) -> str:
    """
    便捷函数：生成机械臂控制代码

    Args:
        description: 用户描述
        llm_client: LLM 客户端 (可选)
        skill_dir: skill 目录路径
        robot_type: 机器人类型
        validate: 是否验证代码

    Returns:
        生成的 Python 代码
    """
    skill = AgxArmCodeGenSkill(
        skill_dir=skill_dir, llm_client=llm_client, validate_code=validate
    )

    result = await skill.execute(description, robot_type=robot_type)

    if result.status == SkillStatus.SUCCESS:
        return result.output["generated_code"]
    else:
        raise RuntimeError(f"Code generation failed: {result.error}")


def create_skill_manager(skills_dir: str = None) -> OpenClawSkillManager:
    """
    创建 Skill 管理器

    Args:
        skills_dir: skills 根目录

    Returns:
        OpenClawSkillManager 实例
    """
    return OpenClawSkillManager(skills_dir=skills_dir)
