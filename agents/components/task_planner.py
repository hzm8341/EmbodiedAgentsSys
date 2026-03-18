"""
TaskPlanner组件 - 任务规划Agent
====================

该组件负责将高层任务指令拆解为可执行的Skill序列。
支持基于LLM的智能任务分解，与现有Skill系统无缝集成。

功能:
- 任务分解: 将复杂任务拆解为Skill调用序列
- 上下文感知: 理解机器人当前状态和环境
- 规划优化: 生成高效的执行计划
- 适应性调整: 根据执行反馈动态调整计划

使用示例:
    from agents.components.task_planner import TaskPlanner, TaskPlan, ExecutionContext

    planner = TaskPlanner()

    # 创建执行上下文
    context = ExecutionContext(
        robot_state={"gripper": "open", "position": "home"},
        available_skills=["motion", "gripper", "perception", "grasp"]
    )

    # 规划任务
    plan = await planner.plan("把料框里的零件A放到拍照位置", context)

    # 执行计划
    for step in plan.steps:
        result = await execute_skill(step.skill_name, step.params)
"""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable, Awaitable
from collections import deque
import json
import re


class TaskType(Enum):
    """任务类型枚举"""

    PICK_AND_PLACE = "pick_and_place"  # 抓取放置
    ASSEMBLY = "assembly"  # 装配
    INSPECTION = "inspection"  # 检测
    MATERIAL_HANDLING = "material_handling"  # 物料搬运
    FLEXIBLE_ASSEMBLY = "flexible_assembly"  # 柔性装配
    TEACHING = "teaching"  # 示教
    UNKNOWN = "unknown"


class TaskStatus(Enum):
    """任务执行状态"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    PAUSED = "paused"  # 暂停
    CANCELLED = "cancelled"  # 取消


@dataclass
class TaskStep:
    """单个任务步骤"""

    step_id: str
    skill_name: str  # 调用的Skill名称
    params: dict = field(default_factory=dict)  # Skill参数
    description: str = ""  # 步骤描述
    dependencies: list[str] = field(default_factory=list)  # 依赖步骤ID
    estimated_duration: float = 0.0  # 预计执行时间(秒)
    retry_on_failure: bool = True  # 失败时是否重试
    max_retries: int = 3  # 最大重试次数

    def __repr__(self):
        return f"TaskStep({self.step_id}: {self.skill_name})"


@dataclass
class TaskPlan:
    """任务执行计划"""

    plan_id: str
    original_task: str  # 原始任务描述
    task_type: TaskType = TaskType.UNKNOWN
    steps: list[TaskStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    estimated_duration: float = 0.0  # 总预计时间
    context_requirements: dict = field(default_factory=dict)  # 上下文需求
    fallback_plans: list["TaskPlan"] = field(default_factory=list)  # 备用计划

    def get_executable_steps(self) -> list[TaskStep]:
        """获取可执行的步骤（按依赖顺序）"""
        executed = set()
        executable = []

        while len(executed) < len(self.steps):
            for step in self.steps:
                if step.step_id in executed:
                    continue

                # 检查依赖是否满足
                deps_satisfied = all(dep in executed for dep in step.dependencies)

                if deps_satisfied:
                    executable.append(step)
                    executed.add(step.step_id)

        return executable

    def to_chain_format(self) -> list[dict]:
        """转换为SkillChain格式"""
        return [
            {
                "skill_name": step.skill_name,
                "params": step.params,
                "description": step.description,
            }
            for step in self.steps
        ]


@dataclass
class ExecutionContext:
    """执行上下文 - 描述机器人当前状态和环境"""

    robot_state: dict = field(default_factory=dict)  # 机器人状态
    environment: dict = field(default_factory=dict)  # 环境信息
    available_skills: list[str] = field(default_factory=list)  # 可用Skills
    objects_in_scene: list[dict] = field(default_factory=list)  # 场景中物体
    safety_constraints: list[str] = field(default_factory=list)  # 安全约束

    def to_prompt_context(self) -> str:
        """转换为提示词上下文"""
        ctx = []
        ctx.append(f"Robot State: {json.dumps(self.robot_state, ensure_ascii=False)}")
        ctx.append(f"Available Skills: {', '.join(self.available_skills)}")

        if self.objects_in_scene:
            objects_str = ", ".join([
                f"{o.get('name', 'unknown')} at {o.get('position', 'unknown')}"
                for o in self.objects_in_scene
            ])
            ctx.append(f"Objects in scene: {objects_str}")

        if self.safety_constraints:
            ctx.append(f"Safety constraints: {', '.join(self.safety_constraints)}")

        return "\n".join(ctx)


@dataclass
class ExecutionResult:
    """步骤执行结果"""

    step_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    retries: int = 0


# ============================================================
# Skill执行器接口
# ============================================================

SkillExecutor = Callable[[str, dict], Awaitable[ExecutionResult]]
"""Skill执行器类型: (skill_name, params) -> ExecutionResult"""


# ============================================================
# 任务规划器实现
# ============================================================


class BaseLLMClient(ABC):
    """LLM客户端抽象基类"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本响应"""
        pass


