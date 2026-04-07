"""
测试SkillGenerator组件
"""
import asyncio
import sys
import os
import importlib.util

# 直接加载skill_generator模块
spec = importlib.util.spec_from_file_location(
    "skill_generator",
    "/media/hzm/data_disk/EmbodiedAgentsSys/skills/teaching/skill_generator.py"
)
generator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator_module)

SkillGenerator = generator_module.SkillGenerator


async def test_generate_skill():
    """测试生成Skill"""
    print("\n" + "="*60)
    print("测试1: 生成Skill")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    # 模拟示教动作数据
    teaching_action = {
        "name": "拾取放置动作",
        "action_id": "test_001",
        "description": "测试用的拾取放置动作",
        "duration": 5.0,
        "frames": [
            {
                "frame_id": 0,
                "joint_positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "ee_position": [0.3, 0.1, 0.1]
            },
            {
                "frame_id": 1,
                "joint_positions": [0.1, 0.2, 0.3, 0.1, 0.1, 0.0],
                "ee_position": [0.3, 0.1, 0.05]
            },
        ]
    }
    
    result = await generator.generate_skill(
        teaching_action=teaching_action,
        skill_name="pick_and_place",
        description="拾取并放置物体"
    )
    
    print(f"  成功: {result['success']}")
    print(f"  Skill ID: {result['skill_id']}")
    print(f"  名称: {result['name']}")
    print(f"  类名: {result['class_name']}")
    print(f"  代码预览:")
    print(f"  {result['code_preview'][:200]}...")


async def test_generate_parametric():
    """测试生成参数化Skill"""
    print("\n" + "="*60)
    print("测试2: 生成参数化Skill")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    # 基础示教动作
    base_action = {
        "name": "移动动作",
        "action_id": "move_001"
    }
    
    # 参数
    parameters = ["target_position", "speed", "gripper_state"]
    
    result = await generator.generate_parametric(
        base_action=base_action,
        parameters=parameters,
        skill_name="move_to"
    )
    
    print(f"  成功: {result['success']}")
    print(f"  Skill ID: {result['skill_id']}")
    print(f"  名称: {result['name']}")
    print(f"  是否参数化: {result['is_parametric']}")
    print(f"  参数列表:")
    for param in result['parameters']:
        print(f"    - {param['name']}: {param['type']}")
    print(f"  代码预览:")
    print(f"  {result['code_preview'][:200]}...")


async def test_generate_wrapper():
    """测试生成包装器"""
    print("\n" + "="*60)
    print("测试3: 生成包装器")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    result = await generator.generate_wrapper(
        skill_name="pick_and_place",
        wrapper_name="pick_and_place_advanced"
    )
    
    print(f"  成功: {result['success']}")
    print(f"  Skill ID: {result['skill_id']}")
    print(f"  类名: {result['class_name']}")


async def test_validate_skill():
    """测试验证Skill"""
    print("\n" + "="*60)
    print("测试4: 验证Skill")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    # 先生成一个Skill
    result = await generator.generate_skill(
        teaching_action={"name": "测试", "action_id": "test"},
        skill_name="test_skill"
    )
    
    # 验证
    result = await generator.validate_skill(skill_id=result['skill_id'])
    
    print(f"  成功: {result['success']}")
    print(f"  验证通过: {result['valid']}")
    print(f"  检查项:")
    for check, passed in result['checks'].items():
        print(f"    - {check}: {'✓' if passed else '✗'}")


async def test_export_skill():
    """测试导出Skill"""
    print("\n" + "="*60)
    print("测试5: 导出Skill")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    # 先生成一个Skill
    result = await generator.generate_skill(
        teaching_action={"name": "导出测试"},
        skill_name="export_test"
    )
    skill_id = result['skill_id']
    
    # 导出
    result = await generator.export_skill(
        skill_id=skill_id,
        filename="exported_skill.py"
    )
    
    print(f"  成功: {result['success']}")
    print(f"  文件名: {result['filename']}")
    print(f"  代码长度: {result['code_length']}")
    print(f"  消息: {result['message']}")


async def test_list_templates():
    """测试列出模板"""
    print("\n" + "="*60)
    print("测试6: 列出模板")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    result = await generator.list_templates()
    
    print(f"  成功: {result['success']}")
    print(f"  模板数量: {result['count']}")
    for template in result['templates']:
        print(f"    - {template['name']}: {template['description']}")
        print(f"      类别: {template['category']}")


async def test_list_generated():
    """测试列出生成的Skills"""
    print("\n" + "="*60)
    print("测试7: 列出生成的Skills")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    # 生成几个Skills
    await generator.generate_skill(teaching_action={"name": "动作1"}, skill_name="skill1")
    await generator.generate_skill(teaching_action={"name": "动作2"}, skill_name="skill2")
    await generator.generate_parametric(
        base_action={"name": "动作3"},
        parameters=["pos"],
        skill_name="skill3"
    )
    
    result = await generator.list_generated_skills()
    
    print(f"  成功: {result['success']}")
    print(f"  Skills数量: {result['count']}")
    for skill in result['skills']:
        parametric = "✓" if skill['is_parametric'] else "✗"
        print(f"    - {skill['name']}: {skill['category']} (参数化: {parametric})")


async def test_class_name_conversion():
    """测试类名转换"""
    print("\n" + "="*60)
    print("测试8: 类名转换")
    print("="*60)
    
    generator = SkillGenerator(_simulated=True)
    
    test_cases = [
        "pick and place",
        "move_to_position",
        "抓取物体",
        "assembly_action",
        "test"
    ]
    
    for name in test_cases:
        class_name = generator._to_class_name(name)
        print(f"  '{name}' -> '{class_name}'")


async def main():
    print("\n" + "="*60)
    print("SkillGenerator测试")
    print("="*60)
    
    await test_generate_skill()
    await test_generate_parametric()
    await test_generate_wrapper()
    await test_validate_skill()
    await test_export_skill()
    await test_list_templates()
    await test_list_generated()
    await test_class_name_conversion()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
