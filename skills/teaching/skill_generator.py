"""
SkillGenerator - Skill生成器
===========================

该模块用于根据示教动作自动生成可复用的Skill代码。

功能:
- 从示教动作生成Skill代码
- 参数化Skill支持可变目标
- 生成Skill元数据和接口
- 代码模板定制

使用示例:
    from skills.teaching.skill_generator import SkillGenerator
    
    generator = SkillGenerator()
    
    # 从示教动作生成Skill
    result = await generator.execute(
        action="generate_skill",
        teaching_action=teaching_action,
        skill_name="pick_and_place"
    )
    
    # 生成参数化Skill
    result = await generator.execute(
        action="generate_parametric",
        base_action=teaching_action,
        parameters=["target_position", "speed"]
    )
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class GeneratorAction(Enum):
    """生成器动作"""
    GENERATE_SKILL = "generate_skill"           # 生成Skill
    GENERATE_PARAMETRIC = "generate_parametric"   # 生成参数化Skill
    GENERATE_WRAPPER = "generate_wrapper"        # 生成包装器
    VALIDATE_SKILL = "validate_skill"           # 验证Skill
    EXPORT_SKILL = "export_skill"               # 导出Skill


@dataclass
class SkillTemplate:
    """Skill代码模板"""
    name: str
    description: str
    category: str
    input_params: List[Dict[str, Any]] = field(default_factory=list)
    output_params: List[Dict[str, Any]] = field(default_factory=list)
    code_template: str = ""
    test_template: str = ""


@dataclass
class GeneratedSkill:
    """生成的Skill"""
    skill_id: str
    name: str
    description: str
    category: str
    source_teaching_id: Optional[str] = None
    
    # 代码
    skill_code: str = ""
    test_code: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 参数化信息
    is_parametric: bool = False
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "source_teaching_id": self.source_teaching_id,
            "skill_code": self.skill_code,
            "test_code": self.test_code,
            "metadata": self.metadata,
            "is_parametric": self.is_parametric,
            "parameters": self.parameters
        }


class SkillGenerator:
    """
    Skill生成器 - 根据示教动作生成可复用的Skill代码
    
    功能:
    1. 从示教动作生成基础Skill
    2. 参数化处理，支持可变参数
    3. 生成测试代码
    4. 导出Skill到文件
    """
    
    # 基础Skill模板
    BASE_SKILL_TEMPLATE = '''"""
{skill_name} - 自动生成的Skill
{description}

由SkillGenerator自动生成
来源示教动作: {source_teaching_id}
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class {class_name}Config:
    """{class_name}配置"""
{config_fields}

class {class_name}:
    """
    {class_name} - {description}
    
    输入参数:
{input_descriptions}
    
    输出参数:
{output_descriptions}
    """
    
    def __init__(self, config: {class_name}Config = None, **kwargs):
        self.config = config or {class_name}Config()
        self._initialized = False
        
    async def initialize(self) -> bool:
        """初始化"""
        self._initialized = True
        return True
        
    async def execute(self, **params) -> Dict[str, Any]:
        """
        执行Skill
        
{execute_params_doc}
        
        Returns:
            执行结果
        """
        if not self._initialized:
            await self.initialize()
            
{execute_body}
        
        return {{
            "success": True,
            "skill_name": "{skill_name}",
{return_fields}
        }}
    
    async def validate_inputs(self, **kwargs) -> bool:
        """验证输入参数"""
{validate_body}
        return True
        
    async def cleanup(self):
        """清理资源"""
        pass
'''

    # 参数化Skill模板
    PARAMETRIC_SKILL_TEMPLATE = '''"""
{skill_name}_parametric - 参数化的{skill_name}
{description}

由SkillGenerator自动生成
支持参数: {parameter_names}
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class {class_name}Config:
    """{class_name}配置"""
{config_fields}

@dataclass
class {class_name}Parametric:
    """参数化{class_name}"""
    skill_id: str = ""
    name: str = "{skill_name}"
    description: str = "{description}"
    
    # 关键帧数据
    keyframes: List[Dict[str, Any]] = field(default_factory=list)
    
    # 参数化配置
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 配置
    config: {class_name}Config = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {class_name}Config()
    
    async def initialize(self) -> bool:
        """初始化"""
        self._initialized = True
        return True
        
    async def execute(self, **params) -> Dict[str, Any]:
        """
        执行参数化Skill
        
