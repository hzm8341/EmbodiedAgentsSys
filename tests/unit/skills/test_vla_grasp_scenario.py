"""
VLA 抓取任务集成测试（逻辑层）

覆盖链路：
- 视觉检测结果 -> GraspSkill 抓取规划 / 验证 / 路径规划
- MotionSkill / GripperSkill 执行基础抓取动作

注意：
- 本测试不依赖真实相机 / 机械臂 / ROS，仅在 Python 逻辑层验证
  “视觉-语言-动作（VLA）抓取” 场景的关键步骤是否协同工作。
"""

import asyncio

from skills.manipulation.grasp_skill import GraspSkill, SkillStatus as GraspStatus
from skills.arm_control.motion_skill import MotionSkill
from skills.arm_control.gripper_skill import GripperSkill, SkillStatus as ArmStatus


async def _run_vla_grasp_scenario() -> bool:
    """执行一次完整的“检测 -> 抓取规划 -> 验证 -> 路径 -> 夹爪控制”流程。"""
    grasp_skill = GraspSkill()
    motion_skill = MotionSkill()
    gripper_skill = GripperSkill()

    # Step 1: 构造伪造的目标检测结果
    detection = {
        "class_name": "test_object",
        "bbox": [100, 120, 200, 260],
        "confidence": 0.9,
    }

    # Step 2: 为检测结果规划抓取
    plan_result = await grasp_skill.execute("plan_grasp", detection=detection)
    assert plan_result.status == GraspStatus.SUCCESS
    assert "best_grasp" in plan_result.output

    best_grasp = plan_result.output["best_grasp"]

    # Step 3: 验证抓取点可行性
    validate_result = await grasp_skill.execute(
        "validate_grasp",
        grasp_point=best_grasp,
    )
    assert validate_result.status == GraspStatus.SUCCESS
    assert validate_result.output["valid"] is True

    # Step 4: 生成从起点到抓取点的路径
    path_result = await grasp_skill.execute(
        "optimize_path",
        grasp_point=best_grasp,
        start_position={"x": 0.0, "y": 0.0, "z": 0.3},
    )
    assert path_result.status == GraspStatus.SUCCESS
    path = path_result.output["path"]
    assert path[0]["type"] == "start"
    assert path[-1]["type"] == "grasp"
    assert path_result.output["path_length"] == len(path)

    # Step 5: 使用 MotionSkill / GripperSkill 模拟执行抓取流程
    # 这里我们不做真实运动学，仅验证接口调用与状态更新

    # 5.1 移动到“料框”预设位置，模拟接近目标
    move_to_bin = await motion_skill.execute(action="move_to", target="bin")
    assert move_to_bin.status == ArmStatus.SUCCESS

    # 5.2 打开夹爪，准备抓取
    open_res = await gripper_skill.execute("open")
    assert open_res.status == ArmStatus.SUCCESS

    # 5.3 模拟 “向下” 接近抓取点 的相对运动
    move_down = await motion_skill.execute(
        action="move_relative",
        position=[0.0, 0.0, -0.05, 0.0, 0.0, 0.0],
    )
    assert move_down.status == ArmStatus.SUCCESS

    # 5.4 闭合夹爪，完成抓取
    close_res = await gripper_skill.execute("close")
    assert close_res.status == ArmStatus.SUCCESS

    return True


def test_vla_grasp_scenario_end_to_end():
    """
    逻辑层端到端测试：
    确认抓取规划技能与机械臂运动 / 夹爪技能可以协同完成一次抓取流程。
    """

    success = asyncio.run(_run_vla_grasp_scenario())
    assert success is True

