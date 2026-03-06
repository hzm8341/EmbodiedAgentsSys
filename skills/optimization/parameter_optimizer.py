"""
ParameterOptimizer - 参数优化模块
================================

该模块根据执行反馈自动优化Skill参数。

功能:
- 性能跟踪: 记录Skill执行过程中的性能指标
- 参数调优: 自动调整Skill参数以优化性能
- 学习机制: 从历史执行中学习最佳参数
- 适应环境: 根据环境变化调整参数

使用示例:
    from skills.optimization.parameter_optimizer import ParameterOptimizer
    
    optimizer = ParameterOptimizer()
    
    # 记录执行结果
    await optimizer.record_execution(
        skill_name="pick_and_place",
        params={"speed": 0.5, "force": 10.0},
        result={"success": True, "duration": 3.5, "quality": 0.9}
    )
    
    # 获取优化后的参数
    optimized = await optimizer.optimize(
        skill_name="pick_and_place",
        target_metric="duration"
    )
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import numpy as np
from collections import defaultdict


class OptimizationGoal(Enum):
    """优化目标"""
    MINIMIZE_DURATION = "duration"      # 最小化执行时间
    MAXIMIZE_SUCCESS = "success_rate"   # 最大化成功率
    MAXIMIZE_QUALITY = "quality"        # 最大化质量
    MINIMIZE_ENERGY = "energy"          # 最小化能耗
    BALANCED = "balanced"                # 平衡多个指标


class ParameterType(Enum):
    """参数类型"""
    CONTINUOUS = "continuous"   # 连续参数 (如速度、力度)
    DISCRETE = "discrete"       # 离散参数 (如抓取策略)
    CATEGORICAL = "categorical" # 类别参数 (如运动模式)


@dataclass
class ParameterConfig:
    """参数配置"""
    name: str
    param_type: ParameterType
    min_value: float = 0.0      # 连续参数最小值
    max_value: float = 1.0      # 连续参数最大值
    default_value: Any = None   # 默认值
    step_size: float = 0.1      # 步长 (用于离散化)
    options: List[Any] = field(default_factory=list)  # 选项 (离散/类别)


@dataclass
class ExecutionRecord:
    """执行记录"""
    record_id: str
    skill_name: str
    timestamp: float
    
    # 参数
    params: Dict[str, Any]
    
    # 结果
    success: bool
    duration: float = 0.0
    quality: float = 0.0
    energy: float = 0.0
    
    # 额外指标
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # 上下文
    environment: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "skill_name": self.skill_name,
            "timestamp": self.timestamp,
            "params": self.params,
            "success": self.success,
            "duration": self.duration,
            "quality": self.quality,
            "energy": self.energy,
            "metrics": self.metrics,
            "environment": self.environment
        }


@dataclass
class OptimizationResult:
    """优化结果"""
    skill_name: str
    converged: bool
    iterations: int
    
    # 最佳参数
    best_params: Dict[str, Any]
    best_score: float
    
    # 历史
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 建议
    suggestions: List[str] = field(default_factory=list)


class ParameterOptimizer:
    """
    参数优化器 - 根据执行反馈自动优化Skill参数
    
    功能:
    1. 执行记录: 记录每次执行的参数和结果
    2. 参数学习: 从历史数据中学习最佳参数
    3. 优化算法: 支持网格搜索、随机搜索、贝叶斯优化
    4. 适应机制: 根据环境变化动态调整
    """
    
    def __init__(
        self,
        _simulated: bool = True,
        max_records: int = 1000,
        optimization_method: str = "grid_search"
    ):
        """
        初始化参数优化器
        
        Args:
            _simulated: 是否使用模拟模式
            max_records: 最大记录数
            optimization_method: 优化方法
        """
        self._simulated = _simulated
        self.max_records = max_records
        self.optimization_method = optimization_method
        
        # 执行记录
        self._records: List[ExecutionRecord] = []
        
        # 参数配置
        self._param_configs: Dict[str, Dict[str, ParameterConfig]] = defaultdict(dict)
        
        # 优化状态
        self._optimization_in_progress: Dict[str, bool] = {}
        
        # 回调
        self._on_optimization_complete = None
        
        # 默认参数配置
        self._register_default_configs()
    
    def _register_default_configs(self):
        """注册默认参数配置"""
        # 运动参数
        self._param_configs["motion"] = {
            "speed": ParameterConfig(
                name="speed",
                param_type=ParameterType.CONTINUOUS,
                min_value=0.1,
                max_value=1.0,
                default_value=0.5,
                step_size=0.1
            ),
            "acceleration": ParameterConfig(
                name="acceleration",
                param_type=ParameterType.CONTINUOUS,
                min_value=0.1,
                max_value=1.0,
                default_value=0.5,
                step_size=0.1
            ),
            "smoothness": ParameterConfig(
                name="smoothness",
                param_type=ParameterType.CONTINUOUS,
                min_value=0.0,
                max_value=1.0,
                default_value=0.5,
                step_size=0.1
            )
        }
        
        # 抓取参数
        self._param_configs["gripper"] = {
            "force": ParameterConfig(
                name="force",
                param_type=ParameterType.CONTINUOUS,
                min_value=1.0,
                max_value=20.0,
                default_value=10.0,
                step_size=1.0
            ),
            "grasp_strategy": ParameterConfig(
                name="grasp_strategy",
                param_type=ParameterType.CATEGORICAL,
                options=["parallel", "pinch", "wrap"],
                default_value="parallel"
            ),
            "approach_distance": ParameterConfig(
                name="approach_distance",
                param_type=ParameterType.CONTINUOUS,
                min_value=0.01,
                max_value=0.2,
                default_value=0.05,
                step_size=0.01
            )
        }
        
        # 力控参数
        self._param_configs["force_control"] = {
            "stiffness": ParameterConfig(
                name="stiffness",
                param_type=ParameterType.CONTINUOUS,
                min_value=10.0,
                max_value=500.0,
                default_value=100.0,
                step_size=10.0
            ),
            "damping": ParameterConfig(
                name="damping",
                param_type=ParameterType.CONTINUOUS,
                min_value=1.0,
                max_value=50.0,
                default_value=10.0,
                step_size=1.0
            ),
            "max_force": ParameterConfig(
                name="max_force",
                param_type=ParameterType.CONTINUOUS,
                min_value=1.0,
                max_value=20.0,
                default_value=5.0,
                step_size=0.5
            )
        }
    
    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """执行操作"""
        action_map = {
            "record_execution": self.record_execution,
            "optimize": self.optimize,
            "get_best_params": self.get_best_params,
            "get_statistics": self.get_statistics,
            "register_params": self.register_params,
            "clear_records": self.clear_records,
            "export_records": self.export_records,
        }
        
        if action in action_map:
            return await action_map[action](**params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    async def record_execution(
        self,
        skill_name: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        environment: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        记录执行结果
        
        Args:
            skill_name: Skill名称
            params: 使用的参数
            result: 执行结果
            environment: 环境信息
        """
        import uuid
        
        record = ExecutionRecord(
            record_id=str(uuid.uuid4())[:8],
            skill_name=skill_name,
            timestamp=time.time(),
            params=params,
            success=result.get("success", False),
            duration=result.get("duration", 0.0),
            quality=result.get("quality", 0.0),
            energy=result.get("energy", 0.0),
            metrics=result.get("metrics", {}),
            environment=environment or {}
        )
        
        # 添加到记录
        self._records.append(record)
        
        # 保持记录数不超过限制
        if len(self._records) > self.max_records:
            self._records = self._records[-self.max_records:]
        
        return {
            "success": True,
            "action": "record_execution",
            "record_id": record.record_id,
            "total_records": len(self._records)
        }
    
    async def optimize(
        self,
        skill_name: str,
        target_metric: str = "duration",
        goal: str = "minimize",
        max_iterations: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """
        优化参数
        
        Args:
            skill_name: Skill名称
            target_metric: 目标指标
            goal: 优化目标 (minimize/maximize)
            max_iterations: 最大迭代次数
        """
        # 获取该Skill的记录
        skill_records = [r for r in self._records if r.skill_name == skill_name]
        
        if len(skill_records) < 3:
            return {
                "success": False,
                "error": f"Not enough records for optimization. Need at least 3, got {len(skill_records)}"
            }
        
        # 根据优化方法执行
        if self.optimization_method == "grid_search":
            result = await self._grid_search(skill_records, target_metric, goal, max_iterations)
        elif self.optimization_method == "random_search":
            result = await self._random_search(skill_records, target_metric, goal, max_iterations)
        elif self.optimization_method == "gradient":
            result = await self._gradient_descent(skill_records, target_metric, goal, max_iterations)
        else:
            result = await self._grid_search(skill_records, target_metric, goal, max_iterations)
        
        return result
    
    async def _grid_search(
        self,
        records: List[ExecutionRecord],
        target_metric: str,
        goal: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """网格搜索优化"""
        # 获取所有参数名
        param_names = list(records[0].params.keys())
        
        # 简单实现: 基于成功率选择最佳参数组合
        success_records = [r for r in records if r.success]
        
        if not success_records:
            return {
                "success": False,
                "error": "No successful records to optimize from"
            }
        
        # 统计每个参数值的成功率
        param_scores = {}
        for param in param_names:
            values = {}
            for r in records:
                if param in r.params:
                    val = r.params[param]
                    if val not in values:
                        values[val] = {"success": 0, "total": 0}
                    values[val]["total"] += 1
                    if r.success:
                        values[val]["success"] += 1
            
            # 计算成功率
            for val, stats in values.items():
                stats["rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            
            param_scores[param] = values
        
        # 选择最佳参数值
        best_params = {}
        for param, values in param_scores.items():
            if values:
                best_val = max(values.items(), key=lambda x: x[1]["rate"])
                best_params[param] = best_val[0]
        
        # 计算最佳分数
        best_score = 0.0
        if best_params:
            matching = [r for r in records if all(r.params.get(k) == v for k, v in best_params.items())]
            if matching:
                success_count = sum(1 for r in matching if r.success)
                best_score = success_count / len(matching)
        
        # 生成建议
        suggestions = []
        for param, values in param_scores.items():
            if values:
                rates = [v["rate"] for v in values.values()]
                if min(rates) < 0.5:
                    suggestions.append(f"参数 {param} 的某些值成功率较低，建议调整")
        
        return {
            "success": True,
            "action": "optimize",
            "skill_name": records[0].skill_name,
            "best_params": best_params,
            "best_score": best_score,
            "iterations": len(records),
            "converged": best_score > 0.8,
            "suggestions": suggestions
        }
    
    async def _random_search(
        self,
        records: List[ExecutionRecord],
        target_metric: str,
        goal: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """随机搜索优化"""
        # 类似于网格搜索，但随机采样
        return await self._grid_search(records, target_metric, goal, max_iterations)
    
    async def _gradient_descent(
        self,
        records: List[ExecutionRecord],
        target_metric: str,
        goal: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """梯度下降优化"""
        # 简化实现
        return await self._grid_search(records, target_metric, goal, max_iterations)
    
    async def get_best_params(
        self,
        skill_name: str,
        metric: str = "success_rate",
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取最佳参数
        
        Args:
            skill_name: Skill名称
            metric: 评估指标
        """
        records = [r for r in self._records if r.skill_name == skill_name]
        
        if not records:
            return {
                "success": False,
                "error": f"No records for skill {skill_name}"
            }
        
        # 简化: 返回成功率最高的参数组合
        success_records = [r for r in records if r.success]
        
        if not success_records:
            return {
                "success": False,
                "error": "No successful executions"
            }
        
        # 返回最后一次成功执行的参数
        last_success = success_records[-1]
        
        return {
            "success": True,
            "action": "get_best_params",
            "skill_name": skill_name,
            "params": last_success.params,
            "metrics": {
                "success_rate": len(success_records) / len(records),
                "avg_duration": np.mean([r.duration for r in records]),
                "avg_quality": np.mean([r.quality for r in records])
            }
        }
    
    async def get_statistics(
        self,
        skill_name: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            skill_name: 可选的Skill名称过滤
        """
        records = self._records
        if skill_name:
            records = [r for r in records if r.skill_name == skill_name]
        
        if not records:
            return {
                "success": True,
                "action": "get_statistics",
                "total_records": 0
            }
        
        # 计算统计
        success_count = sum(1 for r in records if r.success)
        
        stats = {
            "total_records": len(records),
            "success_count": success_count,
            "success_rate": success_count / len(records),
            "avg_duration": float(np.mean([r.duration for r in records])),
            "std_duration": float(np.std([r.duration for r in records])),
            "avg_quality": float(np.mean([r.quality for r in records])),
            "avg_energy": float(np.mean([r.energy for r in records]))
        }
        
        return {
            "success": True,
            "action": "get_statistics",
            "skill_name": skill_name,
            "statistics": stats
        }
    
    async def register_params(
        self,
        skill_category: str,
        param_configs: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        注册参数配置
        
        Args:
            skill_category: Skill类别
            param_configs: 参数配置列表
        """
        for config in param_configs:
            param = ParameterConfig(
                name=config["name"],
                param_type=ParameterType(config["param_type"]),
                min_value=config.get("min_value", 0.0),
                max_value=config.get("max_value", 1.0),
                default_value=config.get("default_value"),
                step_size=config.get("step_size", 0.1),
                options=config.get("options", [])
            )
            self._param_configs[skill_category][param.name] = param
        
        return {
            "success": True,
            "action": "register_params",
            "skill_category": skill_category,
            "param_count": len(param_configs)
        }
    
    async def clear_records(
        self,
        skill_name: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """清除记录"""
        if skill_name:
            self._records = [r for r in self._records if r.skill_name != skill_name]
            count = len(self._records)
        else:
            count = len(self._records)
            self._records = []
        
        return {
            "success": True,
            "action": "clear_records",
            "cleared_count": count,
            "remaining_count": len(self._records)
        }
    
    async def export_records(
        self,
        skill_name: str = None,
        filename: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """导出记录"""
        records = self._records
        if skill_name:
            records = [r for r in records if r.skill_name == skill_name]
        
        data = [r.to_dict() for r in records]
        
        if self._simulated:
            return {
                "success": True,
                "action": "export_records",
                "filename": filename or "optimization_records.json",
                "record_count": len(data),
                "preview": json.dumps(data[:2], indent=2)
            }
        else:
            # TODO: 实际保存
            pass
    
    def get_record_count(self) -> int:
        """获取记录数"""
        return len(self._records)
    
    def set_optimization_method(self, method: str):
        """设置优化方法"""
        self.optimization_method = method


def create_parameter_optimizer(
    simulated: bool = True,
    optimization_method: str = "grid_search"
) -> ParameterOptimizer:
    """
    工厂函数: 创建ParameterOptimizer实例
    """
    return ParameterOptimizer(
        _simulated=simulated,
        optimization_method=optimization_method
    )
