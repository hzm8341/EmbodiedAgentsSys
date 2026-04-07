#!/usr/bin/env python3
"""
独立测试TaskPlanner组件
"""
import asyncio
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable, Awaitable


# ============================================================
# TaskPlanner核心代码（简化版）
# ============================================================

class TaskType(Enum):
    PICK_AND_PLACE = "pick_and_place"
    ASSEMBLY = "assembly"
    INSPECTION = "inspection"
    MATERIAL_HANDLING = "material_handling"
    FLEXIBLE_ASSEMBLY = "flexible_assembly"
    TEACHING = "teaching"
    UNKNOWN = "unknown"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class TaskStep:
    step_id: str
    skill_name: str
    params: dict = field(default_factory=dict)
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    retry_on_failure: bool = True
    max_retries: int = 3


@dataclass
class TaskPlan:
    plan_id: str
    original_task: str
    task_type: TaskType = TaskType.UNKNOWN
    steps: list[TaskStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    estimated_duration: float = 0.0

    def get_executable_steps(self) -> list[TaskStep]:
        executed = set()
        executable = []

        while len(executed) < len(self.steps):
            for step in self.steps:
                if step.step_id in executed:
                    continue

                deps_satisfied = all(dep in executed for dep in step.dependencies)

                if deps_satisfied:
                    executable.append(step)
                    executed.add(step.step_id)

        return executable


@dataclass
class ExecutionContext:
    robot_state: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)
    available_skills: list[str] = field(default_factory=list)
    objects_in_scene: list[dict] = field(default_factory=list)
    safety_constraints: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    step_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    retries: int = 0


# ============================================================
# TaskPlanner实现
# ============================================================

