"""
测试Perception3DSkill组件
"""
import asyncio
import sys
import os
import importlib.util
import numpy as np

# 直接加载perception_3d_skill模块
spec = importlib.util.spec_from_file_location(
    "perception_3d_skill",
    "/media/hzm/data_disk/EmbodiedAgentsSys/skills/vision/perception_3d_skill.py"
)
perception_3d_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perception_3d_module)

Perception3DSkill = perception_3d_module.Perception3DSkill
Pose6D = perception_3d_module.Pose6D


async def test_get_point_cloud():
    """测试获取点云"""
    print("\n" + "="*60)
    print("测试1: 获取点云")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(action="get_point_cloud")
    
    print(f"  成功: {result['success']}")
    print(f"  点数量: {result['point_count']}")
    print(f"  图像尺寸: {result['width']} x {result['height']}")
    print(f"  点云范围:")
    print(f"    最小点: {result['bounds']['min']}")
    print(f"    最大点: {result['bounds']['max']}")


async def test_localize_3d():
    """测试3D目标定位"""
    print("\n" + "="*60)
    print("测试2: 3D目标定位")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    # 定位特定物体
    result = await skill.execute(action="localize_3d", target_name="零件A")
    print(f"  定位零件A:")
    print(f"    成功: {result['success']}")
    if result['success']:
        print(f"    位置: {result['position']}")
        print(f"    尺寸: {result['dimensions']}")
        print(f"    置信度: {result['confidence']}")
    
    # 获取所有物体
    print(f"\n  获取所有物体:")
    result = await skill.execute(action="localize_3d")
    print(f"    成功: {result['success']}")
    print(f"    物体数量: {result['count']}")
    for obj in result.get('objects', []):
        print(f"    - {obj['name']}: {obj['position']}")


async def test_segment_objects():
    """测试目标分割"""
    print("\n" + "="*60)
    print("测试3: 目标分割")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(action="segment_objects")
    
    print(f"  成功: {result['success']}")
    print(f"  分割物体数量: {result['count']}")
    
    for obj in result.get('objects', []):
        print(f"    - {obj['name']}:")
        print(f"        类别ID: {obj['class_id']}")
        print(f"        置信度: {obj['confidence']:.2f}")
        print(f"        边界盒: {obj['bbox_min']} ~ {obj['bbox_max']}")
        print(f"        中心: {obj['center']}")
        print(f"        尺寸: {obj['dimensions']}")


async def test_detect_planes():
    """测试平面检测"""
    print("\n" + "="*60)
    print("测试4: 平面检测")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(action="detect_planes")
    
    print(f"  成功: {result['success']}")
    print(f"  检测到平面数量: {result['count']}")
    
    for plane in result.get('planes', []):
        print(f"    - 类型: {plane['plane_type']}")
        print(f"      法向量: {plane['normal']}")
        print(f"      面积: {plane['area']:.2f} m²")


async def test_calculate_pose():
    """测试姿态计算"""
    print("\n" + "="*60)
    print("测试5: 姿态计算")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(action="calculate_pose", object_name="零件A")
    
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  物体: {result['object_name']}")
        print(f"  位置: {result['pose']['position']}")
        print(f"  姿态: {result['pose']['orientation']}")
        print(f"  置信度: {result['confidence']:.2f}")


async def test_fuse_sensors():
    """测试传感器融合"""
    print("\n" + "="*60)
    print("测试6: 传感器融合")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    result = await skill.execute(action="fuse_sensors")
    
    print(f"  成功: {result['success']}")
    print(f"  融合位置: {result['fused_position']}")
    print(f"  置信度: {result['confidence']:.2f}")
    print(f"  数据源: {result['sources']}")


async def test_pose_6d():
    """测试Pose6D类"""
    print("\n" + "="*60)
    print("测试7: Pose6D类")
    print("="*60)
    
    pose = Pose6D(
        position=[0.3, 0.1, 0.05],
        orientation=[0.0, 0.1, 0.2]
    )
    
    print(f"  位置: {pose.position}")
    print(f"  姿态: {pose.orientation}")
    print(f"  变换矩阵:")
    print(pose.to_matrix())
    print(f"  字典:")
    print(pose.to_dict())


async def test_depth_to_pointcloud():
    """测试深度图转点云"""
    print("\n" + "="*60)
    print("测试8: 深度图转点云")
    print("="*60)
    
    skill = Perception3DSkill(_simulated=True)
    await skill.initialize()
    
    # 创建简单的深度图
    depth = np.ones((100, 100)) * 2.0
    depth[40:60, 40:60] = 0.5  # 中间一个物体
    
    points = skill.depth_to_pointcloud(depth)
    
    print(f"  输入深度图尺寸: {depth.shape}")
    print(f"  生成的点数量: {len(points)}")
    print(f"  点云范围:")
    print(f"    X: [{points[:, 0].min():.3f}, {points[:, 0].max():.3f}]")
    print(f"    Y: [{points[:, 1].min():.3f}, {points[:, 1].max():.3f}]")
    print(f"    Z: [{points[:, 2].min():.3f}, {points[:, 2].max():.3f}]")


async def main():
    print("\n" + "="*60)
    print("Perception3DSkill测试")
    print("="*60)
    
    await test_get_point_cloud()
    await test_localize_3d()
    await test_segment_objects()
    await test_detect_planes()
    await test_calculate_pose()
    await test_fuse_sensors()
    await test_pose_6d()
    await test_depth_to_pointcloud()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
