"""
测试AssemblySkill组件
"""
import asyncio
import sys
import os
import importlib.util

# 直接加载assembly_skill模块
spec = importlib.util.spec_from_file_location(
    "assembly_skill",
    "/media/hzm/data_disk/EmbodiedAgentsSys/skills/manipulation/assembly_skill.py"
)
assembly_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly_module)

AssemblySkill = assembly_module.AssemblySkill
AssemblyPart = assembly_module.AssemblyPart


async def test_plan_sequence():
    """测试装配序列规划"""
    print("\n" + "="*60)
    print("测试1: 装配序列规划")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    # 指定零件
    result = await skill.execute(
        action="plan_sequence",
        parts=["零件A", "零件B"]
    )
    
    print(f"  成功: {result['success']}")
    print(f"  序列ID: {result['sequence_id']}")
    print(f"  预计时间: {result['estimated_time']:.1f}s")
    print(f"  难度: {result['difficulty']}")
    print(f"  装配步骤:")
    for step in result['sequence']:
        print(f"    {step['step_id']}. {step['description']}")


async def test_recognize_fit():
    """测试配合关系识别"""
    print("\n" + "="*60)
    print("测试2: 配合关系识别")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    # 识别特定零件
    result = await skill.execute(
        action="recognize_fit",
        part_a="螺栓M6",
        part_b="螺母M6"
    )
    
    print(f"  螺栓+螺母:")
    print(f"    成功: {result['success']}")
    print(f"    配合类型: {result['fit_type']}")
    print(f"    公差: {result['tolerance']}")
    
    # 获取所有可能的配合
    result = await skill.execute(
        action="recognize_fit"
    )
    
    print(f"\n  所有配合关系:")
    print(f"    成功: {result['success']}")
    print(f"    数量: {result['count']}")
    for fit in result['fits']:
        print(f"    - {fit['part_a']} + {fit['part_b']}: {fit['fit_type']}")


async def test_plan_path():
    """测试装配路径规划"""
    print("\n" + "="*60)
    print("测试3: 装配路径规划")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(
        action="plan_path",
        part_name="零件A",
        target_position=[0.3, 0.0, 0.0]
    )
    
    print(f"  成功: {result['success']}")
    print(f"  路径类型: {result['path']['path_type']}")
    print(f"  路径点数: {result['path_length']}")
    print(f"  安全高度: {result['path']['clearance_height']} m")
    print(f"  接近高度: {result['path']['approach_height']} m")
    print(f"  预计时间: {result['estimated_time']:.1f}s")
    
    print(f"  路径点:")
    for i, point in enumerate(result['path']['path_points']):
        print(f"    {i+1}. {point}")


async def test_align_parts():
    """测试零件对齐"""
    print("\n" + "="*60)
    print("测试4: 零件对齐")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(
        action="align_parts",
        part_a="零件A",
        part_b="零件B",
        alignment_type="both"
    )
    
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  对齐类型: {result['alignment']['alignment_type']}")
        print(f"  状态: {result['status']}")
        print(f"  对齐精度: {result['alignment']['alignment_accuracy']*1000:.2f} mm")
        print(f"  偏移: {result['alignment']['offset']}")
        print(f"  旋转: {result['alignment']['rotation']}")
    else:
        print(f"  错误: {result.get('error')}")


async def test_assemble():
    """测试执行装配"""
    print("\n" + "="*60)
    print("测试5: 执行装配")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    # 过盈配合
    result = await skill.execute(
        action="assemble",
        part_a="零件A",
        part_b="零件B",
        fit_type="press"
    )
    
    print(f"  过盈配合:")
    print(f"    成功: {result['success']}")
    print(f"    配合力: {result['applied_force']} N")
    print(f"    插入速度: {result['insertion_speed']} m/s")
    print(f"    状态: {result['status']}")
    
    # 间隙配合
    result = await skill.execute(
        action="assemble",
        part_a="螺栓M6",
        part_b="螺母M6",
        fit_type="clearance"
    )
    
    print(f"\n  间隙配合:")
    print(f"    成功: {result['success']}")
    print(f"    配合力: {result['applied_force']} N")
    print(f"    插入速度: {result['insertion_speed']} m/s")
    
    # 螺纹配合
    result = await skill.execute(
        action="assemble",
        part_a="螺栓M6",
        part_b="螺母M6",
        fit_type="threaded"
    )
    
    print(f"\n  螺纹配合:")
    print(f"    成功: {result['success']}")
    print(f"    配合力: {result['applied_force']} N")
    print(f"    插入速度: {result['insertion_speed']} m/s")


async def test_verify_assembly():
    """测试装配验证"""
    print("\n" + "="*60)
    print("测试6: 装配验证")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(
        action="verify_assembly",
        assembly_name="test_assembly"
    )
    
    print(f"  成功: {result['success']}")
    print(f"  验证通过: {result['verified']}")
    print(f"  质量等级: {result['quality']}")
    print(f"  位置检查: {result['tolerance_check']['position']}")
    print(f"  姿态检查: {result['tolerance_check']['orientation']}")
    print(f"  备注: {result['notes']}")


async def test_parts_library():
    """测试零件库"""
    print("\n" + "="*60)
    print("测试7: 零件库")
    print("="*60)
    
    skill = AssemblySkill(_simulated=True)
    await skill.initialize()
    
    # 获取零件信息
    part = skill.get_part_info("零件A")
    print(f"  零件A信息:")
    print(f"    名称: {part.name}")
    print(f"    ID: {part.part_id}")
    print(f"    尺寸: {part.dimensions}")
    print(f"    几何类型: {part.geometry_type}")
    print(f"    特征: {part.features}")
    print(f"    位置: {part.position}")
    
    # 添加新零件
    new_part = AssemblyPart(
        name="新零件",
        part_id="NEW_001",
        dimensions=[0.1, 0.05, 0.02],
        geometry_type="box",
        features=[],
        position=[0.5, 0.0, 0.1]
    )
    skill.add_part_to_library(new_part)
    
    # 验证添加成功
    added_part = skill.get_part_info("新零件")
    print(f"\n  添加新零件: {added_part.name}")


async def main():
    print("\n" + "="*60)
    print("AssemblySkill测试")
    print("="*60)
    
    await test_plan_sequence()
    await test_recognize_fit()
    await test_plan_path()
    await test_align_parts()
    await test_assemble()
    await test_verify_assembly()
    await test_parts_library()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