{execute_params_doc}
        
        Returns:
            执行结果
        """
        if not self._initialized:
            await self.initialize()
            
        # 合并参数
        merged_params = {{**self.parameters, **params}}
        
{param_execute_body}
        
        return {{
            "success": True,
            "skill_name": "{skill_name}",
            "parameters_used": merged_params,
{return_fields}
        }}
'''

    # 测试模板
    TEST_TEMPLATE = '''
"""
测试{skill_name}
"""
import asyncio
import pytest
from {module_name} import {class_name}


async def test_{skill_name}_basic():
    """基础测试"""
    skill = {class_name}()
    
    # 初始化
    initialized = await skill.initialize()
    assert initialized is True
    
    # 执行
    result = await skill.execute{test_execute_args}
    
    # 验证
    assert result["success"] is True
    assert result["skill_name"] == "{skill_name}"


async def test_{skill_name}_validation():
    """参数验证测试"""
    skill = {class_name}()
    await skill.initialize()
    
    # 测试无效输入
    result = await skill.execute{test_validation_args}
    # 应该能处理并返回结果
'''

    def __init__(
        self,
        output_dir: str = "./generated_skills",
        _simulated: bool = True
    ):
        """
        初始化生成器
        
        Args:
            output_dir: 输出目录
            _simulated: 是否使用模拟模式
        """
        self.output_dir = output_dir
        self._simulated = _simulated
        
        # 生成的Skills
        self._generated_skills: Dict[str, GeneratedSkill] = {}
        
        # 内置模板
        self._templates: Dict[str, SkillTemplate] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """注册默认模板"""
        self._templates = {
            "pick_place": SkillTemplate(
                name="pick_place",
                description="抓取放置动作",
                category="manipulation",
                input_params=[
                    {"name": "target_object", "type": "str", "required": True},
                    {"name": "target_position", "type": "List[float]", "required": True},
                ],
                output_params=[
                    {"name": "success", "type": "bool"},
                    {"name": "final_position", "type": "List[float]"},
                ]
            ),
            "move_sequence": SkillTemplate(
                name="move_sequence",
                description="移动序列动作",
                category="motion",
                input_params=[
                    {"name": "positions", "type": "List[List[float]]", "required": True},
                    {"name": "speed", "type": "float", "default": 1.0},
                ],
                output_params=[
                    {"name": "success", "type": "bool"},
                    {"name": "reached_positions", "type": "List[List[float]]"},
                ]
            ),
            "assembly": SkillTemplate(
                name="assembly",
                description="装配动作",
                category="assembly",
                input_params=[
                    {"name": "part_a", "type": "str", "required": True},
                    {"name": "part_b", "type": "str", "required": True},
                    {"name": "fit_type", "type": "str", "default": "press"},
                ],
                output_params=[
                    {"name": "success", "type": "bool"},
                    {"name": "assembly_quality", "type": "str"},
                ]
            )
        }
    
    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """
        执行生成器动作
        
        Args:
            action: 动作类型
            **params: 动作参数
            
        Returns:
            生成结果
        """
        action_map = {
            "generate_skill": self.generate_skill,
            "generate_parametric": self.generate_parametric,
            "generate_wrapper": self.generate_wrapper,
            "validate_skill": self.validate_skill,
            "export_skill": self.export_skill,
            "list_templates": self.list_templates,
            "list_generated": self.list_generated_skills,
        }
        
        if action in action_map:
            return await action_map[action](**params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    async def generate_skill(
        self,
        teaching_action: Dict[str, Any] = None,
        skill_name: str = None,
        description: str = None,
        template: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        """
        从示教动作生成Skill
        
        Args:
            teaching_action: 示教动作数据
            skill_name: Skill名称
            description: Skill描述
            template: 使用的模板
        """
        # 生成唯一ID
        skill_id = str(uuid.uuid4())[:8]
        
        # 确定名称和描述
        name = skill_name or teaching_action.get("name", "generated_skill") if teaching_action else "generated_skill"
        desc = description or teaching_action.get("description", "自动生成的Skill") if teaching_action else "自动生成的Skill"
        
        # 获取帧数据用于生成代码
        frames = []
        if teaching_action and "frames" in teaching_action:
            frames = teaching_action["frames"]
        
        # 生成Skill代码
        class_name = self._to_class_name(name)
        
        # 生成配置字段
        config_fields = self._generate_config_fields(frames, teaching_action)
        
        # 生成输入/输出描述
        input_desc = self._generate_input_description(frames)
        output_desc = self._generate_output_description(frames)
        execute_params = self._generate_execute_params(frames)
        
        # 生成代码
        skill_code = self.BASE_SKILL_TEMPLATE.format(
            skill_name=name,
            class_name=class_name,
            description=desc,
            source_teaching_id=teaching_action.get("action_id", "unknown") if teaching_action else "unknown",
            config_fields=config_fields,
            input_descriptions=input_desc,
            output_descriptions=output_desc,
            execute_params_doc=execute_params,
            execute_body=self._generate_execute_body(frames),
            validate_body=self._generate_validate_body(frames),
            return_fields=self._generate_return_fields(frames)
        )
        
        # 生成测试代码
        test_code = self._generate_test_code(name, class_name, frames)
        
        # 创建生成的Skill
        generated = GeneratedSkill(
            skill_id=skill_id,
            name=name,
            description=desc,
            category="generated",
            source_teaching_id=teaching_action.get("action_id") if teaching_action else None,
            skill_code=skill_code,
            test_code=test_code,
            metadata={
                "frame_count": len(frames),
                "generated_at": "now"
            },
            is_parametric=False
        )
        
        # 保存
        self._generated_skills[skill_id] = generated
        
        return {
            "success": True,
            "action": "generate_skill",
            "skill_id": skill_id,
            "name": name,
            "class_name": class_name,
            "code_preview": skill_code[:500] + "..." if len(skill_code) > 500 else skill_code
        }
    
    async def generate_parametric(
        self,
        base_action: Dict[str, Any] = None,
        parameters: List[str] = None,
        skill_name: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成参数化Skill
        
        Args:
            base_action: 基础示教动作
            parameters: 要参数化的变量列表
            skill_name: Skill名称
        """
        skill_id = str(uuid.uuid4())[:8]
        
        name = skill_name or f"{base_action.get('name', 'skill')}_parametric" if base_action else "parametric_skill"
        desc = f"参数化的{name}"
        
        class_name = self._to_class_name(name)
        
        # 处理参数
        param_list = []
        config_fields = ""
        param_execute_body = ""
        
        if parameters:
            for param in parameters:
                param_list.append({
                    "name": param,
                    "type": "Any",
                    "required": False
                })
                config_fields += f"    {param}: Any = None\n"
                param_execute_body += f"        # 使用参数: {param}\n"
                param_execute_body += f"        # value = merged_params.get('{param}')\n"
        
        # 生成参数化代码
        skill_code = self.PARAMETRIC_SKILL_TEMPLATE.format(
            skill_name=name,
            class_name=class_name,
            description=desc,
            parameter_names=", ".join(parameters) if parameters else "none",
            config_fields=config_fields or "    pass",
            execute_params_doc="        **params: 执行参数",
            param_execute_body=param_execute_body or "        pass",
            return_fields="            \"status\": \"completed\""
        )
        
        # 生成测试代码
        test_code = self._generate_test_code(name, class_name, [])
        
        generated = GeneratedSkill(
            skill_id=skill_id,
            name=name,
            description=desc,
            category="parametric",
            source_teaching_id=base_action.get("action_id") if base_action else None,
            skill_code=skill_code,
            test_code=test_code,
            is_parametric=True,
            parameters=param_list
        )
        
        self._generated_skills[skill_id] = generated
        
        return {
            "success": True,
            "action": "generate_parametric",
            "skill_id": skill_id,
            "name": name,
            "is_parametric": True,
            "parameters": param_list,
            "code_preview": skill_code[:500] + "..."
        }
    
    async def generate_wrapper(
        self,
        skill_name: str,
        wrapper_name: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成包装器"""
        # 简单的包装器生成
        class_name = self._to_class_name(wrapper_name or f"{skill_name}_wrapper")
        
        wrapper_code = f'''"""
{class_name} - {skill_name}的包装器
"""

from typing import Any, Dict

class {class_name}:
    """包装{skill_name}"""
    
    def __init__(self, wrapped_skill=None, **kwargs):
        self.wrapped_skill = wrapped_skill
        
    async def execute(self, **params) -> Dict[str, Any]:
        """执行包装的Skill"""
        if self.wrapped_skill:
            return await self.wrapped_skill.execute(**params)
        return {{"success": False, "error": "No wrapped skill"}}
'''
        
        skill_id = str(uuid.uuid4())[:8]
        
        generated = GeneratedSkill(
            skill_id=skill_id,
            name=class_name,
            description=f"{skill_name}的包装器",
            category="wrapper",
            skill_code=wrapper_code,
            is_parametric=False
        )
        
        self._generated_skills[skill_id] = generated
        
        return {
            "success": True,
            "action": "generate_wrapper",
            "skill_id": skill_id,
            "class_name": class_name
        }
    
    async def validate_skill(
        self,
        skill_code: str = None,
        skill_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """验证生成的Skill代码"""
        if skill_id and skill_id in self._generated_skills:
            skill = self._generated_skills[skill_id]
            code = skill.skill_code
        elif skill_code:
            code = skill_code
        else:
            return {"success": False, "error": "No code to validate"}
        
        # 简单的语法检查
        validation_results = {
            "has_class": "class " in code,
            "has_execute": "async def execute" in code or "def execute" in code,
            "has_init": "def __init__" in code,
            "has_return": "return" in code
        }
        
        all_passed = all(validation_results.values())
        
        return {
            "success": True,
            "action": "validate_skill",
            "valid": all_passed,
            "checks": validation_results
        }
    
    async def export_skill(
        self,
        skill_id: str,
        filename: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """导出Skill到文件"""
        if skill_id not in self._generated_skills:
            return {"success": False, "error": f"Skill {skill_id} not found"}
        
        skill = self._generated_skills[skill_id]
        
        # 确定文件名
        if filename is None:
            filename = f"{skill.name}.py"
        
        if self._simulated:
            # 模拟模式
            return {
                "success": True,
                "action": "export_skill",
                "skill_id": skill_id,
                "filename": filename,
                "code_length": len(skill.skill_code),
                "message": f"Simulated export to {filename}"
            }
        else:
            # TODO: 实际保存文件
            pass
    
    async def list_templates(self, **kwargs) -> Dict[str, Any]:
        """列出可用模板"""
        templates = []
        for name, template in self._templates.items():
            templates.append({
                "name": name,
                "description": template.description,
                "category": template.category,
                "input_params": template.input_params,
                "output_params": template.output_params
            })
        
        return {
            "success": True,
            "templates": templates,
            "count": len(templates)
        }
    
    async def list_generated_skills(self, **kwargs) -> Dict[str, Any]:
        """列出已生成的Skills"""
        skills = []
        for skill_id, skill in self._generated_skills.items():
            skills.append({
                "skill_id": skill_id,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "is_parametric": skill.is_parametric,
                "source_teaching_id": skill.source_teaching_id
            })
        
        return {
            "success": True,
            "skills": skills,
            "count": len(skills)
        }
    
    def _to_class_name(self, name: str) -> str:
        """转换为类名"""
        # 替换特殊字符为空格，然后按空格分割，取每个单词的首字母大写
        name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', ' ', name)
        parts = name.split()
        return ''.join(p.capitalize() for p in parts if p) + "Skill"
    
    def _generate_config_fields(self, frames: List[Dict], action: Dict = None) -> str:
        """生成配置字段"""
        if not frames:
            return "    pass"
        
        # 从帧数据提取关节数量等信息
        joint_count = 0
        if frames and "joint_positions" in frames[0]:
            joint_count = len(frames[0].get("joint_positions", []))
        
        fields = f"    joint_count: int = {joint_count}\n"
        fields += f"    frame_count: int = {len(frames)}\n"
        
        if action:
            fields += f"    duration: float = {action.get('duration', 0.0)}\n"
        
        return fields
    
    def _generate_input_description(self, frames: List[Dict]) -> str:
        """生成输入参数描述"""
        return "    - params: 执行参数"
    
    def _generate_output_description(self, frames: List[Dict]) -> str:
        """生成输出参数描述"""
        return "    - result: 执行结果字典"
    
    def _generate_execute_params(self, frames: List[Dict]) -> str:
        """生成执行参数文档"""
        return "        **params: Skill执行参数"
    
    def _generate_execute_body(self, frames: List[Dict]) -> str:
        """生成执行函数体"""
        if not frames:
            return "        pass"
        
        # 简单的模拟执行
        return "        # 从示教动作生成的执行逻辑\n        # 遍历关键帧并执行\n        for frame in frames:\n            # 执行每一帧\n            pass"
    
        return "        # 从示教动作生成的执行逻辑\n        # 遍历关键帧并执行\n        for frame in frames:\n            # 执行每一帧\n            pass"
    
    def _generate_validate_body(self, frames: List[Dict]) -> str:
        """生成验证函数体"""
        if not frames:
            return "        return True"
        return "        # 验证必要参数\n        return True"
    
    def _generate_return_fields(self, frames: List[Dict]) -> str:
        """生成返回字段"""
        return '            "status": "completed"'
    
    def _generate_test_code(
        self,
        skill_name: str,
        class_name: str,
        frames: List[Dict]
    ) -> str:
        """生成测试代码"""
        return self.TEST_TEMPLATE.format(
            skill_name=skill_name,
            class_name=class_name,
            module_name=skill_name.lower().replace(" ", "_"),
            test_execute_args="()",
            test_validation_args="()"
        )


def create_skill_generator(
    output_dir: str = "./generated_skills",
    simulated: bool = True
) -> SkillGenerator:
    """
    工厂函数: 创建SkillGenerator实例
    """
    return SkillGenerator(
        output_dir=output_dir,
        _simulated=simulated
    )
