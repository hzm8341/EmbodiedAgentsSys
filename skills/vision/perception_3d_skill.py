"""
Perception3DSkill - 3D感知模块
===========================

该模块提供3D环境感知能力，支持深度图像处理和3D目标定位。

功能:
- 深度图处理: 将深度图像转换为3D点云
- 3D目标检测: 从点云中检测和分割目标物体
- 空间定位: 获取物体在机器人坐标系中的精确位置
- 表面重建: 生成物体或场景的3D模型

使用示例:
    from skills.vision.perception_3d_skill import Perception3DSkill
    
    skill = Perception3DSkill()
    
    # 获取场景点云
    result = await skill.execute(action="get_point_cloud")
    
    # 定位3D目标
    result = await skill.execute(
        action="localize_3d",
        target_name="零件A"
    )
    
    # 平面检测
    result = await skill.execute(action="detect_planes")
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class Perception3DAction(Enum):
    """3D感知动作类型"""
    GET_POINT_CLOUD = "get_point_cloud"     # 获取点云
    LOCALIZE_3D = "localize_3d"             # 3D目标定位
    SEGMENT_OBJECTS = "segment_objects"      # 目标分割
    DETECT_PLANES = "detect_planes"          # 平面检测
    CALCULATE_POSE = "calculate_pose"        # 计算物体姿态
    FUSE_SENSORS = "fuse_sensors"           # 多传感器融合


@dataclass
class PointCloudData:
    """点云数据"""
    points: np.ndarray = field(default_factory=lambda: np.array([]))  # Nx3
    colors: np.ndarray = field(default_factory=lambda: np.array([]))  # Nx3
    normals: np.ndarray = field(default_factory=lambda: np.array([]))  # Nx3
    timestamps: float = 0.0
    width: int = 0
    height: int = 0
    
    @property
    def size(self) -> int:
        """点数量"""
        return len(self.points)
    
    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return self.size == 0


@dataclass
class DetectedObject3D:
    """3D检测到的物体"""
    name: str
    class_id: int
    confidence: float
    # 3D边界盒
    bbox_min: List[float]  # [x, y, z] 最小点
    bbox_max: List[float]  # [x, y, z] 最大点
    # 中心位置
    center: List[float]    # [x, y, z]
    # 姿态 (roll, pitch, yaw)
    pose: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # 分割点云索引
    segment_indices: List[int] = field(default_factory=list)
    # 尺寸 (长, 宽, 高)
    dimensions: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class Plane:
    """检测到的平面"""
    # 平面方程 ax + by + cz + d = 0
    coefficients: List[float]  # [a, b, c, d]
    # 平面上的采样点
    points: np.ndarray = field(default_factory=np.array)
    # 平面法向量
    normal: List[float] = field(default_factory=lambda: [0.0, 0.0, 1.0])
    # 平面类型 (horizontal, vertical, other)
    plane_type: str = "other"
    # 平面面积
    area: float = 0.0


@dataclass
class Pose6D:
    """6D位姿"""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # x, y, z (m)
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # roll, pitch, yaw (rad)
    
    def to_matrix(self) -> np.ndarray:
        """转换为4x4变换矩阵"""
        # 简化实现：只包含位置
        matrix = np.eye(4)
        matrix[:3, 3] = self.position
        return matrix
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "position": self.position,
            "orientation": self.orientation
        }


class Perception3DSkill:
    """
    3D感知Skill - 提供3D环境感知能力
    
    支持的能力:
    1. 点云获取与处理
    2. 3D目标检测与分割
    3. 空间定位与姿态估计
    4. 平面检测与分割
    5. 多传感器融合
    
    注意: 这是逻辑实现，ROS集成部分可在环境准备好后添加。
    """
    
    def __init__(
        self,
        component_name: str = "perception_3d",
        depth_topic: str = "/camera/depth",
        rgb_topic: str = "/camera/rgb",
        pointcloud_topic: str = "/camera/points",
        _simulated: bool = True
    ):
        """
        初始化3D感知模块
        
        Args:
            component_name: 组件名称
            depth_topic: 深度图像话题
            rgb_topic: RGB图像话题
            pointcloud_topic: 点云话题
            _simulated: 是否使用模拟模式
        """
        self.name = component_name
        self.depth_topic = depth_topic
        self.rgb_topic = rgb_topic
        self.pointcloud_topic = pointcloud_topic
        self._simulated = _simulated
        self._initialized = False
        
        # 相机内参 (模拟)
        self._camera_matrix = np.array([
            [525.0, 0.0, 319.5],
            [0.0, 525.0, 239.5],
            [0.0, 0.0, 1.0]
        ])
        self._depth_scale = 0.001  # mm to m
        
        # 模拟的场景物体
        self._simulated_objects = {
            "零件A": {"position": [0.3, 0.1, 0.05], "size": [0.05, 0.03, 0.02]},
            "零件B": {"position": [0.35, -0.1, 0.05], "size": [0.04, 0.04, 0.03]},
            "料框": {"position": [0.0, 0.2, 0.0], "size": [0.3, 0.2, 0.1]},
            "工作台": {"position": [0.3, 0.0, 0.0], "size": [0.5, 0.3, 0.02]},
        }
    
    async def initialize(self) -> bool:
        """初始化3D感知模块"""
        if self._simulated:
            self._initialized = True
            return True
            
        # TODO: ROS初始化
        # 订阅深度图像话题
        # 订阅点云话题
        # 初始化PCL/Open3D处理
        return True
    
    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """
        执行3D感知动作
        
        Args:
            action: 动作类型 (见 Perception3DAction)
            **params: 动作参数
            
        Returns:
            执行结果字典
        """
        if not self._initialized:
            await self.initialize()
            
        action_enum = self._str_to_action(action)
        
        try:
            if action_enum == Perception3DAction.GET_POINT_CLOUD:
                return await self._get_point_cloud(**params)
            elif action_enum == Perception3DAction.LOCALIZE_3D:
                return await self._localize_3d(**params)
            elif action_enum == Perception3DAction.SEGMENT_OBJECTS:
                return await self._segment_objects(**params)
            elif action_enum == Perception3DAction.DETECT_PLANES:
                return await self._detect_planes(**params)
            elif action_enum == Perception3DAction.CALCULATE_POSE:
                return await self._calculate_pose(**params)
            elif action_enum == Perception3DAction.FUSE_SENSORS:
                return await self._fuse_sensors(**params)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _str_to_action(self, action: str) -> Perception3DAction:
        """字符串转换为动作枚举"""
        action_map = {
            "get_point_cloud": Perception3DAction.GET_POINT_CLOUD,
            "point_cloud": Perception3DAction.GET_POINT_CLOUD,
            "pc": Perception3DAction.GET_POINT_CLOUD,
            "localize_3d": Perception3DAction.LOCALIZE_3D,
            "localize": Perception3DAction.LOCALIZE_3D,
            "localize_3d": Perception3DAction.LOCALIZE_3D,
            "segment_objects": Perception3DAction.SEGMENT_OBJECTS,
            "segment": Perception3DAction.SEGMENT_OBJECTS,
            "detect_planes": Perception3DAction.DETECT_PLANES,
            "planes": Perception3DAction.DETECT_PLANES,
            "calculate_pose": Perception3DAction.CALCULATE_POSE,
            "pose": Perception3DAction.CALCULATE_POSE,
            "fuse_sensors": Perception3DAction.FUSE_SENSORS,
            "fuse": Perception3DAction.FUSE_SENSORS,
        }
        
        return action_map.get(action.lower(), Perception3DAction.GET_POINT_CLOUD)
    
    async def _get_point_cloud(self, **kwargs) -> Dict[str, Any]:
        """获取点云"""
        if self._simulated:
            # 生成模拟点云
            width, height = 480, 640
            
            # 生成网格点
            u, v = np.meshgrid(np.arange(width), np.arange(height))
            u = u.flatten()
            v = v.flatten()
            
            # 模拟深度值 (平面 + 一些物体)
            depth = np.ones((height, width)) * 2.0  # 2m 远处的平面
            
            # 添加一些物体
            # 零件A
            cx1, cy1 = int(0.3 * width), int(0.4 * height)
            r1 = 30
            mask1 = (u - cx1)**2 + (v - cy1)**2 < r1**2
            depth[mask1.reshape(height, width)] = 0.5
            
            # 零件B
            cx2, cy2 = int(0.35 * width), int(0.6 * height)
            r2 = 25
            mask2 = (u - cx2)**2 + (v - cy2)**2 < r2**2
            depth[mask2.reshape(height, width)] = 0.6
            
            depth = depth.flatten() * self._depth_scale
            
            # 转换为3D点
            fx, fy = self._camera_matrix[0, 0], self._camera_matrix[1, 1]
            cx, cy = self._camera_matrix[0, 2], self._camera_matrix[1, 2]
            
            x = (u - cx) * depth / fx
            y = (v - cy) * depth / fy
            z = depth
            
            points = np.column_stack([x, y, z])
            
            # 生成颜色
            colors = np.random.rand(height * width, 3) * 255
            
            pc_data = PointCloudData(
                points=points,
                colors=colors,
                width=width,
                height=height,
                timestamps=asyncio.get_event_loop().time()
            )
            
            return {
                "success": True,
                "action": "get_point_cloud",
                "point_count": pc_data.size,
                "width": width,
                "height": height,
                "bounds": {
                    "min": points.min(axis=0).tolist(),
                    "max": points.max(axis=0).tolist()
                }
            }
        else:
            # TODO: ROS实现
            pass
    
    async def _localize_3d(self, target_name: str = None, **kwargs) -> Dict[str, Any]:
        """3D目标定位"""
        if self._simulated:
            # 如果指定了目标名称
            if target_name and target_name in self._simulated_objects:
                obj = self._simulated_objects[target_name]
                return {
                    "success": True,
                    "action": "localize_3d",
                    "target_name": target_name,
                    "position": obj["position"],
                    "dimensions": obj["size"],
                    "pose": Pose6D(position=obj["position"]).to_dict(),
                    "confidence": 0.95
                }
            
            # 否则返回所有检测到的物体
            objects = []
            for name, obj in self._simulated_objects.items():
                objects.append({
                    "name": name,
                    "position": obj["position"],
                    "dimensions": obj["size"],
                    "confidence": 0.9
                })
            
            return {
                "success": True,
                "action": "localize_3d",
                "objects": objects,
                "count": len(objects)
            }
        else:
            # TODO: ROS实现
            # 使用PCL进行目标检测
            pass
    
    async def _segment_objects(self, **kwargs) -> Dict[str, Any]:
        """目标分割"""
        if self._simulated:
            # 模拟分割结果
            objects = []
            for name, obj in self._simulated_objects.items():
                obj_data = DetectedObject3D(
                    name=name,
                    class_id=hash(name) % 100,
                    confidence=0.9,
                    bbox_min=[p - s/2 for p, s in zip(obj["position"], obj["size"])],
                    bbox_max=[p + s/2 for p, s in zip(obj["position"], obj["size"])],
                    center=obj["position"],
                    dimensions=obj["size"],
                    segment_indices=list(range(100))
                )
                objects.append({
                    "name": obj_data.name,
                    "class_id": obj_data.class_id,
                    "confidence": obj_data.confidence,
                    "bbox_min": obj_data.bbox_min,
                    "bbox_max": obj_data.bbox_max,
                    "center": obj_data.center,
                    "dimensions": obj_data.dimensions
                })
            
            return {
                "success": True,
                "action": "segment_objects",
                "objects": objects,
                "count": len(objects)
            }
        else:
            # TODO: ROS实现
            pass
    
    async def _detect_planes(self, **kwargs) -> Dict[str, Any]:
        """平面检测"""
        if self._simulated:
            # 模拟检测到平面
            planes = [
                {
                    "coefficients": [0.0, 0.0, 1.0, 0.0],  # z = 0
                    "normal": [0.0, 0.0, 1.0],
                    "plane_type": "horizontal",
                    "area": 1.0,
                    "points_count": 1000
                }
            ]
            
            return {
                "success": True,
                "action": "detect_planes",
                "planes": planes,
                "count": len(planes)
            }
        else:
            # TODO: ROS实现
            pass
    
    async def _calculate_pose(self, object_name: str = None, **kwargs) -> Dict[str, Any]:
        """计算物体姿态"""
        if self._simulated:
            if object_name and object_name in self._simulated_objects:
                obj = self._simulated_objects[object_name]
                pose = Pose6D(
                    position=obj["position"],
                    orientation=[0.0, 0.0, 0.0]  # 默认朝上
                )
                
                return {
                    "success": True,
                    "action": "calculate_pose",
                    "object_name": object_name,
                    "pose": pose.to_dict(),
                    "confidence": 0.92
                }
            
            return {
                "success": False,
                "error": f"Object {object_name} not found"
            }
        else:
            # TODO: ROS实现
            pass
    
    async def _fuse_sensors(self, **kwargs) -> Dict[str, Any]:
        """多传感器融合"""
        if self._simulated:
            # 模拟融合结果
            return {
                "success": True,
                "action": "fuse_sensors",
                "fused_position": [0.3, 0.05, 0.05],
                "confidence": 0.95,
                "sources": ["depth_camera", "force_sensor", "joint_encoder"]
            }
        else:
            # TODO: ROS实现
            pass
    
    def depth_to_pointcloud(self, depth: np.ndarray) -> np.ndarray:
        """
        将深度图像转换为点云
        
        Args:
            depth: 深度图像 (H x W)
            
        Returns:
            点云 (N x 3)
        """
        height, width = depth.shape
        
        u, v = np.meshgrid(np.arange(width), np.arange(height))
        u = u.flatten()
        v = v.flatten()
        
        depth_flat = depth.flatten() * self._depth_scale
        
        fx, fy = self._camera_matrix[0, 0], self._camera_matrix[1, 1]
        cx, cy = self._camera_matrix[0, 2], self._camera_matrix[1, 2]
        
        x = (u - cx) * depth_flat / fx
        y = (v - cy) * depth_flat / fy
        z = depth_flat
        
        # 过滤无效点
        valid = z > 0
        
        return np.column_stack([x[valid], y[valid], z[valid]])
    
    def set_camera_intrinsics(self, fx: float, fy: float, cx: float, cy: float):
        """设置相机内参"""
        self._camera_matrix = np.array([
            [fx, 0.0, cx],
            [0.0, fy, cy],
            [0.0, 0.0, 1.0]
        ])
    
    def set_depth_scale(self, scale: float):
        """设置深度尺度"""
        self._depth_scale = scale


def create_perception_3d_skill(
    component_name: str = "perception_3d",
    simulated: bool = True
) -> Perception3DSkill:
    """
    工厂函数: 创建Perception3DSkill实例
    
    Args:
        component_name: 组件名称
        simulated: 是否使用模拟模式
        
    Returns:
        Perception3DSkill实例
    """
    return Perception3DSkill(
        component_name=component_name,
        _simulated=simulated
    )
