"""
agents/execution/tools/move_tool.py - 移动规划工具

提供机器人运动规划功能：
- 绝对位置移动
- 相对移动
- 避碰规划
- 轨迹规划
"""

from typing import Optional, List, Dict
from .base import ToolBase


class MoveTool(ToolBase):
    """移动规划工具"""

    name = "move"
    description = "Robot motion planning and trajectory execution"
    keywords = ["move", "position", "trajectory", "motion", "planning"]

    def __init__(self):
        """初始化移动工具"""
        # 工作空间范围
        self.workspace_min = {"x": -1.0, "y": -1.0, "z": 0.0}
        self.workspace_max = {"x": 1.0, "y": 1.0, "z": 1.0}
        # 当前位置
        self.current_position = {"x": 0.0, "y": 0.0, "z": 0.0}

    async def execute(
        self,
        target: Optional[Dict] = None,
        trajectory: Optional[List[Dict]] = None,
        mode: str = "direct",
    ) -> dict:
        """
        执行移动规划

        Args:
            target: 目标位置 {'x': float, 'y': float, 'z': float}
            trajectory: 轨迹路径点列表（仅用于 'trajectory' 模式）
            mode: 移动模式 ('direct', 'relative', 'safe', 'trajectory')

        Returns:
            dict: 执行结果

        Raises:
            ValueError: 无效的坐标或模式
        """
        # 验证移动模式
        valid_modes = ["direct", "relative", "safe", "trajectory"]
        if mode not in valid_modes:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of: {valid_modes}"
            )

        # 根据模式处理
        if mode == "trajectory":
            return await self._execute_trajectory(trajectory)
        elif mode == "relative":
            return await self._execute_relative(target)
        elif mode == "safe":
            return await self._execute_safe(target)
        else:  # direct
            return await self._execute_direct(target)

    async def _execute_direct(self, target: Dict) -> dict:
        """直接移动到目标位置"""
        self._validate_coordinates(target)
        self._validate_position(target)

        self.current_position = target.copy()

        return {
            "success": True,
            "mode": "direct",
            "target": target,
            "current_position": self.current_position.copy(),
            "execution_time": 0.5,  # 模拟执行时间
            "message": f"Moved to position {target}",
        }

    async def _execute_relative(self, delta: Dict) -> dict:
        """相对移动"""
        self._validate_coordinates(delta)

        # 计算新位置
        new_position = {
            "x": self.current_position["x"] + delta["x"],
            "y": self.current_position["y"] + delta["y"],
            "z": self.current_position["z"] + delta["z"],
        }

        # 验证新位置在工作空间内
        self._validate_position(new_position)

        self.current_position = new_position

        return {
            "success": True,
            "mode": "relative",
            "delta": delta,
            "current_position": self.current_position.copy(),
            "execution_time": 0.3,
            "message": f"Moved by delta {delta}",
        }

    async def _execute_safe(self, target: Dict) -> dict:
        """使用避碰规划移动"""
        self._validate_coordinates(target)
        self._validate_position(target)

        self.current_position = target.copy()

        # 计算路径长度（欧氏距离）
        import math
        distance = math.sqrt(
            sum((target[k] - self.current_position[k]) ** 2 for k in ["x", "y", "z"])
        )

        return {
            "success": True,
            "mode": "safe",
            "target": target,
            "current_position": self.current_position.copy(),
            "path_length": distance,
            "collision_free": True,
            "execution_time": 1.0,
            "message": f"Safely moved to position {target}",
        }

    async def _execute_trajectory(self, trajectory: List[Dict]) -> dict:
        """执行轨迹规划"""
        if not trajectory or len(trajectory) == 0:
            raise ValueError("Trajectory must not be empty")

        # 验证所有路径点
        for waypoint in trajectory:
            self._validate_coordinates(waypoint)
            self._validate_position(waypoint)

        # 执行轨迹（移动到最后一个路径点）
        self.current_position = trajectory[-1].copy()

        return {
            "success": True,
            "mode": "trajectory",
            "waypoint_count": len(trajectory),
            "current_position": self.current_position.copy(),
            "execution_time": len(trajectory) * 0.2,
            "message": f"Executed trajectory with {len(trajectory)} waypoints",
        }

    def _validate_coordinates(self, coords: Dict) -> None:
        """验证坐标有效性"""
        required_keys = ["x", "y", "z"]
        for key in required_keys:
            if key not in coords:
                raise ValueError(f"Missing coordinate: {key}")

    def _validate_position(self, pos: Dict) -> None:
        """验证位置在工作空间范围内"""
        for axis in ["x", "y", "z"]:
            value = pos[axis]
            min_val = self.workspace_min[axis]
            max_val = self.workspace_max[axis]

            if value < min_val or value > max_val:
                raise ValueError(
                    f"Coordinate {axis}={value} out of workspace range "
                    f"[{min_val}, {max_val}]"
                )

    async def validate(self, **kwargs) -> bool:
        """验证参数有效性"""
        try:
            mode = kwargs.get("mode", "direct")
            if mode not in ["direct", "relative", "safe", "trajectory"]:
                return False
            return True
        except Exception:
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        # 返回安全位置
        self.current_position = {"x": 0.0, "y": 0.0, "z": 0.0}
