"""
测试TaskPlanner组件
"""
import asyncio
import sys
import os

# AGENTS_DOCS_BUILD is set in conftest.py; set here as fallback
os.environ.setdefault("AGENTS_DOCS_BUILD", "1")

from agents.components.task_planner import TaskPlanner

# 以下类在当前版本的 task_planner 中尚未实现，使用占位符保持向后兼容
try:
    from agents.components.task_planner import (
        TaskExecutor,
        ExecutionContext,
        TaskType,
        TaskStatus,
        TaskStep,
        ExecutionResult,
    )
except ImportError:
    TaskExecutor = None
    ExecutionContext = None
    TaskType = None
    TaskStatus = None
    TaskStep = None
    ExecutionResult = None


# 模拟LLM客户端
class MockLLMClient:
    """模拟LLM客户端用于测试"""
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """模拟LLM生成"""
        # 简单的基于关键词的响应模拟
        await asyncio.sleep(0.1)  # 模拟API延迟
        
        if "装配" in prompt:
            return '''{
                "steps": [
                    {
                        "step_id": "step_1",
                        "skill_name": "perception",
                        "params": {"action": "detect_objects"},
                        "description": "检测场景中的物体",
                        "dependencies": [],
                        "estimated_duration": 2.0
                    },
                    {
                        "step_id": "step_2",
                        "skill_name": "perception",
                        "params": {"action": "localize_3d", "target": "零件A"},
                        "description": "定位零件A",
                        "dependencies": ["step_1"],
                        "estimated_duration": 1.5
                    },
                    {
                        "step_id": "step_3",
                        "skill_name": "grasp",
                        "params": {"action": "plan_grasp", "target": "零件A"},
                        "description": "规划抓取零件A",
                        "dependencies": ["step_2"],
                        "estimated_duration": 1.0
                    },
                    {
                        "step_id": "step_4",
                        "skill_name": "motion",
                        "params": {"action": "move_to_grasp"},
                        "description": "移动到抓取位置",
                        "dependencies": ["step_3"],
                        "estimated_duration": 3.0
                    },
                    {
                        "step_id": "step_5",
                        "skill_name": "gripper",
                        "params": {"action": "grab"},
                        "description": "抓取零件A",
                        "dependencies": ["step_4"],
                        "estimated_duration": 1.0
                    },
                    {
                        "step_id": "step_6",
                        "skill_name": "motion",
                        "params": {"action": "move_to", "position": "装配台"},
                        "description": "移动到装配位置",
                        "dependencies": ["step_5"],
                        "estimated_duration": 3.0
                    },
                    {
                        "step_id": "step_7",
                        "skill_name": "force_control",
                        "params": {"action": "assemble"},
                        "description": "执行装配",
                        "dependencies": ["step_6"],
                        "estimated_duration": 5.0
                    }
                ]
            }'''
        elif "抓取" in prompt:
            return '''{
                "steps": [
                    {
                        "step_id": "step_1",
                        "skill_name": "perception",
                        "params": {"action": "detect_objects"},
                        "description": "检测目标物体",
                        "dependencies": [],
                        "estimated_duration": 2.0
                    },
                    {
                        "step_id": "step_2",
                        "skill_name": "grasp",
                        "params": {"action": "plan_grasp"},
                        "description": "规划抓取",
                        "dependencies": ["step_1"],
                        "estimated_duration": 1.0
                    },
                    {
                        "step_id": "step_3",
                        "skill_name": "motion",
                        "params": {"action": "move_to_grasp"},
                        "description": "移动到抓取位置",
                        "dependencies": ["step_2"],
                        "estimated_duration": 3.0
                    },
                    {
                        "step_id": "step_4",
                        "skill_name": "gripper",
                        "params": {"action": "grab"},
                        "description": "抓取物体",
                        "dependencies": ["step_3"],
                        "estimated_duration": 1.0
                    }
                ]
            }'''
        else:
            return '''{
                "steps": [
                    {
                        "step_id": "step_1",
                        "skill_name": "motion",
                        "params": {"action": "move_to", "position": "home"},
                        "description": "移动到默认位置",
                        "dependencies": [],
                        "estimated_duration": 3.0
                    }
                ]
            }'''