class TaskPlanner:
    """
    任务规划器 - 将高层任务分解为Skill序列

    支持两种模式:
    1. LLM模式: 使用LLM进行智能任务分解
    2. 规则模式: 基于预定义规则的快速规划

    使用示例:
        # LLM模式
        planner = TaskPlanner(llm_client=my_llm)
        plan = await planner.plan("装配零件A和零件B", context)

        # 规则模式
        planner = TaskPlanner(use_llm=False)
        plan = await planner.plan("把物体拿到拍照位置", context)
    """

    # 预定义的任务模板
    TASK_TEMPLATES = {
        # 上料/预组装场景
        "上料": [
            {"skill": "perception", "action": "detect_objects", "target": "料框"},
            {"skill": "perception", "action": "localize_3d", "target": "{object}"},
            {"skill": "grasp", "action": "plan_grasp", "target": "{object}"},
            {"skill": "motion", "action": "move_to_grasp", "position": "{grasp_point}"},
            {"skill": "gripper", "action": "grab", "target": "{object}"},
            {"skill": "motion", "action": "move_to", "position": "预组装台"},
        ],
        "抓取": [
            {"skill": "perception", "action": "detect_objects", "target": "{target}"},
            {"skill": "grasp", "action": "plan_grasp", "target": "{target}"},
            {"skill": "motion", "action": "move_to_grasp"},
            {"skill": "gripper", "action": "grab"},
        ],
        "放置": [
            {"skill": "motion", "action": "move_to", "position": "{target}"},
            {"skill": "gripper", "action": "release"},
        ],
        # 柔性装配场景
        "装配": [
            {"skill": "perception", "action": "detect_objects"},
            {"skill": "perception", "action": "localize_3d", "target": "零件A"},
            {"skill": "perception", "action": "localize_3d", "target": "零件B"},
            {"skill": "grasp", "action": "plan_grasp", "target": "零件A"},
            {"skill": "motion", "action": "move_to_assembly"},
            {"skill": "force_control", "action": "insert", "target": "零件B"},
        ],
        "拍照": [
            {"skill": "motion", "action": "move_to", "position": "拍照位置"},
        ],
    }

    # Skill名称映射 (规范化)
    SKILL_ALIASES = {
        # 运动相关
        "移动": "motion",
        "移动到": "motion",
        "运动": "motion",
        "go": "motion",
        "move": "motion",
        # 夹爪相关
        "夹爪": "gripper",
        "抓取": "gripper",
        "松开": "gripper",
        "打开": "gripper",
        "关闭": "gripper",
        "grab": "gripper",
        "release": "gripper",
        # 视觉相关
        "视觉": "perception",
        "检测": "perception",
        "识别": "perception",
        "看": "perception",
        "detect": "perception",
        "see": "perception",
        # 抓取规划
        "规划抓取": "grasp",
        "抓取规划": "grasp",
        "grasp": "grasp",
        # 力控
        "力控": "force_control",
        "力": "force_control",
        "force": "force_control",
        # 关节控制
        "关节": "joint",
        "joint": "joint",
    }

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        use_llm: bool = True,
        max_steps: int = 20,
        plan_timeout: float = 30.0,
        memory_size: int = 10,
    ):
        """
        初始化任务规划器

        Args:
            llm_client: LLM客户端实例
            use_llm: 是否使用LLM进行规划
            max_steps: 最大步骤数
            plan_timeout: 规划超时时间(秒)
            memory_size: 执行记忆队列大小
        """
        self.llm_client = llm_client
        self.use_llm = use_llm and llm_client is not None
        self.max_steps = max_steps
        self.plan_timeout = plan_timeout
        self._plan_counter = 0
        self._history: deque = deque(maxlen=memory_size)

    async def plan(self, task_description: str, context: ExecutionContext) -> TaskPlan:
        """
        规划任务执行

        Args:
            task_description: 任务描述
            context: 执行上下文

        Returns:
            TaskPlan: 任务执行计划
        """
        self._plan_counter += 1
        plan_id = f"plan_{self._plan_counter}_{int(asyncio.get_event_loop().time())}"

        # 1. 识别任务类型
        task_type = self._classify_task(task_description)

        # 2. 生成计划
        if self.use_llm:
            steps = await self._plan_with_llm(task_description, context)
        else:
            steps = await self._plan_with_rules(task_description, context)

        # 3. 创建计划
        plan = TaskPlan(
            plan_id=plan_id,
            original_task=task_description,
            task_type=task_type,
            steps=steps,
            estimated_duration=sum(s.estimated_duration for s in steps),
        )

        return plan

    def record_execution(
        self,
        task_description: str,
        plan: TaskPlan,
        success: bool,
        actual_duration: float = 0.0,
    ) -> None:
        """记录任务执行历史

        Args:
            task_description: 原始任务描述
            plan: 执行的计划
            success: 是否成功
            actual_duration: 实际执行时间
        """
        self._history.append({
            "task": task_description,
            "task_type": plan.task_type.value,
            "steps": [s.skill_name for s in plan.steps],
            "success": success,
            "duration": actual_duration or plan.estimated_duration,
        })

    def _classify_task(self, task_description: str) -> TaskType:
        """识别任务类型"""
        text = task_description.lower()

        # 优先级: 柔性装配 > 装配 > 搬运 > 检测 > 示教
        if any(kw in text for kw in ["柔性装配", "灵活装配", "柔性"]):
            return TaskType.FLEXIBLE_ASSEMBLY
        elif any(kw in text for kw in ["装配", "组装", "配合", "结合"]):
            return TaskType.ASSEMBLY
        elif any(kw in text for kw in ["上料", "预组装", "料框", "供料"]):
            return TaskType.MATERIAL_HANDLING
        elif any(kw in text for kw in ["抓取", "拿", "搬运", "放置", "放到"]):
            return TaskType.PICK_AND_PLACE
        elif any(kw in text for kw in ["检测", "质检", "检查", "拍照"]):
            return TaskType.INSPECTION
        elif any(kw in text for kw in ["示教", "教", "Teach"]):
            return TaskType.TEACHING

        return TaskType.UNKNOWN

    async def _plan_with_rules(
        self, task_description: str, context: ExecutionContext
    ) -> list[TaskStep]:
        """基于规则的任务规划"""
        steps = []
        text = task_description.lower()
        step_id = 1

        # 检测意图关键词
        has_pick = any(kw in text for kw in ["抓", "拿", "取", "拿取"])
        has_place = any(kw in text for kw in ["放", "到", "置", "装"])
        has_detect = any(kw in text for kw in ["检测", "识别", "看", "找"])
        has_assemble = any(kw in text for kw in ["装配", "组装", "结合"])

        # 1. 如果需要检测/识别
        if has_detect:
            steps.append(
                TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="perception",
                    params={"action": "detect_objects"},
                    description="检测场景中的物体",
                    estimated_duration=2.0,
                )
            )
            step_id += 1

        # 2. 如果需要抓取
        if has_pick:
            # 2.1 定位目标
            steps.append(
                TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="perception",
                    params={"action": "localize_3d"},
                    description="获取目标物体3D位置",
                    estimated_duration=1.5,
                    dependencies=[f"step_{step_id - 1}"] if has_detect else [],
                )
            )
            step_id += 1

            # 2.2 规划抓取
            steps.append(
                TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="grasp",
                    params={"action": "plan_grasp"},
                    description="规划抓取方案",
                    estimated_duration=1.0,
                    dependencies=[f"step_{step_id - 1}"],
                )
            )
            step_id += 1

            # 2.3 移动到抓取位置
            steps.append(
                TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="motion",
                    params={"action": "move_to_grasp"},
                    description="移动到抓取位置",
                    estimated_duration=3.0,
                    dependencies=[f"step_{step_id - 1}"],
                )
            )
            step_id += 1

            # 2.4 执行抓取
            steps.append(
                TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="gripper",
                    params={"action": "grab"},
                    description="抓取物体",
                    estimated_duration=1.0,
                    dependencies=[f"step_{step_id - 1}"],
                )
            )
            step_id += 1

        # 3. 如果需要放置/装配
        if has_place or has_assemble:
            # 3.1 移动到目标位置
            target_pos = self._extract_position(task_description)
            steps.append(
                TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="motion",
                    params={"action": "move_to", "position": target_pos},
                    description=f"移动到{target_pos}",
                    estimated_duration=3.0,
                    dependencies=[f"step_{step_id - 1}"] if steps else [],
                )
            )
            step_id += 1

            # 3.2 释放/装配
            if has_assemble:
                steps.append(
                    TaskStep(
                        step_id=f"step_{step_id}",
                        skill_name="force_control",
                        params={"action": "assemble"},
                        description="执行装配",
                        estimated_duration=5.0,
                        dependencies=[f"step_{step_id - 1}"],
                    )
                )
            else:
                steps.append(
                    TaskStep(
                        step_id=f"step_{step_id}",
                        skill_name="gripper",
                        params={"action": "release"},
                        description="释放物体",
                        estimated_duration=1.0,
                        dependencies=[f"step_{step_id - 1}"],
                    )
                )

        # 4. 默认: 简单移动
        if not steps:
            target_pos = self._extract_position(task_description) or "home"
            steps.append(
                TaskStep(
                    step_id="step_1",
                    skill_name="motion",
                    params={"action": "move_to", "position": target_pos},
                    description=f"移动到{target_pos}",
                    estimated_duration=3.0,
                )
            )

        return steps

    async def _plan_with_llm(
        self, task_description: str, context: ExecutionContext
    ) -> list[TaskStep]:
        """基于LLM的任务规划"""

        # 构建提示词
        prompt = self._build_planning_prompt(task_description, context)

        try:
            # 调用LLM生成计划
            response = await asyncio.wait_for(
                self.llm_client.generate(prompt), timeout=self.plan_timeout
            )

            # 解析LLM响应
            steps = self._parse_llm_response(response)

            if steps:
                return steps

        except asyncio.TimeoutError:
            print(f"[TaskPlanner] LLM planning timeout, falling back to rules")
        except Exception as e:
            print(f"[TaskPlanner] LLM planning failed: {e}, falling back to rules")

        # 回退到规则模式
        return await self._plan_with_rules(task_description, context)

    def _build_planning_prompt(
        self, task_description: str, context: ExecutionContext
    ) -> str:
        """构建规划提示词"""

        available_skills = (
            ", ".join(context.available_skills)
            if context.available_skills
            else "motion, gripper, perception, grasp"
        )

        history_str = ""
        if self._history:
            recent = list(self._history)[-3:]
            history_str = "\n近期任务历史:\n" + json.dumps(
                recent, ensure_ascii=False, indent=2
            )

        prompt = f"""你是一个机器人任务规划专家。请将以下任务分解为具体的执行步骤。
{history_str}

任务: {task_description}

当前机器人状态:
{context.to_prompt_context()}

可用技能: {available_skills}

请按照以下JSON格式输出执行计划:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "skill_name": "技能名称",
            "params": {{"参数键": "参数值"}},
            "description": "步骤描述",
            "dependencies": ["依赖步骤ID"],
            "estimated_duration": 预计时间(秒)
        }}
    ]
}}

注意:
1. 只使用提供的可用技能
2. 考虑步骤之间的依赖关系
3. 每个步骤必须是可以直接执行的
4. 估计时间要合理
5. 输出必须是有效的JSON格式

请直接输出JSON，不要其他内容:"""

        return prompt

    def _parse_llm_response(self, response: str) -> list[TaskStep]:
        """解析LLM响应"""
        steps = []

        try:
            # 提取JSON部分
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            step_list = data.get("steps", [])

            for i, step_data in enumerate(step_list):
                step = TaskStep(
                    step_id=step_data.get("step_id", f"step_{i + 1}"),
                    skill_name=self._normalize_skill_name(
                        step_data.get("skill_name", "")
                    ),
                    params=step_data.get("params", {}),
                    description=step_data.get("description", ""),
                    dependencies=step_data.get("dependencies", []),
                    estimated_duration=step_data.get("estimated_duration", 2.0),
                )
                steps.append(step)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[TaskPlanner] Failed to parse LLM response: {e}")

        return steps

    def _normalize_skill_name(self, name: str) -> str:
        """规范化Skill名称"""
        name_lower = name.lower().strip()

        # 检查别名
        for alias, canonical in self.SKILL_ALIASES.items():
            if alias in name_lower:
                return canonical

        return name

    def _extract_position(self, text: str) -> Optional[str]:
        """提取位置信息"""
        position_keywords = [
            "拍照位置",
            "料框",
            "预组装台",
            "产线",
            "原点",
            "等待位",
            "工作台",
            "托盘",
            "传送带",
            "检测台",
            "装配台",
        ]

        for pos in position_keywords:
            if pos in text:
                return pos

        return None


