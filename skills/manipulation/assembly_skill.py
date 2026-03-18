"""
AssemblySkill - 装配规划Skill
===========================

该模块负责装配任务的规划和执行，支持柔性装配场景。

功能:
- 装配序列规划: 确定零件装配顺序
- 配合关系识别: 识别零件间的配合关系
- 路径规划: 生成安全的装配路径
- 位置/姿态调整: 精确对齐零件位置和姿态

使用示例:
    from skills.manipulation.assembly_skill import AssemblySkill

    skill = AssemblySkill()

    # 规划装配序列
    result = await skill.execute(
        action="plan_sequence",
        parts=["零件A", "零件B"]
    )

    # 执行装配
    result = await skill.execute(
        action="assemble",
        part_a="零件A",
        part_b="零件B"
    )
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

# Import ForceController for assembly force control
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent / "force_control"))
from force_control import ForceController, ForceControlMode


class AssemblyAction(Enum):
    """装配动作类型"""

    PLAN_SEQUENCE = "plan_sequence"  # 规划装配序列
    RECOGNIZE_FIT = "recognize_fit"  # 识别配合关系
    PLAN_PATH = "plan_path"  # 规划装配路径
    ALIGN_PARTS = "align_parts"  # 对齐零件
    ASSEMBLE = "assemble"  # 执行装配
    VERIFY_ASSEMBLY = "verify_assembly"  # 验证装配结果


@dataclass
class AssemblyPart:
    """装配零件"""

    name: str
    part_id: str
    # 几何信息
    dimensions: List[float]  # [长, 宽, 高]
    geometry_type: str  # box, cylinder, sphere, complex
    # 配合特征
    features: List[Dict[str, Any]]  # 孔、轴、槽等
    # 当前位置
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # 目标位置
    target_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    target_orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class FitRelation:
    """配合关系"""

    part_a: str  # 零件A名称
    part_b: str  # 零件B名称
    fit_type: str  # 配合类型: press, clearance, interference
    tolerance: float = 0.0  # 公差 (m)
    features_a: List[str] = field(default_factory=list)  # 零件A的特征
    features_b: List[str] = field(default_factory=list)  # 零件B的特征


@dataclass
class AssemblySequence:
    """装配序列"""

    sequence_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_time: float = 0.0
    difficulty: str = "medium"  # easy, medium, hard

    def to_chain_format(self) -> List[Dict[str, Any]]:
        """转换为SkillChain格式"""
        return self.steps


@dataclass
class AssemblyPath:
    """装配路径"""

    path_points: List[List[float]] = field(default_factory=list)  # 路径点序列
    path_type: str = "linear"  # linear, curve, hybrid
    clearance_height: float = 0.05  # 安全高度 (m)
    approach_height: float = 0.01  # 接近距离 (m)

    def get_execution_params(self) -> Dict[str, Any]:
        """获取执行参数"""
        return {
            "path_points": self.path_points,
            "path_type": self.path_type,
            "clearance_height": self.clearance_height,
            "approach_height": self.approach_height,
        }


class AssemblySkill:
    """
    装配规划Skill - 提供装配任务的规划和执行能力

    支持的能力:
    1. 装配序列规划
    2. 配合关系识别
    3. 装配路径规划
    4. 零件对齐与装配
    5. 装配结果验证

    注意: 这是逻辑实现，ROS集成部分可在环境准备好后添加。
    """

    # 预定义的配合关系
    PREDEFINED_FITS = {
        ("轴", "孔"): "clearance",
        ("螺栓", "螺母"): "threaded",
        ("销", "销孔"): "press",
        ("齿轮", "轴"): "keyed",
    }

    def __init__(
        self,
        component_name: str = "assembly",
        _simulated: bool = True,
        force_controller: Optional[ForceController] = None,
    ):
        """
        初始化装配规划模块

        Args:
            component_name: 组件名称
            _simulated: 是否使用模拟模式
            force_controller: 力控制器实例
        """
        self.name = component_name
        self._simulated = _simulated
        self._initialized = False
        self.force_controller = force_controller

        # 模拟的零件库
        self._parts_library = {
            "零件A": AssemblyPart(
                name="零件A",
                part_id="PART_001",
                dimensions=[0.05, 0.03, 0.02],
                geometry_type="box",
                features=[{"type": "hole", "diameter": 0.01, "depth": 0.02}],
                position=[0.3, 0.1, 0.05],
            ),
            "零件B": AssemblyPart(
                name="零件B",
                part_id="PART_002",
                dimensions=[0.04, 0.04, 0.03],
                geometry_type="box",
                features=[{"type": "shaft", "diameter": 0.01, "length": 0.03}],
                position=[0.35, -0.1, 0.05],
            ),
            "螺母M6": AssemblyPart(
                name="螺母M6",
                part_id="PART_003",
                dimensions=[0.01, 0.01, 0.005],
                geometry_type="cylinder",
                features=[{"type": "thread", "diameter": 0.006}],
                position=[0.4, 0.0, 0.05],
            ),
            "螺栓M6": AssemblyPart(
                name="螺栓M6",
                part_id="PART_004",
                dimensions=[0.03, 0.006, 0.006],
                geometry_type="cylinder",
                features=[{"type": "thread", "diameter": 0.006}],
                position=[0.4, 0.05, 0.05],
            ),
        }

    async def initialize(self) -> bool:
        """初始化装配模块"""
        if self._simulated:
            self._initialized = True
            return True

        # TODO: ROS初始化
        return True

    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """
        执行装配动作

        Args:
            action: 动作类型 (见 AssemblyAction)
            **params: 动作参数

        Returns:
            执行结果字典
        """
        if not self._initialized:
            await self.initialize()

        action_enum = self._str_to_action(action)

        try:
            if action_enum == AssemblyAction.PLAN_SEQUENCE:
                return await self._plan_sequence(**params)
            elif action_enum == AssemblyAction.RECOGNIZE_FIT:
                return await self._recognize_fit(**params)
            elif action_enum == AssemblyAction.PLAN_PATH:
                return await self._plan_path(**params)
            elif action_enum == AssemblyAction.ALIGN_PARTS:
                return await self._align_parts(**params)
            elif action_enum == AssemblyAction.ASSEMBLE:
                return await self._assemble(**params)
            elif action_enum == AssemblyAction.VERIFY_ASSEMBLY:
                return await self._verify_assembly(**params)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _str_to_action(self, action: str) -> AssemblyAction:
        """字符串转换为动作枚举"""
        action_map = {
            "plan_sequence": AssemblyAction.PLAN_SEQUENCE,
            "sequence": AssemblyAction.PLAN_SEQUENCE,
            "recognize_fit": AssemblyAction.RECOGNIZE_FIT,
            "fit": AssemblyAction.RECOGNIZE_FIT,
            "plan_path": AssemblyAction.PLAN_PATH,
            "path": AssemblyAction.PLAN_PATH,
            "align_parts": AssemblyAction.ALIGN_PARTS,
            "align": AssemblyAction.ALIGN_PARTS,
            "assemble": AssemblyAction.ASSEMBLE,
            "assembly": AssemblyAction.ASSEMBLE,
            "verify_assembly": AssemblyAction.VERIFY_ASSEMBLY,
            "verify": AssemblyAction.VERIFY_ASSEMBLY,
        }

        return action_map.get(action.lower(), AssemblyAction.PLAN_SEQUENCE)

    async def _plan_sequence(self, parts: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        规划装配序列

        Args:
            parts: 要装配的零件列表

        Returns:
            装配序列
        """
        if self._simulated:
            # 使用预定义的简单序列
            if parts is None:
                parts = ["零件A", "零件B"]

            # 简单的基于数量的序列规划
            sequence = []
            for i, part in enumerate(parts):
                # 先拾取零件
                sequence.append({
                    "step_id": i * 2 + 1,
                    "action": "pick",
                    "part": part,
                    "skill": "grasp",
                    "description": f"抓取{part}",
                })

                # 然后移动到装配位置
                sequence.append({
                    "step_id": i * 2 + 2,
                    "action": "move",
                    "part": part,
                    "skill": "motion",
                    "description": f"移动{part}到装配位置",
                })

            assembly_seq = AssemblySequence(
                sequence_id=f"seq_{len(parts)}",
                steps=sequence,
                estimated_time=len(sequence) * 3.0,
                difficulty="medium",
            )

            return {
                "success": True,
                "action": "plan_sequence",
                "sequence": assembly_seq.steps,
                "sequence_id": assembly_seq.sequence_id,
                "estimated_time": assembly_seq.estimated_time,
                "difficulty": assembly_seq.difficulty,
            }
        else:
            # TODO: ROS实现
            pass

    async def _recognize_fit(
        self, part_a: str = None, part_b: str = None, **kwargs
    ) -> Dict[str, Any]:
        """
        识别配合关系

        Args:
            part_a: 零件A名称
            part_b: 零件B名称

        Returns:
            配合关系
        """
        if self._simulated:
            # 如果没有指定零件，返回所有可能的配合
            if part_a is None or part_b is None:
                fits = [
                    {
                        "part_a": "螺栓M6",
                        "part_b": "螺母M6",
                        "fit_type": "threaded",
                        "tolerance": 0.0001,
                        "features_a": ["thread"],
                        "features_b": ["thread"],
                    },
                    {
                        "part_a": "零件A",
                        "part_b": "零件B",
                        "fit_type": "press",
                        "tolerance": 0.0002,
                        "features_a": ["hole"],
                        "features_b": ["shaft"],
                    },
                ]
                return {
                    "success": True,
                    "action": "recognize_fit",
                    "fits": fits,
                    "count": len(fits),
                }

            # 识别特定零件的配合
            fit_type = "unknown"
            tolerance = 0.0

            # 简单的配合识别逻辑
            for (feat_a, feat_b), ftype in self.PREDEFINED_FITS.items():
                if part_a in self._parts_library and part_b in self._parts_library:
                    pa = self._parts_library[part_a]
                    pb = self._parts_library[part_b]

                    # 检查特征
                    for f in pa.features:
                        if feat_a in f.get("type", ""):
                            for bf in pb.features:
                                if feat_b in bf.get("type", ""):
                                    fit_type = ftype
                                    tolerance = 0.0001
                                    break

            return {
                "success": True,
                "action": "recognize_fit",
                "part_a": part_a,
                "part_b": part_b,
                "fit_type": fit_type,
                "tolerance": tolerance,
            }
        else:
            # TODO: ROS实现
            pass

    async def _plan_path(
        self, part_name: str = None, target_position: List[float] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        规划装配路径

        Args:
            part_name: 零件名称
            target_position: 目标位置

        Returns:
            装配路径
        """
        if self._simulated:
            # 获取零件信息
            if part_name and part_name in self._parts_library:
                part = self._parts_library[part_name]
                start_pos = part.position
            else:
                start_pos = [0.3, 0.0, 0.1]

            if target_position is None:
                target_position = [0.3, 0.0, 0.0]

            # 生成路径点
            clearance_height = 0.05
            approach_height = 0.01

            # 路径: 当前位置 -> 抬升 -> 平移 -> 下降 -> 目标位置
            path_points = [
                start_pos,  # 当前位置
                [start_pos[0], start_pos[1], clearance_height],  # 抬升
                [
                    target_position[0],
                    target_position[1],
                    clearance_height,
                ],  # 平移到目标上方
                [
                    target_position[0],
                    target_position[1],
                    target_position[2] + approach_height,
                ],  # 下降到接近位置
                target_position,  # 目标位置
            ]

            assembly_path = AssemblyPath(
                path_points=path_points,
                path_type="linear",
                clearance_height=clearance_height,
                approach_height=approach_height,
            )

            return {
                "success": True,
                "action": "plan_path",
                "path": assembly_path.get_execution_params(),
                "path_length": len(path_points),
                "estimated_time": 3.0,
            }
        else:
            # TODO: ROS实现
            pass

    async def _align_parts(
        self, part_a: str, part_b: str, alignment_type: str = "position", **kwargs
    ) -> Dict[str, Any]:
        """
        对齐零件

        Args:
            part_a: 零件A名称
            part_b: 零件B名称
            alignment_type: 对齐类型 (position, orientation, both)

        Returns:
            对齐参数
        """
        if self._simulated:
            # 获取零件信息
            pa = self._parts_library.get(
                part_a,
                AssemblyPart(name=part_a, part_id="", dimensions=[0.1, 0.1, 0.1]),
            )
            pb = self._parts_library.get(
                part_b,
                AssemblyPart(name=part_b, part_id="", dimensions=[0.1, 0.1, 0.1]),
            )

            # 计算对齐参数
            alignment = {
                "part_a": part_a,
                "part_b": part_b,
                "alignment_type": alignment_type,
                "offset": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "alignment_accuracy": 0.001,  # 1mm精度
            }

            return {
                "success": True,
                "action": "align_parts",
                "alignment": alignment,
                "status": "aligned",
            }
        else:
            # TODO: ROS实现
            pass

    async def _assemble(
        self, part_a: str, part_b: str, fit_type: str = "press", **kwargs
    ) -> Dict[str, Any]:
        """
        执行装配

        Args:
            part_a: 零件A名称
            part_b: 零件B名称
            fit_type: 配合类型

        Returns:
            装配结果
        """
        if self._simulated:
            # 模拟装配过程
            await asyncio.sleep(0.1)

            # 根据配合类型调整
            if fit_type == "press":
                # 过盈配合: 需要较大的力
                force = 10.0
                speed = 0.005
            elif fit_type == "clearance":
                # 间隙配合: 轻松插入
                force = 1.0
                speed = 0.01
            elif fit_type == "threaded":
                # 螺纹配合: 旋转插入
                force = 2.0
                speed = 0.02
            else:
                force = 5.0
                speed = 0.008

            return {
                "success": True,
                "action": "assemble",
                "part_a": part_a,
                "part_b": part_b,
                "fit_type": fit_type,
                "applied_force": force,
                "insertion_speed": speed,
                "status": "completed",
                "final_position": [0.3, 0.0, 0.0],
            }
        else:
            # TODO: ROS实现
            pass

    async def _verify_assembly(
        self, assembly_name: str = None, **kwargs
    ) -> Dict[str, Any]:
        """
        验证装配结果

        Args:
            assembly_name: 装配体名称

        Returns:
            验证结果
        """
        if self._simulated:
            # 模拟验证
            return {
                "success": True,
                "action": "verify_assembly",
                "assembly_name": assembly_name,
                "verified": True,
                "quality": "good",
                "tolerance_check": {
                    "position": {"required": 0.001, "actual": 0.0005, "passed": True},
                    "orientation": {"required": 0.01, "actual": 0.005, "passed": True},
                },
                "notes": "Assembly completed successfully",
            }

    async def execute_insertion(
        self,
        target_pose: List[float],
        max_insertion_force: float = 5.0,
        max_steps: int = 100,
    ) -> Dict[str, Any]:
        """
        使用力控制执行精确插入

        Args:
            target_pose: 目标位姿 [x, y, z, roll, pitch, yaw]
            max_insertion_force: 最大插入力 (N)
            max_steps: 最大步数

        Returns:
            插入结果
        """
        if self.force_controller is None:
            return {
                "success": False,
                "error": "No force controller available",
            }

        self.force_controller.set_mode(ForceControlMode.HYBRID)
        self.force_controller.max_force = max_insertion_force

        for step in range(max_steps):
            current_force = self.force_controller.get_current_force()

            if self.force_controller.detect_contact(current_force):
                return {
                    "success": True,
                    "status": "contact_detected",
                    "step": step,
                    "force": current_force.tolist(),
                    "mode": self.force_controller.mode.value,
                }

            target_force = np.array([0, 0, -max_insertion_force, 0, 0, 0])
            result = await self.force_controller.execute(target_force)

            if result.get("status") == "contact":
                return {
                    "success": True,
                    "status": "contact",
                    "step": step,
                    "force": current_force.tolist(),
                    "displacement": result.get("displacement", []),
                }

            await asyncio.sleep(0.02)

        return {
            "success": True,
            "status": "completed",
            "steps": max_steps,
            "final_force": self.force_controller.get_current_force().tolist(),
        }

    def add_part_to_library(self, part: AssemblyPart):
        """添加零件到库"""
        self._parts_library[part.name] = part

    def get_part_info(self, part_name: str) -> Optional[AssemblyPart]:
        """获取零件信息"""
        return self._parts_library.get(part_name)


def create_assembly_skill(
    component_name: str = "assembly",
    simulated: bool = True,
    force_controller: Optional[ForceController] = None,
) -> AssemblySkill:
    """
    工厂函数: 创建AssemblySkill实例

    Args:
        component_name: 组件名称
        simulated: 是否使用模拟模式
        force_controller: 力控制器实例

    Returns:
        AssemblySkill实例
    """
    return AssemblySkill(
        component_name=component_name,
        _simulated=simulated,
        force_controller=force_controller,
    )
