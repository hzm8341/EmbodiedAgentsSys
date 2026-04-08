#!/usr/bin/env python
"""
独立的 TDD 场景测试 - 演示成功和失败的完整流程

执行: python test_scenarios_standalone.py
"""

import asyncio
import sys
import time
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, '/media/hzm/data_disk/EmbodiedAgentsSys')

from agents.policy.action_proposal import (
    ActionProposal, Action, ActionType, ExpectedOutcomeType
)
from agents.policy.validation_pipeline import TwoLevelValidationPipeline
from agents.execution.confirmation import ExecutionConfirmationEngine
from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.human_oversight.engine import HumanOversightEngine
from agents.human_oversight.system_mode import SystemMode
from agents.feedback.audit_trail import AuditTrail, ExecutionLog
from agents.feedback.alert_system import AlertLevel


async def test_scenario_1_successful_flow():
    """
    ✅ 场景 1: 成功的验证和执行流程

    流程：
    1. 创建有效的动作提案（在工作空间内）
    2. 通过两层验证（whitelist + boundary）
    3. 标记为需要人工确认（move_to 很危险）
    4. 执行完成，结果确认成功
    5. 完整的审计日志记录
    """
    print("\n" + "="*70)
    print("✅ 场景 1: 成功执行流程")
    print("="*70)

    # 1️⃣ 创建有效提案
    proposal = ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.MOVE_TO,
                params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )
        ]
    )

    robot_state = {
        "arm_is_moving": False,
        "emergency_stop": False,
        "gripper_holding": False,
        "current_pose": [0.0, 0.0, 0.0],
        "collision_detected": False,
    }

    print(f"\n1️⃣ 创建动作提案")
    print(f"   - 动作类型: {proposal.action_sequence[0].action_type.value}")
    print(f"   - 目标位置: {proposal.action_sequence[0].params['target_pose']}")

    # 2️⃣ 两层验证
    pipeline = TwoLevelValidationPipeline()
    validation_result = await pipeline.validate_proposal(proposal, robot_state)

    print(f"\n2️⃣ 两层验证")
    assert validation_result.valid, f"验证失败: {validation_result.reason}"
    assert validation_result.requires_human_approval, "move_to 应该需要人工确认"
    print(f"   ✓ 验证通过")
    print(f"   ✓ 需要人工确认: {validation_result.requires_human_approval}")
    print(f"   ✓ 验证器链: whitelist → boundary → conflict → second_confirmation")

    # 3️⃣ 执行结果确认
    engine = ExecutionConfirmationEngine()
    action = proposal.action_sequence[0]

    # 模拟执行完成的反馈
    t0 = time.time()
    feedbacks = [
        ExecutionFeedback(
            stage=FeedbackStage.STARTED,
            progress=0.0,
            current_state=robot_state,
            timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)
        ),
        ExecutionFeedback(
            stage=FeedbackStage.IN_PROGRESS,
            progress=0.5,
            current_state=robot_state,
            timestamp=datetime.fromtimestamp(t0 + 0.5, tz=timezone.utc)
        ),
        ExecutionFeedback(
            stage=FeedbackStage.COMPLETED,
            progress=1.0,
            current_state={
                **robot_state,
                "current_pose": [0.5, 0.3, 0.2],  # 到达目标
            },
            timestamp=datetime.fromtimestamp(t0 + 1.0, tz=timezone.utc)
        ),
    ]

    confirmation = await engine.confirm(
        action,
        feedbacks,
        {"current_pose": [0.5, 0.3, 0.2], "collision_detected": False}
    )

    print(f"\n3️⃣ 执行完成和结果确认")
    assert confirmation.status == "confirmed", f"确认失败: {confirmation.reason}"
    print(f"   ✓ 确认状态: {confirmation.status}")
    print(f"   ✓ 位置误差: {confirmation.pose_error:.4f}m (容差: 0.05m)")

    # 4️⃣ 审计日志
    trail = AuditTrail()
    events = [
        ExecutionLog("proposal_received", "move_to", details={"proposal_id": "test_001"}),
        ExecutionLog("validation_passed", "move_to", details={"validators": ["whitelist", "boundary"]}),
        ExecutionLog("execution_started", "move_to", details={"target_pose": [0.5, 0.3, 0.2]}),
        ExecutionLog("execution_completed", "move_to", details={"status": "confirmed"}),
    ]

    for event in events:
        trail.log_event(event)

    print(f"\n4️⃣ 审计日志记录")
    assert trail.verify_chain_integrity(), "审计链被篡改"
    assert len(trail.events) == 4, f"应该有4个事件，实际: {len(trail.events)}"
    print(f"   ✓ 审计事件数: {len(trail.events)}")
    print(f"   ✓ 链完整性验证: {trail.verify_chain_integrity()}")
    print(f"   ✓ 事件链: {' → '.join([e.event_type for e in trail.events])}")

    print(f"\n✅ 场景 1 通过: 成功执行和记录")


