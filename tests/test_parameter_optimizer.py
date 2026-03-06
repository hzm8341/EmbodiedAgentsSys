"""
测试ParameterOptimizer组件
"""
import asyncio
import sys
import os
import importlib.util
import numpy as np

# 直接加载parameter_optimizer模块
spec = importlib.util.spec_from_file_location(
    "parameter_optimizer",
    "/media/hzm/data_disk/EmbodiedAgentsSys/skills/optimization/parameter_optimizer.py"
)
optimizer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(optimizer_module)

ParameterOptimizer = optimizer_module.ParameterOptimizer


async def test_record_execution():
    """测试记录执行"""
    print("\n" + "="*60)
    print("测试1: 记录执行结果")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 记录几次执行
    for i in range(5):
        result = await optimizer.record_execution(
            skill_name="pick_and_place",
            params={"speed": 0.3 + i * 0.1, "force": 10.0},
            result={
                "success": i < 4,  # 前4次成功
                "duration": 3.5 - i * 0.2,
                "quality": 0.7 + i * 0.05
            }
        )
        print(f"  记录 {i+1}: {result['success']}, ID: {result['record_id']}")
    
    print(f"\n  总记录数: {optimizer.get_record_count()}")


async def test_optimize():
    """测试参数优化"""
    print("\n" + "="*60)
    print("测试2: 参数优化")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 记录一些执行（包含不同参数）
    params_list = [
        {"speed": 0.3, "force": 8.0},
        {"speed": 0.5, "force": 8.0},
        {"speed": 0.7, "force": 8.0},
        {"speed": 0.3, "force": 12.0},
        {"speed": 0.5, "force": 12.0},
        {"speed": 0.7, "force": 12.0},
    ]
    
    # 模拟不同的成功率
    for i, params in enumerate(params_list):
        success = i % 2 == 0  # 交替成功
        await optimizer.record_execution(
            skill_name="pick_and_place",
            params=params,
            result={
                "success": success,
                "duration": 3.5 - params["speed"] * 2,
                "quality": 0.8 if success else 0.3
            }
        )
    
    # 优化
    result = await optimizer.optimize(
        skill_name="pick_and_place",
        target_metric="quality",
        goal="maximize"
    )
    
    print(f"  优化结果:")
    print(f"    成功: {result['success']}")
    print(f"    收敛: {result.get('converged', False)}")
    print(f"    迭代次数: {result['iterations']}")
    print(f"    最佳参数: {result['best_params']}")
    print(f"    最佳分数: {result['best_score']:.2f}")
    if result.get('suggestions'):
        print(f"    建议:")
        for s in result['suggestions']:
            print(f"      - {s}")


async def test_get_best_params():
    """测试获取最佳参数"""
    print("\n" + "="*60)
    print("测试3: 获取最佳参数")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 记录一些执行
    for i in range(5):
        await optimizer.record_execution(
            skill_name="gripper",
            params={"force": 5.0 + i * 2, "strategy": "parallel" if i < 3 else "pinch"},
            result={"success": i >= 2, "duration": 1.0 + i * 0.1}
        )
    
    result = await optimizer.get_best_params(skill_name="gripper")
    
    print(f"  获取最佳参数:")
    print(f"    成功: {result['success']}")
    print(f"    最佳参数: {result['params']}")
    print(f"    统计:")
    for k, v in result['metrics'].items():
        print(f"      {k}: {v:.3f}")


async def test_get_statistics():
    """测试获取统计信息"""
    print("\n" + "="*60)
    print("测试4: 获取统计信息")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 记录一些执行
    for i in range(10):
        skill = "motion" if i < 5 else "gripper"
        await optimizer.record_execution(
            skill_name=skill,
            params={"speed": 0.5},
            result={
                "success": i < 8,
                "duration": 2.0 + np.random.rand(),
                "quality": 0.7 + np.random.rand() * 0.3,
                "energy": 10.0 + np.random.rand() * 5
            }
        )
    
    # 全部统计
    result = await optimizer.get_statistics()
    print(f"  全部统计:")
    print(f"    总记录数: {result['statistics']['total_records']}")
    print(f"    成功率: {result['statistics']['success_rate']:.2%}")
    print(f"    平均时长: {result['statistics']['avg_duration']:.2f}s")
    print(f"    平均质量: {result['statistics']['avg_quality']:.2f}")
    
    # 按Skill统计
    result = await optimizer.get_statistics(skill_name="motion")
    print(f"\n  Motion统计:")
    print(f"    成功率: {result['statistics']['success_rate']:.2%}")