class TaskPlanner:
    """任务规划器 - 将高层任务分解为Skill序列"""

    SKILL_ALIASES = {
        "移动": "motion",
        "移动到": "motion",
        "运动": "motion",
        "夹爪": "gripper",
        "抓取": "gripper",
        "松开": "gripper",
        "打开": "gripper",
        "关闭": "gripper",
        "视觉": "perception",
        "检测": "perception",
        "识别": "perception",
        "规划抓取": "grasp",
        "抓取规划": "grasp",
        "力控": "force_control",
        "力": "force_control",
        "关节": "joint",
    }

    def __init__(self, llm_client=None, use_llm=False, max_steps=20, plan_timeout=30.0):
        self.llm_client = llm_client
        self.use_llm = use_llm and llm_client is not None
        self.max_steps = max_steps
        self.plan_timeout = plan_timeout
        self._plan_counter = 0

    async def plan(self, task_description: str, context: ExecutionContext) -> TaskPlan:
        self._plan_counter += 1
        plan_id = f"plan_{self._plan_counter}"

        task_type = self._classify_task(task_description)
        steps = await self._plan_with_rules(task_description, context)

        plan = TaskPlan(
            plan_id=plan_id,
            original_task=task_description,
            task_type=task_type,
            steps=steps,
            estimated_duration=sum(s.estimated_duration for s in steps),
        )

        return plan

    def _classify_task(self, task_description: str) -> TaskType:
        text = task_description.lower()

        if any(kw in text for kw in ["装配", "组装", "配合"]):
            return TaskType.ASSEMBLY
        elif any(kw in text for kw in ["柔性装配", "灵活装配"]):
            return TaskType.FLEXIBLE_ASSEMBLY
        elif any(kw in text for kw in ["检测", "质检", "检查", "拍照"]):
            return TaskType.INSPECTION
        elif any(kw in text for kw in ["上料", "预组装", "料框", "供料"]):
            return TaskType.MATERIAL_HANDLING
        elif any(kw in text for kw in ["抓取", "拿", "搬运", "放置", "放到"]):
            return TaskType.PICK_AND_PLACE
        elif any(kw in text for kw in ["示教", "教"]):
            return TaskType.TEACHING

        return TaskType.UNKNOWN

    async def _plan_with_rules(self, task_description: str, context: ExecutionContext) -> list[TaskStep]:
        steps = []
        text = task_description.lower()
        step_id = 1

        has_pick = any(kw in text for kw in ["抓", "拿", "取"])
        has_place = any(kw in text for kw in ["放", "到", "置"])
        has_detect = any(kw in text for kw in ["检测", "识别", "看", "找"])
        has_assemble = any(kw in text for kw in ["装配", "组装"])

        # 检测
        if has_detect:
            steps.append(TaskStep(
                step_id=f"step_{step_id}",
                skill_name="perception",
                params={"action": "detect_objects"},
                description="检测场景中的物体",
                estimated_duration=2.0
            ))
            step_id += 1

        # 抓取
        if has_pick:
            steps.append(TaskStep(
                step_id=f"step_{step_id}",
                skill_name="perception",
                params={"action": "localize_3d"},
                description="获取目标物体3D位置",
                estimated_duration=1.5,
                dependencies=[f"step_{step_id-1}"] if has_detect else []
            ))
            step_id += 1

            steps.append(TaskStep(
                step_id=f"step_{step_id}",
                skill_name="grasp",
                params={"action": "plan_grasp"},
                description="规划抓取方案",
                estimated_duration=1.0,
                dependencies=[f"step_{step_id-1}"]
            ))
            step_id += 1

            steps.append(TaskStep(
                step_id=f"step_{step_id}",
                skill_name="motion",
                params={"action": "move_to_grasp"},
                description="移动到抓取位置",
                estimated_duration=3.0,
                dependencies=[f"step_{step_id-1}"]
            ))
            step_id += 1

            steps.append(TaskStep(
                step_id=f"step_{step_id}",
                skill_name="gripper",
                params={"action": "grab"},
                description="抓取物体",
                estimated_duration=1.0,
                dependencies=[f"step_{step_id-1}"]
            ))
            step_id += 1

        # 放置/装配
        if has_place or has_assemble:
            target_pos = self._extract_position(task_description) or "目标位置"
            steps.append(TaskStep(
                step_id=f"step_{step_id}",
                skill_name="motion",
                params={"action": "move_to", "position": target_pos},
                description=f"移动到{target_pos}",
                estimated_duration=3.0,
                dependencies=[f"step_{step_id-1}"] if steps else []
            ))
            step_id += 1

            if has_assemble:
                steps.append(TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="force_control",
                    params={"action": "assemble"},
                    description="执行装配",
                    estimated_duration=5.0,
                    dependencies=[f"step_{step_id-1}"]
                ))
            else:
                steps.append(TaskStep(
                    step_id=f"step_{step_id}",
                    skill_name="gripper",
                    params={"action": "release"},
                    description="释放物体",
                    estimated_duration=1.0,
                    dependencies=[f"step_{step_id-1}"]
                ))

        # 默认移动
        if not steps:
            target_pos = self._extract_position(task_description) or "home"
            steps.append(TaskStep(
                step_id="step_1",
                skill_name="motion",
                params={"action": "move_to", "position": target_pos},
                description=f"移动到{target_pos}",
                estimated_duration=3.0
            ))

        return steps

    def _normalize_skill_name(self, name: str) -> str:
        name_lower = name.lower().strip()

        for alias, canonical in self.SKILL_ALIASES.items():
            if alias in name_lower:
                return canonical

        return name

    def _extract_position(self, text: str) -> Optional[str]:
        position_keywords = [
            "拍照位置", "料框", "预组装台", "产线", "原点", "等待位",
            "工作台", "托盘", "传送带", "检测台", "装配台"
        ]

        for pos in position_keywords:
            if pos in text:
                return pos

        return None


class TaskExecutor:
    """任务执行器"""

    def __init__(self, skill_executor):
        self.skill_executor = skill_executor

    async def execute_plan(self, plan: TaskPlan, stop_on_error: bool = True) -> list[ExecutionResult]:
        results = []
        plan.status = TaskStatus.RUNNING

        executable_steps = plan.get_executable_steps()

        for step in executable_steps:
            result = await self.execute_step(step)
            results.append(result)

            if result.status == TaskStatus.FAILED and stop_on_error:
                plan.status = TaskStatus.FAILED
                break

        if all(r.status == TaskStatus.SUCCESS for r in results):
            plan.status = TaskStatus.SUCCESS
        else:
            plan.status = TaskStatus.PENDING

        return results

    async def execute_step(self, step: TaskStep) -> ExecutionResult:
        import time
        start_time = time.time()

        retries = 0
        last_error = None

        while retries <= step.max_retries:
            try:
                result = await self.skill_executor(step.skill_name, step.params)

                if result.status == TaskStatus.SUCCESS:
                    return ExecutionResult(
                        step_id=step.step_id,
                        status=TaskStatus.SUCCESS,
                        output=result.output,
                        duration=time.time() - start_time
                    )
                else:
                    last_error = result.error

            except Exception as e:
                last_error = str(e)

            retries += 1

            if retries <= step.max_retries and step.retry_on_failure:
                await asyncio.sleep(0.5)

        return ExecutionResult(
            step_id=step.step_id,
            status=TaskStatus.FAILED,
            error=last_error or "Unknown error",
            duration=time.time() - start_time,
            retries=retries - 1
        )