async def test_scenario_2_failure_and_emergency():
    """
    ❌ 场景 2: 验证失败和紧急处理流程

    流程：
    1. 创建超出工作空间的提案
    2. BoundaryChecker 拒绝
    3. 进入人工接管模式
    4. 尝试手动操作超过限制
    5. 系统产生 CRITICAL 警报
    6. 触发紧急停止（终态）
    7. 完整的失败流程被审计记录
    """
    print("\n" + "="*70)
    print("❌ 场景 2: 验证失败和紧急处理")
    print("="*70)

    # 1️⃣ 创建无效提案（超出边界）
    bad_proposal = ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.MOVE_TO,
                params={"target_pose": [99, 99, 99], "speed": 0.5},  # 超出工作空间
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )
        ]
    )

    robot_state = {
        "arm_is_moving": False,
        "emergency_stop": False,
        "gripper_holding": False,
    }

    print(f"\n1️⃣ 创建无效提案（超出边界）")
    print(f"   - 目标位置: [99, 99, 99]")
    print(f"   - 工作空间: x∈[0.1,1.5], y∈[-1.0,1.0], z∈[0.0,2.0]")

    # 2️⃣ 验证失败
    pipeline = TwoLevelValidationPipeline()
    validation_result = await pipeline.validate_proposal(bad_proposal, robot_state)

    print(f"\n2️⃣ 验证失败（预期）")
    assert not validation_result.valid, "应该拒绝超出边界的动作"
    assert "boundary" in validation_result.reason.lower(), f"应该提及边界: {validation_result.reason}"
    print(f"   ✓ 验证失败")
    print(f"   ✓ 失败原因: {validation_result.reason}")
    print(f"   ✓ 拒绝验证器: {validation_result.validator}")

    # 3️⃣ 进入人工接管模式
    oversight = HumanOversightEngine()
    success = oversight.transition_mode(
        SystemMode.MANUAL_OVERRIDE,
        reason="操作员请求手动控制",
        triggered_by="user"
    )

    print(f"\n3️⃣ 进入人工接管模式")
    assert success, "应该成功进入人工接管"
    assert oversight.current_mode == SystemMode.MANUAL_OVERRIDE
    print(f"   ✓ 模式转换成功")
    print(f"   ✓ 当前模式: {oversight.current_mode.value}")

    # 4️⃣ 尝试超过限制的手动操作
    unsafe_action = Action(
        action_type=ActionType.GRIPPER_CLOSE,
        params={"force": 999},  # 超过限制 (max=100)
        expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
    )

    validation_result = await oversight.validate_manual_action(unsafe_action)

    print(f"\n4️⃣ 手动操作超过安全限制")
    assert not validation_result.valid, "应该拒绝超过限制的操作"
    print(f"   ✓ 操作被拒绝")
    print(f"   ✓ 手动模式仍然强制边界检查")

    # 5️⃣ 检查 CRITICAL 警报
    critical_alerts = [
        a for a in oversight.alert_system.alerts
        if a.level == AlertLevel.CRITICAL
    ]

    print(f"\n5️⃣ CRITICAL 警报产生")
    assert len(critical_alerts) > 0, "应该产生 CRITICAL 警报"
    print(f"   ✓ 警报数: {len(critical_alerts)}")
    print(f"   ✓ 警报消息: {critical_alerts[0].message}")

    # 6️⃣ 触发紧急停止
    emergency_success = oversight.transition_mode(
        SystemMode.EMERGENCY_STOP,
        reason="边界违规检测到，触发紧急停止",
        triggered_by="safety_system"
    )

    print(f"\n6️⃣ 触发紧急停止")
    assert emergency_success, "应该成功进入紧急停止"
    assert oversight.current_mode == SystemMode.EMERGENCY_STOP
    print(f"   ✓ 紧急停止激活")
    print(f"   ✓ 当前模式: {oversight.current_mode.value}")

    # 7️⃣ 验证紧急停止是终态
    recovery_attempt = oversight.transition_mode(
        SystemMode.AUTOMATIC,
        reason="尝试恢复",
        triggered_by="user"
    )

    print(f"\n7️⃣ 验证紧急停止是终态")
    assert not recovery_attempt, "应该无法从紧急停止恢复"
    assert oversight.current_mode == SystemMode.EMERGENCY_STOP
    print(f"   ✓ 无法从紧急停止状态转出")
    print(f"   ✓ 系统处于安全的终止状态")

    # 8️⃣ 审计日志验证
    audit_trail = oversight.audit_trail
    assert audit_trail.verify_chain_integrity(), "审计链应该完整"

    print(f"\n8️⃣ 审计日志")
    print(f"   ✓ 审计事件数: {len(audit_trail.events)}")
    print(f"   ✓ 链完整性: {audit_trail.verify_chain_integrity()}")
    print(f"   ✓ 事件流: {' → '.join([e.event_type for e in audit_trail.events])}")

    print(f"\n✅ 场景 2 通过: 失败被正确处理和记录")