async def test_register_params():
    """测试注册参数配置"""
    print("\n" + "="*60)
    print("测试5: 注册参数配置")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 注册新的参数配置
    configs = [
        {"name": "custom_param", "param_type": "continuous", "min_value": 0.0, "max_value": 100.0, "default_value": 50.0},
        {"name": "mode", "param_type": "categorical", "options": ["fast", "slow", "balanced"], "default_value": "balanced"}
    ]
    
    result = await optimizer.register_params(
        skill_category="custom_skill",
        param_configs=configs
    )
    
    print(f"  注册参数:")
    print(f"    成功: {result['success']}")
    print(f"    参数数量: {result['param_count']}")


async def test_clear_records():
    """测试清除记录"""
    print("\n" + "="*60)
    print("测试6: 清除记录")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 添加一些记录
    await optimizer.record_execution(
        skill_name="skill1",
        params={},
        result={"success": True}
    )
    await optimizer.record_execution(
        skill_name="skill2",
        params={},
        result={"success": True}
    )
    
    print(f"  添加后记录数: {optimizer.get_record_count()}")
    
    # 清除特定Skill
    result = await optimizer.clear_records(skill_name="skill1")
    print(f"  清除skill1后:")
    print(f"    成功: {result['success']}")
    print(f"    清除数量: {result['cleared_count']}")
    print(f"    剩余: {result['remaining_count']}")
    
    # 清除全部
    result = await optimizer.clear_records()
    print(f"  清除全部:")
    print(f"    成功: {result['success']}")
    print(f"    剩余: {result['remaining_count']}")


async def test_export_records():
    """测试导出记录"""
    print("\n" + "="*60)
    print("测试7: 导出记录")
    print("="*60)
    
    optimizer = ParameterOptimizer(_simulated=True)
    
    # 添加一些记录
    for i in range(3):
        await optimizer.record_execution(
            skill_name="test_skill",
            params={"param1": i},
            result={"success": True, "duration": 1.0}
        )
    
    # 导出
    result = await optimizer.export_records(
        skill_name="test_skill",
        filename="test_records.json"
    )
    
    print(f"  导出结果:")
    print(f"    成功: {result['success']}")
    print(f"    文件名: {result['filename']}")
    print(f"    记录数: {result['record_count']}")
    print(f"  预览:")
    print(f"  {result['preview'][:200]}...")


async def test_optimization_methods():
    """测试不同优化方法"""
    print("\n" + "="*60)
    print("测试8: 不同优化方法")
    print("="*60)
    
    methods = ["grid_search", "random_search", "gradient"]
    
    for method in methods:
        optimizer = ParameterOptimizer(_simulated=True, optimization_method=method)
        
        # 添加记录
        for i in range(10):
            await optimizer.record_execution(
                skill_name="test",
                params={"p1": i * 0.1, "p2": i * 0.2},
                result={"success": i > 3, "quality": 0.5 + i * 0.05}
            )
        
        # 优化
        result = await optimizer.optimize(skill_name="test")
        
        print(f"  {method}:")
        print(f"    成功: {result['success']}")
        if result['success']:
            print(f"    最佳参数: {result.get('best_params', {})}")


async def main():
    print("\n" + "="*60)
    print("ParameterOptimizer测试")
    print("="*60)
    
    await test_record_execution()
    await test_optimize()
    await test_get_best_params()
    await test_get_statistics()
    await test_register_params()
    await test_clear_records()
    await test_export_records()
    await test_optimization_methods()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
