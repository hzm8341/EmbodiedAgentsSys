"""
抓取规划Skill

基于工件检测结果，规划最优抓取策略。
包括抓取点计算、夹爪选择、运动路径规划等。
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass


class SkillStatus(Enum):
    """Skill执行状态"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SkillResult:
    """Skill执行结果"""
    
    def __init__(self, status: SkillStatus, output: Any = None, 
                 error: Optional[str] = None, metadata: Dict[str, Any] = None):
        self.status = status
        self.output = output
        self.error = error
        self.metadata = metadata or {}


@dataclass
class GraspPoint:
    """抓取点数据类"""
    position: Dict[str, float]  # {x, y, z}
    orientation: Dict[str, float]  # {roll, pitch, yaw}
    approach_direction: Dict[str, float]  # 接近方向
    gripper_width: float  # 夹爪开合度


class GraspSkill:
    """
    抓取规划Skill
    
    基于视觉检测结果，规划机械臂的抓取策略。
    支持:
    - 抓取点计算
    - 抓取姿态规划
    - 运动路径规划
    - 夹爪参数配置
    """
    
    # 预设夹爪配置
    GRIPPER_CONFIGS = {
        "default": {
            "max_width": 0.1,  # 最大开合度(米)
            "min_width": 0.0,
            "type": "parallel"
        },
        "wide": {
            "max_width": 0.15,
            "min_width": 0.02,
            "type": "wide_angle"
        },
        "precision": {
            "max_width": 0.05,
            "min_width": 0.0,
            "type": "precision"
        }
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化抓取规划Skill
        
        Args:
            config: 配置选项
        """
        self.config = config or {}
        self._status = SkillStatus.IDLE
        self._gripper_type = self.config.get("gripper_type", "default")
        
    @property
    def status(self) -> SkillStatus:
        return self._status
    
    async def execute(self, action: str, **kwargs) -> SkillResult:
        """
       执行抓取规划任务
        
        Args:
            action: 动作类型 (plan_grasp, validate_grasp, optimize_path)
            **kwargs: 动作参数
                - detection: 目标检测结果
                - grasp_point: 候选抓取点
                
        Returns:
            SkillResult: 执行结果
        """
        self._status = SkillStatus.RUNNING
        result = None
        
        try:
            if action == "plan_grasp":
                # 规划抓取策略
                result = await self._plan_grasp(
                    kwargs.get("detection"),
                    kwargs.get("workspace_bounds")
                )
            elif action == "validate_grasp":
                # 验证抓取点可行性
                result = await self._validate_grasp(
                    kwargs.get("grasp_point")
                )
            elif action == "optimize_path":
                # 优化抓取路径
                result = await self._optimize_path(
                    kwargs.get("grasp_point"),
                    kwargs.get("start_position")
                )
            else:
                result = SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Unknown action: {action}"
                )
            
            if result is None:
                result = SkillResult(
                    status=SkillStatus.FAILED,
                    error="Action returned None"
                )
            
            self._status = SkillStatus.SUCCESS
            return result
            
        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(
                status=SkillStatus.FAILED,
                error=str(e)
            )
    
    async def _plan_grasp(self, detection: Dict, workspace_bounds: Dict = None) -> SkillResult:
        """
        规划抓取策略
        
        根据目标检测结果计算最优抓取点。
        """
        if not detection:
            return SkillResult(
                status=SkillStatus.FAILED,
                error="No detection provided"
            )
        
        class_name = detection.get("class_name", "unknown")
        bbox = detection.get("bbox", [0, 0, 100, 100])
        
        # 计算抓取点（基于检测框中心）
        x_center = (bbox[0] + bbox[2]) / 2
        y_center = (bbox[1] + bbox[3]) / 2
        
        # 模拟抓取点计算
        # 实际使用时，会使用GraspNet等模型计算最优抓取位姿
        grasp_points = [
            GraspPoint(
                position={"x": 0.5, "y": 0.0, "z": 0.05},
                orientation={"roll": 0.0, "pitch": 1.57, "yaw": 0.0},
                approach_direction={"x": 0.0, "y": 0.0, "z": -1.0},
                gripper_width=0.05
            ),
            GraspPoint(
                position={"x": 0.5, "y": 0.02, "z": 0.05},
                orientation={"roll": 0.0, "pitch": 1.57, "yaw": 0.1},
                approach_direction={"x": 0.0, "y": 0.0, "z": -1.0},
                gripper_width=0.05
            ),
        ]
        
        # 选择最佳抓取点
        best_grasp = grasp_points[0]
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "grasp_points": [
                    {
                        "position": gp.position,
                        "orientation": gp.orientation,
                        "approach_direction": gp.approach_direction,
                        "gripper_width": gp.gripper_width
                    }
                    for gp in grasp_points
                ],
                "best_grasp": {
                    "position": best_grasp.position,
                    "orientation": best_grasp.orientation,
                    "approach_direction": best_grasp.approach_direction,
                    "gripper_width": best_grasp.gripper_width
                },
                "workpiece_type": class_name
            },
            metadata={
                "action": "plan_grasp",
                "detection_confidence": detection.get("confidence", 0.0),
                "executed": True
            }
        )
    
    async def _validate_grasp(self, grasp_point: Dict) -> SkillResult:
        """
        验证抓取点可行性
        
        检查抓取点是否在工作空间内，是否有碰撞风险等。
        """
        if not grasp_point:
            return SkillResult(
                status=SkillStatus.FAILED,
                error="No grasp point provided"
            )
        
        position = grasp_point.get("position", {})
        x, y, z = position.get("x", 0), position.get("y", 0), position.get("z", 0)
        
        # 工作空间检查
        workspace_valid = (
            -0.5 <= x <= 0.5 and
            -0.5 <= y <= 0.5 and
            0.0 <= z <= 0.5
        )
        
        # 高度检查
        height_valid = z > 0.02  # 确保不在地面上
        
        is_valid = workspace_valid and height_valid
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "valid": is_valid,
                "workspace_ok": workspace_valid,
                "height_ok": height_valid,
                "grasp_point": grasp_point
            },
            metadata={
                "action": "validate_grasp",
                "executed": True
            }
        )
    
    async def _optimize_path(self, grasp_point: Dict, start_position: Dict = None) -> SkillResult:
        """
        优化抓取路径
        
        生成从起点到抓取点的运动路径。
        """
        if not start_position:
            start_position = {"x": 0.0, "y": 0.0, "z": 0.3}
        
        # 生成路径点
        # 实际使用时，会使用MoveIt!或OMPL进行运动规划
        path = [
            {
                "position": start_position,
                "type": "start"
            },
            {
                "position": {
                    "x": grasp_point["position"]["x"],
                    "y": grasp_point["position"]["y"],
                    "z": grasp_point["position"]["z"] + 0.1  # 预抓取位置
                },
                "type": "pre_grasp"
            },
            {
                "position": grasp_point["position"],
                "type": "grasp"
            }
        ]
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "path": path,
                "path_length": len(path),
                "estimated_time": 2.5  # 秒
            },
            metadata={
                "action": "optimize_path",
                "executed": True
            }
        )
    
    async def plan_grasp_for_detection(self, detection: Dict) -> SkillResult:
        """
        便捷方法: 为检测结果规划抓取
        
        Args:
            detection: 目标检测结果
            
        Returns:
            SkillResult: 抓取规划结果
        """
        return await self.execute("plan_grasp", detection=detection)
    
    async def validate_inputs(self, **kwargs) -> bool:
        """验证输入参数"""
        action = kwargs.get("action")
        if not action:
            return False
        valid_actions = ["plan_grasp", "validate_grasp", "optimize_path"]
        return action in valid_actions


def create_grasp_skill(config: Dict = None) -> GraspSkill:
    """工厂函数: 创建GraspSkill实例"""
    return GraspSkill(config=config)
