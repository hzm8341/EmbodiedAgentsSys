"""
测试ForceControlSkill组件
"""
import asyncio
import sys
import os
import importlib.util

# 直接加载force_control_skill模块
spec = importlib.util.spec_from_file_location(
    "force_control_skill",
    "/media/hzm/data_disk/EmbodiedAgentsSys/skills/manipulation/force_control_skill.py"
)
force_control_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(force_control_module)

ForceControlSkill = force_control_module.ForceControlSkill
ForceData = force_control_module.ForceData
ImpedanceParams = force_control_module.ImpedanceParams
InsertParams = force_control_module.InsertParams


async def test_read_force():
    """测试读取力数据"""
    print("\n" + "="*60)
    print("测试1: 读取力数据")
    print("="*60)
    
    skill = ForceControlSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(action="read_force")
    
    print(f"  成功: {result['success']}")
    print(f"  力数据: {result['force']}")
    print(f"  合力: {result['force']['total_force']:.3f} N")
    print(f"  合矩: {result['force']['total_torque']:.3f} Nm")


async def test_impedance_move():
    """测试阻抗控制移动"""
    print("\n" + "="*60)
    print("测试2: 阻抗控制移动")
    print("="*60)
    
    skill = ForceControlSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(
        action="impedance_move",
        target_position=[0.3, 0.1, 0.2],
        stiffness=100.0,
        damping=10.0
    )
    
    print(f"  成功: {result['success']}")
    if result.get('success'):
        print(f"  目标位置: {result['target_position']}")
        print(f"  刚度: {result['stiffness']} N/m")
        print(f"  阻尼: {result['damping']} N·s/m")
        print(f"  状态: {result['status']}")
    else:
        print(f"  错误: {result.get('error', 'Unknown error')}")


async def test_insert():
    """测试插入操作"""
    print("\n" + "="*60)
    print("测试3: 插入操作")
    print("="*60)
    
    skill = ForceControlSkill(_simulated=True)
    await skill.initialize()
    
    # 正常插入
    result = await skill.execute(
        action="insert",
        target_position=[0.3, 0.0, 0.1],
        max_force=5.0,
        insert_speed=0.01
    )
    
    print(f"  成功: {result['success']}")
    print(f"  目标位置: {result['target_position']}")
    print(f"  最终位置: {result.get('final_position')}")
    print(f"  最终力: {result.get('applied_force', 0):.3f} N")
    print(f"  最大力: {result.get('max_force', 0):.3f} N")
    print(f"  状态: {result.get('status')}")
    print(f"  消息: {result.get('message')}")
    
    # 测试力超限
    print("\n  测试力超限情况:")
    result = await skill.execute(
        action="insert",
        target_position=[0.3, 0.0, 0.1],
        max_force=0.1,  # 很小的力阈值
        insert_speed=0.01
    )
    
    print(f"  成功: {result['success']}")
    print(f"  状态: {result.get('status')}")
    print(f"  错误: {result.get('error')}")


async def test_collision_detection():
    """测试碰撞检测"""
    print("\n" + "="*60)
    print("测试4: 碰撞检测")
    print("="*60)
    
    skill = ForceControlSkill(_simulated=True)
    await skill.initialize()
    
    # 正常情况
    result = await skill.execute(action="contact_detect", threshold=10.0)
    print(f"  正常情况:")
    print(f"    检测到碰撞: {result['detected']}")
    print(f"    碰撞力: {result['collision_force']:.3f} N")
    print(f"    需要停止: {result['stop_required']}")
    
    # 模拟高力情况
    skill._last_force = ForceData(fx=15.0, fy=1.0, fz=1.0)
    result = await skill.execute(action="contact_detect", threshold=10.0)
    print(f"\n  高力情况:")
    print(f"    检测到碰撞: {result['detected']}")
    print(f"    碰撞力: {result['collision_force']:.3f} N")
    print(f"    碰撞方向: {result['collision_direction']}")
    print(f"    需要停止: {result['stop_required']}")


async def test_emergency_stop():
    """测试紧急停止"""
    print("\n" + "="*60)
    print("测试5: 紧急停止")
    print("="*60)
    
    skill = ForceControlSkill(_simulated=True)
    await skill.initialize()
    
    # 触发紧急停止
    result = await skill.execute(action="emergency_stop")
    print(f"  紧急停止: {result['success']}")
    print(f"  消息: {result['message']}")
    print(f"  需要重置: {result['reset_required']}")
    
    # 尝试执行其他动作
    result = await skill.execute(action="read_force")
    print(f"\n  紧急停止后尝试读取力:")
    print(f"    成功: {result['success']}")
    print(f"    错误: {result.get('error')}")
    
    # 重置
    result = await skill.emergency_reset()
    print(f"\n  重置紧急停止:")
    print(f"    成功: {result['success']}")
    print(f"    消息: {result['message']}")


async def test_force_data():
    """测试力数据类"""
    print("\n" + "="*60)
    print("测试6: ForceData类")
    print("="*60)
    
    force = ForceData(fx=3.0, fy=4.0, fz=0.0, tx=0.1, ty=0.2, tz=0.0)
    
    print(f"  力分量: fx={force.fx}, fy={force.fy}, fz={force.fz}")
    print(f"  合力: {force.total_force:.3f} N")
    print(f"  合矩: {force.total_torque:.3f} Nm")
    print(f"  总幅值: {force.magnitude:.3f}")
    print(f"  超过阈值(force=5.0): {force.exceeds_threshold(5.0)}")
    print(f"  超过阈值(force=2.0): {force.exceeds_threshold(2.0)}")
    print(f"  转换为字典: {force.to_dict()}")


async def test_impedance_params():
    """测试阻抗参数"""
    print("\n" + "="*60)
    print("测试7: 阻抗参数")
    print("="*60)
    
    params = ImpedanceParams(
        stiffness=200.0,
        damping=15.0,
        mass=0.5,
        force_limit=8.0,
        torque_limit=0.8
    )
    
    print(f"  刚度: {params.stiffness} N/m")
    print(f"  阻尼: {params.damping} N·s/m")
    print(f"  质量: {params.mass} kg")
    print(f"  力限制: {params.force_limit} N")
    print(f"  力矩限制: {params.torque_limit} Nm")


async def main():
    print("\n" + "="*60)
    print("ForceControlSkill测试")
    print("="*60)
    
    await test_read_force()
    await test_impedance_move()
    await test_insert()
    await test_collision_detection()
    await test_emergency_stop()
    await test_force_data()
    await test_impedance_params()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