# ============================================================
# 测试
# ============================================================

class MockSkillExecutor:
    async def __call__(self, skill_name: str, params: dict) -> ExecutionResult:
        await asyncio.sleep(0.05)
        print(f"  [MockExecutor] Executing {skill_name} with params: {params}")
        return ExecutionResult(
            step_id="",
            status=TaskStatus.SUCCESS,
            output={"success": True, "skill": skill_name}
        )


async def test_task_classification():
    print("\n" + "="*60)
    print("测试1: 任务类型识别")
    print("="*60)

    planner = TaskPlanner()

    test_cases = [
        ("把零件A装配到零件B", TaskType.ASSEMBLY),
        ("进行柔性装配", TaskType.FLEXIBLE_ASSEMBLY),
        ("检测产品外观", TaskType.INSPECTION),
        ("从料框上料", TaskType.MATERIAL_HANDLING),
        ("把物体拿到拍照位置", TaskType.PICK_AND_PLACE),
        ("示教这个动作", TaskType.TEACHING),
        ("随便做个动作", TaskType.UNKNOWN),
    ]

    for task_desc, expected_type in test_cases:
        result_type = planner._classify_task(task_desc)
        status = "✓" if result_type == expected_type else "✗"
        print(f"  {status} '{task_desc}' -> {result_type.value} (expected: {expected_type.value})")


async def test_rule_based_planning():
    print("\n" + "="*60)
    print("测试2: 基于规则的任务规划")
    print("="*60)

    planner = TaskPlanner()

    context = ExecutionContext(
        robot_state={"gripper": "open", "position": "home"},
        available_skills=["motion", "gripper", "perception", "grasp", "force_control"]
    )

    test_cases = [
        "把料框里的零件拿到拍照位置",
        "检测场景中的物体",
        "执行柔性装配任务",
        "移动到拍照位置",
    ]

    for task_desc in test_cases:
        print(f"\n  任务: {task_desc}")
        plan = await planner.plan(task_desc, context)

        print(f"  计划ID: {plan.plan_id}")
        print(f"  任务类型: {plan.task_type.value}")
        print(f"  步骤数: {len(plan.steps)}")
        print(f"  预计时间: {plan.estimated_duration:.1f}s")

        for i, step in enumerate(plan.steps, 1):
            deps = f" (依赖: {', '.join(step.dependencies)})" if step.dependencies else ""
            print(f"    {i}. {step.skill_name}: {step.description}{deps}")


async def test_plan_execution():
    print("\n" + "="*60)
    print("测试3: 计划执行")
    print("="*60)

    planner = TaskPlanner()
    executor = TaskExecutor(skill_executor=MockSkillExecutor())

    context = ExecutionContext(
        robot_state={"gripper": "open", "position": "home"},
        available_skills=["motion", "gripper", "perception", "grasp"]
    )

    task_desc = "把物体从A移动到B"
    plan = await planner.plan(task_desc, context)

    print(f"\n  执行计划: {task_desc}")
    print(f"  步骤数: {len(plan.steps)}")

    results = await executor.execute_plan(plan)

    print(f"\n  执行结果:")
    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.status == TaskStatus.SUCCESS else "✗"
        print(f"    {i}. {result.step_id}: {result.status.value} ({result.duration:.2f}s)")
        if result.error:
            print(f"       Error: {result.error}")

    print(f"\n  计划最终状态: {plan.status.value}")


async def test_skill_name_normalization():
    print("\n" + "="*60)
    print("测试4: Skill名称规范化")
    print("="*60)

    planner = TaskPlanner()

    test_cases = [
        "移动到位置",
        "夹爪打开",
        "视觉检测",
        "规划抓取",
        "抓取",
        "力控",
    ]

    for name in test_cases:
        normalized = planner._normalize_skill_name(name)
        print(f"  '{name}' -> '{normalized}'")


async def main():
    print("\n" + "="*60)
    print("TaskPlanner组件测试")
    print("="*60)

    await test_task_classification()
    await test_rule_based_planning()
    await test_plan_execution()
    await test_skill_name_normalization()

    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