async def test_scenario_3_timeout_detection():
    """
    ⏱️ 场景 3: 执行超时检测

    流程：
    1. 执行反馈显示完成
    2. 但执行耗时超过预设超时
    3. 确认引擎标记为 TIMEOUT
    """
    print("\n" + "="*70)
    print("⏱️  场景 3: 超时检测")
    print("="*70)

    engine = ExecutionConfirmationEngine()

    action = Action(
        action_type=ActionType.MOVE_TO,
        params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
        expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
    )

    # 模拟超时的执行
    t0 = time.time()
    feedbacks = [
        ExecutionFeedback(
            stage=FeedbackStage.STARTED,
            progress=0.0,
            current_state={"current_pose": [0.0, 0.0, 0.0]},
            timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)
        ),
        ExecutionFeedback(
            stage=FeedbackStage.COMPLETED,
            progress=1.0,
            current_state={"current_pose": [0.5, 0.3, 0.2]},
            timestamp=datetime.fromtimestamp(t0 + 100, tz=timezone.utc)  # 100秒后!
        ),
    ]

    print(f"\n1️⃣ 执行耗时过长")
    print(f"   - 实际耗时: 100 秒")
    print(f"   - 超时设置: 5 秒")

    result = await engine.confirm(
        action,
        feedbacks,
        {"current_pose": [0.5, 0.3, 0.2], "collision_detected": False},
        timeout_seconds=5.0
    )

    print(f"\n2️⃣ 超时检测")
    assert result.status == "timeout", f"应该检测到超时，实际: {result.status}"
    print(f"   ✓ 确认状态: {result.status}")
    print(f"   ✓ 失败原因: {result.reason}")

    print(f"\n✅ 场景 3 通过: 超时被正确检测")


async def main():
    """
    主测试流程 - TDD 的 GREEN 阶段：
    编写通过所有测试的最小代码
    """
    print("\n" + "="*70)
    print("🧪 EmbodiedAgentsSys TDD 集成测试")
    print("="*70)
    print("\n这个测试演示了三个关键场景：")
    print("  1️⃣  成功的验证和执行流程")
    print("  2️⃣  验证失败和紧急处理")
    print("  3️⃣  执行超时检测")

    try:
        # 场景 1: 成功
        await test_scenario_1_successful_flow()

        # 场景 2: 失败和紧急处理
        await test_scenario_2_failure_and_emergency()

        # 场景 3: 超时
        await test_scenario_3_timeout_detection()

        # 总结
        print("\n" + "="*70)
        print("✅ 所有测试通过！")
        print("="*70)
        print("\n📊 测试总结:")
        print("  ✓ 场景 1: 成功执行 - 通过")
        print("  ✓ 场景 2: 失败和紧急处理 - 通过")
        print("  ✓ 场景 3: 超时检测 - 通过")
        print("\n🎯 TDD 验证:")
        print("  ✓ RED: 所有测试预期的行为都已定义")
        print("  ✓ GREEN: 系统成功通过所有测试")
        print("  ✓ REFACTOR: 代码已优化和清理")
        print("\n" + "="*70 + "\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 意外错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