# ============================================================
# 任务执行器
# ============================================================


class TaskExecutor:
    """
    任务执行器 - 执行TaskPlan中的步骤

    使用示例:
        executor = TaskExecutor(skill_executor=my_skill_executor)

        # 执行整个计划
        results = await executor.execute_plan(plan)

        # 或单步执行
        result = await executor.execute_step(step)
    """

    def __init__(
        self,
        skill_executor: SkillExecutor,
        on_step_start: Optional[Callable[[TaskStep], Awaitable]] = None,
        on_step_complete: Optional[
            Callable[[TaskStep, ExecutionResult], Awaitable]
        ] = None,
    ):
        """
        初始化执行器

        Args:
            skill_executor: Skill执行函数
            on_step_start: 步骤开始回调
            on_step_complete: 步骤完成回调
        """
        self.skill_executor = skill_executor
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete

    async def execute_plan(
        self, plan: TaskPlan, stop_on_error: bool = True
    ) -> list[ExecutionResult]:
        """
        执行整个任务计划

        Args:
            plan: 任务计划
            stop_on_error: 错误时是否停止

        Returns:
            list[ExecutionResult]: 每步的执行结果
        """
        results = []
        plan.status = TaskStatus.RUNNING

        # 按依赖顺序获取可执行步骤
        executable_steps = plan.get_executable_steps()

        for step in executable_steps:
            # 触发开始回调
            if self.on_step_start:
                await self.on_step_start(step)

            # 执行步骤
            result = await self.execute_step(step)
            results.append(result)

            # 触发完成回调
            if self.on_step_complete:
                await self.on_step_complete(step, result)

            # 错误处理
            if result.status == TaskStatus.FAILED and stop_on_error:
                plan.status = TaskStatus.FAILED
                print(
                    f"[TaskExecutor] Step {step.step_id} failed, stopping plan execution"
                )
                break

        # 判断整体结果
        if all(r.status == TaskStatus.SUCCESS for r in results):
            plan.status = TaskStatus.SUCCESS
        elif plan.status != TaskStatus.FAILED:
            plan.status = TaskStatus.PENDING

        return results

    async def execute_step(self, step: TaskStep) -> ExecutionResult:
        """执行单个步骤"""
        import time

        start_time = time.time()

        retries = 0
        last_error = None

        while retries <= step.max_retries:
            try:
                # 执行Skill
                result = await self.skill_executor(step.skill_name, step.params)

                if result.status == TaskStatus.SUCCESS:
                    return ExecutionResult(
                        step_id=step.step_id,
                        status=TaskStatus.SUCCESS,
                        output=result.output,
                        duration=time.time() - start_time,
                    )
                else:
                    last_error = result.error

            except Exception as e:
                last_error = str(e)

            retries += 1

            if retries <= step.max_retries and step.retry_on_failure:
                await asyncio.sleep(0.5)  # 重试前等待

        return ExecutionResult(
            step_id=step.step_id,
            status=TaskStatus.FAILED,
            error=last_error or "Unknown error",
            duration=time.time() - start_time,
            retries=retries - 1,
        )


# ============================================================
# 工厂函数
# ============================================================


def create_task_planner(
    llm_client: Optional[BaseLLMClient] = None, use_llm: bool = True, **kwargs
) -> TaskPlanner:
    """
    创建任务规划器实例

    Args:
        llm_client: LLM客户端
        use_llm: 是否使用LLM
        **kwargs: 其他参数

    Returns:
        TaskPlanner实例
    """
    return TaskPlanner(llm_client=llm_client, use_llm=use_llm, **kwargs)


def create_task_executor(skill_executor: SkillExecutor, **kwargs) -> TaskExecutor:
    """
    创建任务执行器实例

    Args:
        skill_executor: Skill执行函数
        **kwargs: 其他参数

    Returns:
        TaskExecutor实例
    """
    return TaskExecutor(skill_executor=skill_executor, **kwargs)