# 模拟Skill执行器
class MockSkillExecutor:
    """模拟Skill执行器"""
    
    async def __call__(self, skill_name: str, params: dict) -> ExecutionResult:
        """模拟执行Skill"""
        await asyncio.sleep(0.05)  # 模拟执行时间
        
        print(f"  [MockExecutor] Executing {skill_name} with params: {params}")
        
        # 模拟成功
        return ExecutionResult(
            step_id="",
            status=TaskStatus.SUCCESS,
            output={"success": True, "skill": skill_name}
        )


async def test_task_classification():
    """测试任务类型识别"""
    print("\n" + "="*60)
    print("测试1: 任务类型识别")
    print("="*60)
    
    planner = TaskPlanner(use_llm=False)
    
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
    """测试基于规则的任务规划"""
    print("\n" + "="*60)
    print("测试2: 基于规则的任务规划")
    print("="*60)
    
    planner = TaskPlanner(use_llm=False)
    
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


async def test_llm_based_planning():
    """测试基于LLM的任务规划"""
    print("\n" + "="*60)
    print("测试3: 基于LLM的任务规划")
    print("="*60)
    
    llm_client = MockLLMClient()
    planner = TaskPlanner(llm_client=llm_client, use_llm=True)
    
    context = ExecutionContext(
        robot_state={"gripper": "open", "position": "home"},
        available_skills=["motion", "gripper", "perception", "grasp", "force_control"],
        objects_in_scene=[
            {"name": "零件A", "position": "料框"},
            {"name": "零件B", "position": "工作台"}
        ]
    )
    
    test_cases = [
        "把零件A装配到零件B",
        "抓取料框中的零件",
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
    """测试计划执行"""
    print("\n" + "="*60)
    print("测试4: 计划执行")
    print("="*60)
    
    planner = TaskPlanner(use_llm=False)
    executor = TaskExecutor(skill_executor=MockSkillExecutor())
    
    context = ExecutionContext(
        robot_state={"gripper": "open", "position": "home"},
        available_skills=["motion", "gripper", "perception", "grasp"]
    )
    
    # 创建测试计划
    task_desc = "把物体从A移动到B"
    plan = await planner.plan(task_desc, context)
    
    print(f"\n  执行计划: {task_desc}")
    print(f"  步骤数: {len(plan.steps)}")
    
    # 执行计划
    results = await executor.execute_plan(plan)
    
    print(f"\n  执行结果:")
    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.status == TaskStatus.SUCCESS else "✗"
        print(f"    {i}. {result.step_id}: {result.status.value} ({result.duration:.2f}s)")
        if result.error:
            print(f"       Error: {result.error}")
    
    print(f"\n  计划最终状态: {plan.status.value}")


async def test_chain_format():
    """测试转换为SkillChain格式"""
    print("\n" + "="*60)
    print("测试5: SkillChain格式转换")
    print("="*60)
    
    planner = TaskPlanner(use_llm=False)
    
    context = ExecutionContext(
        robot_state={"gripper": "open"},
        available_skills=["motion", "gripper", "perception", "grasp"]
    )
    
    plan = await planner.plan("把零件拿到检测台", context)
    chain_format = plan.to_chain_format()
    
    print(f"\n  SkillChain格式:")
    for i, step in enumerate(chain_format, 1):
        print(f"    {i}. skill: {step['skill_name']}, params: {step['params']}")


async def test_skill_name_normalization():
    """测试Skill名称规范化"""
    print("\n" + "="*60)
    print("测试6: Skill名称规范化")
    print("="*60)
    
    planner = TaskPlanner(use_llm=False)
    
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
    """主测试函数"""
    print("\n" + "="*60)
    print("TaskPlanner组件测试")
    print("="*60)
    
    await test_task_classification()
    await test_rule_based_planning()
    await test_llm_based_planning()
    await test_plan_execution()
    await test_chain_format()
    await test_skill_name_normalization()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
