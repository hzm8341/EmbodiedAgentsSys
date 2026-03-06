"""
ForceControlSkill - 力控模块
===========================

该模块提供机器人末端力感知与控制能力，支持柔性装配场景。

功能:
- 力/力矩监控: 实时读取末端力传感器数据
- 阻抗控制: 实现柔顺控制，支持装配过程的力跟随
- 碰撞检测: 检测异常接触并触发安全停止
- 装配引导: 基于力反馈的精确装配

使用示例:
    from skills.arm_control.force_control_skill import ForceControlSkill
    
    skill = ForceControlSkill()
    
    # 监控当前力
    force = await skill.execute(action="read_force")
    
    # 执行阻抗控制移动
    result = await skill.execute(
        action="impedance_move",
        target_position=[0.3, 0.1, 0.2],
        stiffness=100.0,
        damping=10.0
    )
    
    # 执行装配插入
    result = await skill.execute(
        action="insert",
        target_position=[0.3, 0.0, 0.1],
        max_force=5.0
    )
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class ForceControlAction(Enum):
    """力控动作类型"""
    READ_FORCE = "read_force"           # 读取当前力
    IMPEDANCE_MOVE = "impedance_move"   # 阻抗控制移动
    FORCE_MOVE = "force_move"           # 力跟随移动
    INSERT = "insert"                  # 插入操作
    CONTACT_DETECT = "contact_detect"   # 接触检测
    EMERGENCY_STOP = "emergency_stop"  # 紧急停止


@dataclass
class ForceData:
    """力传感器数据"""
    # 力 (N)
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    # 力矩 (Nm)
    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0
    # 元数据
    timestamp: float = 0.0
    valid: bool = True
    
    @property
    def total_force(self) -> float:
        """计算合力的模"""
        return np.sqrt(self.fx**2 + self.fy**2 + self.fz**2)
    
    @property
    def total_torque(self) -> float:
        """计算合矩的模"""
        return np.sqrt(self.tx**2 + self.ty**2 + self.tz**2)
    
    @property
    def magnitude(self) -> float:
        """总力/力矩幅值"""
        return self.total_force + self.total_torque
    
    def exceeds_threshold(self, force_threshold: float, torque_threshold: float = 1.0) -> bool:
        """检查是否超过阈值"""
        return self.total_force > force_threshold or self.total_torque > torque_threshold
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "fx": self.fx, "fy": self.fy, "fz": self.fz,
            "tx": self.tx, "ty": self.ty, "tz": self.tz,
            "total_force": self.total_force,
            "total_torque": self.total_torque,
            "timestamp": self.timestamp,
            "valid": self.valid
        }


@dataclass
class ImpedanceParams:
    """阻抗控制参数"""
    # 刚度 (N/m) - 越大越硬，越小越柔顺
    stiffness: float = 100.0
    # 阻尼 (N·s/m)
    damping: float = 10.0
    # 惯性 (kg)
    mass: float = 1.0
    # 力阈值 (N)
    force_limit: float = 10.0
    # 力矩阈值 (Nm)
    torque_limit: float = 1.0


@dataclass
class InsertParams:
    """插入操作参数"""
    # 目标位置 [x, y, z] (m)
    target_position: List[float]
    # 最大允许力 (N)
    max_force: float = 5.0
    # 最大允许力矩 (Nm)
    max_torque: float = 0.5
    # 插入速度 (m/s)
    insert_speed: float = 0.01
    # 搜索范围 (m) - 偏离目标时的搜索半径
    search_radius: float = 0.005
    # 搜索尝试次数
    max_search_attempts: int = 3


@dataclass
class CollisionResult:
    """碰撞检测结果"""
    detected: bool = False
    collision_force: float = 0.0
    collision_direction: Optional[str] = None
    stop_required: bool = False
    message: str = ""


class ForceControlSkill:
    """
    力控Skill - 提供机器人末端力感知与控制能力
    
    支持的能力:
    1. 实时力监控
    2. 阻抗控制移动
    3. 力跟随移动
    4. 精确插入操作
    5. 碰撞检测与安全停止
    
    注意: 这是逻辑实现，ROS集成部分可在环境准备好后添加。
    """
    
    # 默认阻抗参数
    DEFAULT_IMPEDANCE = ImpedanceParams(
        stiffness=100.0,
        damping=10.0,
        mass=1.0,
        force_limit=10.0,
        torque_limit=1.0
    )
    
    def __init__(
        self,
        component_name: str = "force_control",
        force_topic: str = "/force_sensor/data",
       _simulated: bool = True
    ):
        """
        初始化力控模块
        
        Args:
            component_name: 组件名称
            force_topic: 力传感器话题
            _simulated: 是否使用模拟模式
        """
        self.name = component_name
        self.force_topic = force_topic
        self._simulated = _simulated
        self._initialized = False
        self._last_force = ForceData()
        self._emergency_stopped = False
        
        # 阻抗控制状态
        self._impedance_enabled = False
        self._current_impedance = self.DEFAULT_IMPEDANCE
        
        # 碰撞检测配置
        self._collision_threshold = 15.0  # N
        self._collision_history: List[ForceData] = []
        self._max_history = 100
        
    async def initialize(self) -> bool:
        """初始化力控模块"""
        if self._simulated:
            self._initialized = True
            return True
            
        # TODO: ROS初始化
        # 订阅力传感器话题
        # 初始化阻抗控制器
        return True
    
    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """
        执行力控动作
        
        Args:
            action: 动作类型 (见 ForceControlAction)
            **params: 动作参数
            
        Returns:
            执行结果字典
        """
        if not self._initialized:
            await self.initialize()
            
        if self._emergency_stopped and action != "emergency_reset":
            return {
                "success": False,
                "error": "Emergency stop is active. Call emergency_reset first.",
                "force": self._last_force.to_dict()
            }
            
        action_enum = self._str_to_action(action)
        
        try:
            if action_enum == ForceControlAction.READ_FORCE:
                return await self._read_force()
            elif action_enum == ForceControlAction.IMPEDANCE_MOVE:
                return await self._impedance_move(**params)
            elif action_enum == ForceControlAction.FORCE_MOVE:
                return await self._force_move(**params)
            elif action_enum == ForceControlAction.INSERT:
                return await self._insert(**params)
            elif action_enum == ForceControlAction.CONTACT_DETECT:
                return await self._contact_detect(**params)
            elif action_enum == ForceControlAction.EMERGENCY_STOP:
                return await self._emergency_stop()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _str_to_action(self, action: str) -> ForceControlAction:
        """字符串转换为动作枚举"""
        action_map = {
            "read_force": ForceControlAction.READ_FORCE,
            "read": ForceControlAction.READ_FORCE,
            "force": ForceControlAction.READ_FORCE,
            "impedance_move": ForceControlAction.IMPEDANCE_MOVE,
            "impedance": ForceControlAction.IMPEDANCE_MOVE,
            "force_move": ForceControlAction.FORCE_MOVE,
            "force_follow": ForceControlAction.FORCE_MOVE,
            "insert": ForceControlAction.INSERT,
            "assemble": ForceControlAction.INSERT,
            "contact_detect": ForceControlAction.CONTACT_DETECT,
            "contact": ForceControlAction.CONTACT_DETECT,
            "collision": ForceControlAction.CONTACT_DETECT,
            "emergency_stop": ForceControlAction.EMERGENCY_STOP,
            "stop": ForceControlAction.EMERGENCY_STOP,
        }
        
        return action_map.get(action.lower(), ForceControlAction.READ_FORCE)
    
    async def _read_force(self) -> Dict[str, Any]:
        """读取当前力数据"""
        if self._simulated:
            # 模拟: 返回带噪声的零力
            import time
            noise = np.random.randn(6) * 0.1
            force = ForceData(
                fx=noise[0], fy=noise[1], fz=noise[2],
                tx=noise[3], ty=noise[4], tz=noise[5],
                timestamp=time.time(),
                valid=True
            )
        else:
            # TODO: 真实ROS读取
            # 读取 /force_sensor/data 话题
            force = ForceData()
            
        self._last_force = force
        
        # 更新历史
        self._collision_history.append(force)
        if len(self._collision_history) > self._max_history:
            self._collision_history.pop(0)
            
        return {
            "success": True,
            "force": force.to_dict(),
            "action": "read_force"
        }
    
    async def _impedance_move(
        self,
        target_position: List[float],
        stiffness: float = 100.0,
        damping: float = 10.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        阻抗控制移动
        
        阻抗控制公式: F = K * (x_d - x) - D * v
        其中:
        - K: 刚度 (stiffness)
        - D: 阻尼 (damping)
        - x_d: 目标位置
        - x: 当前位置
        - v: 末端速度
        
        Args:
            target_position: 目标位置 [x, y, z] (m)
            stiffness: 刚度系数
            damping: 阻尼系数
            
        Returns:
            执行结果
        """
        # 更新阻抗参数
        self._current_impedance = ImpedanceParams(
            stiffness=stiffness,
            damping=damping,
            force_limit=kwargs.get("force_limit", 10.0),
            torque_limit=kwargs.get("torque_limit", 1.0)
        )
        self._impedance_enabled = True
        
        if self._simulated:
            # 模拟阻抗移动
            await asyncio.sleep(0.1)  # 模拟执行时间
            
            # 计算预期接触力
            expected_force = np.random.uniform(0, 2.0)
            
            return {
                "success": True,
                "action": "impedance_move",
                "target_position": target_position,
                "stiffness": stiffness,
                "damping": damping,
                "status": "moving",
                "message": f"Moving to {target_position} with impedance control"
            }
        else:
            # TODO: ROS实现
            # 发送阻抗控制目标
            # 监控力反馈
            pass
    
    async def _force_move(
        self,
        direction: List[float],
        target_force: float = 1.0,
        max_displacement: float = 0.05,
        **kwargs
    ) -> Dict[str, Any]:
        """
        力跟随移动
        
        保持恒定的接触力沿指定方向移动
        
        Args:
            direction: 移动方向向量 [x, y, z] (归一化)
            target_force: 目标接触力 (N)
            max_displacement: 最大移动距离 (m)
            
        Returns:
            执行结果
        """
        if self._simulated:
            await asyncio.sleep(0.1)
            
            return {
                "success": True,
                "action": "force_move",
                "direction": direction,
                "target_force": target_force,
                "status": "completed",
                "actual_force": target_force + np.random.uniform(-0.2, 0.2),
                "displacement": max_displacement * np.random.uniform(0.8, 1.0)
            }
        else:
            # TODO: ROS实现
            pass
    
    async def _insert(
        self,
        target_position: List[float],
        max_force: float = 5.0,
        max_torque: float = 0.5,
        insert_speed: float = 0.01,
        search_radius: float = 0.005,
        max_search_attempts: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        插入操作 - 用于零件装配
        
        策略:
        1. 移动到目标位置上方
        2. 缓慢下降并监控力
        3. 如果遇到阻力，尝试小范围搜索
        4. 达到目标位置或超过力阈值时停止
        
        Args:
            target_position: 目标位置 [x, y, z] (m)
            max_force: 最大允许力 (N)
            max_torque: 最大允许力矩 (Nm)
            insert_speed: 插入速度 (m/s)
            search_radius: 搜索半径 (m)
            max_search_attempts: 最大搜索次数
            
        Returns:
            执行结果
        """
        if self._simulated:
            # 模拟插入过程
            steps = 10
            force_values = []
            
            for i in range(steps):
                await asyncio.sleep(0.02)
                
                # 模拟力数据
                force = np.random.uniform(0.5, max_force * 0.8)
                force_values.append(force)
                
                # 检查是否超过阈值
                if force > max_force:
                    return {
                        "success": False,
                        "action": "insert",
                        "target_position": target_position,
                        "error": f"Force limit exceeded: {force:.2f}N > {max_force}N",
                        "current_position": target_position[:2] + [target_position[2] * (i/steps)],
                        "applied_force": force,
                        "status": "force_limited"
                    }
            
            return {
                "success": True,
                "action": "insert",
                "target_position": target_position,
                "final_position": target_position,
                "applied_force": np.mean(force_values),
                "max_force": max(force_values),
                "status": "completed",
                "message": "Insertion completed successfully"
            }
        else:
            # TODO: ROS实现
            pass
    
    async def _contact_detect(
        self,
        threshold: float = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        接触检测
        
        Args:
            threshold: 碰撞力阈值 (N)，默认使用配置的阈值
            
        Returns:
            碰撞检测结果
        """
        threshold = threshold or self._collision_threshold
        
        # 读取当前力
        result = await self._read_force()
        force = self._last_force
        
        # 检测碰撞
        collision = force.exceeds_threshold(threshold)
        
        # 确定碰撞方向
        direction = None
        if collision:
            max_component = max(abs(force.fx), abs(force.fy), abs(force.fz))
            if abs(force.fx) == max_component:
                direction = "x" if force.fx > 0 else "-x"
            elif abs(force.fy) == max_component:
                direction = "y" if force.fy > 0 else "-y"
            else:
                direction = "z" if force.fz > 0 else "-z"
        
        collision_result = CollisionResult(
            detected=collision,
            collision_force=force.total_force,
            collision_direction=direction,
            stop_required=collision and force.total_force > threshold * 1.5,
            message="Collision detected" if collision else "No collision"
        )
        
        return {
            "success": True,
            "action": "contact_detect",
            "detected": collision_result.detected,
            "collision_force": collision_result.collision_force,
            "collision_direction": collision_result.collision_direction,
            "stop_required": collision_result.stop_required,
            "message": collision_result.message,
            "force": force.to_dict()
        }
    
    async def _emergency_stop(self) -> Dict[str, Any]:
        """紧急停止"""
        self._emergency_stopped = True
        self._impedance_enabled = False
        
        return {
            "success": True,
            "action": "emergency_stop",
            "message": "Emergency stop activated. Robot halted.",
            "reset_required": True
        }
    
    async def emergency_reset(self) -> Dict[str, Any]:
        """重置紧急停止状态"""
        self._emergency_stopped = False
        
        return {
            "success": True,
            "action": "emergency_reset",
            "message": "Emergency stop reset. Robot ready."
        }
    
    def get_current_force(self) -> ForceData:
        """获取当前力数据"""
        return self._last_force
    
    def set_collision_threshold(self, threshold: float):
        """设置碰撞检测阈值"""
        self._collision_threshold = threshold
    
    def set_impedance_params(self, stiffness: float, damping: float):
        """设置阻抗控制参数"""
        self._current_impedance.stiffness = stiffness
        self._current_impedance.damping = damping


def create_force_control_skill(
    component_name: str = "force_control",
    force_topic: str = "/force_sensor/data",
    simulated: bool = True
) -> ForceControlSkill:
    """
    工厂函数: 创建ForceControlSkill实例
    
    Args:
        component_name: 组件名称
        force_topic: 力传感器话题
        simulated: 是否使用模拟模式
        
    Returns:
        ForceControlSkill实例
    """
    return ForceControlSkill(
        component_name=component_name,
        force_topic=force_topic,
        _simulated=simulated
    )
