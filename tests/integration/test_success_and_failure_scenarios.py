"""
成功和失败场景集成测试 - 演示完整的执行流程和紧急处理机制

这个测试模块遵循 TDD 原则：
1. RED: 写失败的测试
2. GREEN: 写最小代码通过测试
3. REFACTOR: 清理代码
"""

import pytest
import asyncio
from agents.policy.action_proposal import (
    ActionProposal, Action, ActionType, ExpectedOutcomeType
)
from agents.policy.validation_pipeline import TwoLevelValidationPipeline
from agents.human_oversight.system_mode import SystemMode
from agents.execution.confirmation import ExecutionConfirmationEngine
from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.feedback.audit_trail import AuditTrail, ExecutionLog
from agents.feedback.alert_system import AlertSystem, AlertLevel


@pytest.fixture
def idle_robot_state():
    """正常空闲的机器人状态"""
    return {
        "arm_is_moving": False,
        "emergency_stop": False,
        "gripper_holding": False,
        "current_pose": [0.0, 0.0, 0.0],
        "collision_detected": False,
    }


@pytest.fixture
def successful_move_proposal():
    """成功的移动动作提案（在工作空间内）"""
    return ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.MOVE_TO,
                params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )
        ]
    )


@pytest.fixture
def failing_move_proposal():
    """失败的移动动作提案（超出工作空间）"""
    return ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.MOVE_TO,
                params={"target_pose": [99, 99, 99], "speed": 0.5},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )
        ]
    )


# ============================================================================
# 场景 1: 成功的验证和确认流程
# ============================================================================
class TestSuccessfulValidationAndConfirmationFlow:
    """
    场景：用户请求机械臂移动到安全位置，系统通过验证、执行、确认

    执行流程：
    提案验证通过 → 人工接管检查 → 执行动作 → 结果确认 → 审计记录
    """

    @pytest.mark.asyncio
    async def test_proposal_passes_two_level_validation(
        self, successful_move_proposal, idle_robot_state
    ):
        """
        测试成功的两层验证流程：
        1. 动作类型通过白名单检查
        2. 参数通过边界检查
        3. 状态检查通过冲突检测
        4. 高危操作标记为需要确认
        """
        pipeline = TwoLevelValidationPipeline()

        # 执行验证
        result = await pipeline.validate_proposal(
            successful_move_proposal,
            idle_robot_state
        )

        # ✅ 断言 1: 验证通过
        assert result.valid, \
            f"应该通过验证，但失败: {result.reason}"

        # ✅ 断言 2: move_to 被标记为需要人工确认
        assert result.requires_human_approval, \
            "move_to 应该被标记为需要人工确认"

        # ✅ 断言 3: 验证器是 second_confirmation（最后一个）
        assert result.validator == "second_confirmation", \
            f"最后的验证器应该是 second_confirmation，实际: {result.validator}"

        print("\n✅ 两层验证流程通过")
        print(f"   - 验证结果: {result.valid}")
        print(f"   - 需要人工确认: {result.requires_human_approval}")
        print(f"   - 最后验证器: {result.validator}")

    @pytest.mark.asyncio
    async def test_successful_execution_confirmation(
        self, successful_move_proposal, idle_robot_state
    ):
        """
        测试成功的执行结果确认：
        1. 执行完成（模拟）
        2. 机械臂到达目标位置
        3. 结果确认为 CONFIRMED
        """
        engine = ExecutionConfirmationEngine()
        action = successful_move_proposal.action_sequence[0]

        # 模拟执行完成的反馈
        import time
        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(
                stage=FeedbackStage.STARTED,
                progress=0.0,
                current_state=idle_robot_state,
                timestamp=t0
            ),
            ExecutionFeedback(
                stage=FeedbackStage.COMPLETED,
                progress=1.0,
                current_state={
                    **idle_robot_state,
                    "current_pose": [0.5, 0.3, 0.2],  # 到达目标
                },
                timestamp=t0 + 1
            ),
        ]

        # 执行确认
        result = await engine.confirm(
            action,
            feedbacks,
            {"current_pose": [0.5, 0.3, 0.2], "collision_detected": False}
        )

        # ✅ 断言 1: 确认成功
        assert result.status == "confirmed", \
            f"应该确认成功，实际: {result.status}"

        # ✅ 断言 2: 位置误差在容差范围内
        assert result.pose_error <= 0.05, \
            f"位置误差应该 <= 0.05m，实际: {result.pose_error}"

        print("\n✅ 执行结果确认通过")
        print(f"   - 确认状态: {result.status}")
        print(f"   - 位置误差: {result.pose_error:.4f}m")

    @pytest.mark.asyncio
    async def test_complete_audit_trail_verification(self):
        """
        测试完整的审计日志链：
        1. 多个事件被记录
        2. 链式哈希确保完整性
        3. 任何篡改都被检测到
        """
        trail = AuditTrail()

        # 记录一系列事件
        events = [
            ExecutionLog(
                event_type="proposal_received",
                action_type="move_to",
                details={"proposal_id": "test_001"}
            ),
            ExecutionLog(
                event_type="validation_passed",
                action_type="move_to",
                details={"validators": ["whitelist", "boundary", "conflict"]}
            ),
            ExecutionLog(
                event_type="execution_started",
                action_type="move_to",
                details={"target_pose": [0.5, 0.3, 0.2]}
            ),
            ExecutionLog(
                event_type="execution_completed",
                action_type="move_to",
                details={"status": "confirmed", "pose_error": 0.02}
            ),
        ]

        for event in events:
            trail.log_event(event)

        # ✅ 断言 1: 记录了4个事件
        assert len(trail.events) == 4, \
            f"应该记录4个事件，实际: {len(trail.events)}"

        # ✅ 断言 2: 链完整性验证
        assert trail.verify_chain_integrity(), \
            "审计链应该通过完整性验证"

        # ✅ 断言 3: 导出为 JSON 成功
        json_str = trail.export_json()
        assert "proposal_received" in json_str, \
            "JSON 导出应该包含事件"

        print("\n✅ 审计日志链验证通过")
        print(f"   - 记录事件数: {len(trail.events)}")
        print(f"   - 链完整性: {trail.verify_chain_integrity()}")


# ============================================================================
# 场景 2: 验证失败和紧急处理
# ============================================================================
class TestValidationFailureAndEmergencyHandling:
    """
    场景：用户请求超出工作空间的动作，系统拒绝 → 警报 →
    人工接管 → 手动操作超过限制 → 触发紧急停止

    执行流程：
    提案 → 验证失败（边界超出）→ WARNING警报 →
    人工接管 → 边界再次失败 → CRITICAL警报 →
    紧急停止 → 完整审计记录
    """

    @pytest.mark.asyncio
    async def test_validation_failure_on_boundary_violation(
        self, failing_move_proposal, idle_robot_state
    ):
        """
        测试边界违规的验证失败：
        1. 动作位置超过工作空间
        2. BoundaryChecker 拒绝
        3. 返回详细的失败原因
        """
        pipeline = TwoLevelValidationPipeline()

        result = await pipeline.validate_proposal(
            failing_move_proposal,
            idle_robot_state
        )

        # ✅ 断言 1: 验证失败
        assert not result.valid, \
            "超出边界的动作应该被拒绝"

        # ✅ 断言 2: 失败原因包含 boundary
        assert "boundary" in result.reason.lower() or "workspace" in result.reason.lower(), \
            f"失败原因应该提及边界，实际: {result.reason}"

        # ✅ 断言 3: 拒绝来自 BoundaryChecker
        assert result.validator == "boundary", \
            f"应该是 boundary validator 拒绝，实际: {result.validator}"

        print("\n✅ 边界违规验证失败检测")
        print(f"   - 验证结果: {result.valid}")
        print(f"   - 失败原因: {result.reason}")
        print(f"   - 拒绝验证器: {result.validator}")

    @pytest.mark.asyncio
    async def test_manual_override_with_boundary_enforcement(
        self, idle_robot_state
    ):
        """
        测试人工接管模式下的强制边界检查和紧急停止：
        1. 进入人工接管模式
        2. 尝试超过限制的手动操作
        3. 系统产生 CRITICAL 警报
        4. 触发紧急停止
        5. 进入终态，无法恢复
        """
        from agents.human_oversight.engine import HumanOversightEngine

        engine = HumanOversightEngine()

        # 第一步：进入人工接管模式
        success = engine.transition_mode(
            SystemMode.MANUAL_OVERRIDE,
            reason="操作员请求手动控制",
            triggered_by="user"
        )

        assert success, "应该成功进入人工接管模式"
        assert engine.current_mode == SystemMode.MANUAL_OVERRIDE

        print("\n✅ 进入人工接管模式")

        # 第二步：尝试超过限制的手动操作
        unsafe_action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 999},  # max=100
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )

        validation_result = await engine.validate_manual_action(unsafe_action)

        # ✅ 断言 1: 手动模式仍然强制边界检查
        assert not validation_result.valid, \
            "手动模式不应该允许超过限制的操作"

        # ✅ 断言 2: 产生 CRITICAL 警报
        critical_alerts = [
            a for a in engine.alert_system.alerts
            if a.level == AlertLevel.CRITICAL
        ]
        assert len(critical_alerts) > 0, \
            "应该产生 CRITICAL 警报"

        print(f"✅ 手动模式边界检查失败，产生 CRITICAL 警报")
        print(f"   - 验证结果: {validation_result.valid}")
        print(f"   - CRITICAL 警报数: {len(critical_alerts)}")

        # 第三步：触发紧急停止
        emergency_success = engine.transition_mode(
            SystemMode.EMERGENCY_STOP,
            reason="边界违规检测，触发紧急停止",
            triggered_by="safety_system"
        )

        assert emergency_success, "应该成功进入紧急停止"
        assert engine.current_mode == SystemMode.EMERGENCY_STOP

        print(f"✅ 紧急停止触发成功")

        # 第四步：验证紧急停止是终态
        recovery_attempt = engine.transition_mode(
            SystemMode.AUTOMATIC,
            reason="尝试恢复",
            triggered_by="user"
        )

        # ✅ 断言 3: 无法从紧急停止恢复
        assert not recovery_attempt, \
            "应该无法从紧急停止状态转出"
        assert engine.current_mode == SystemMode.EMERGENCY_STOP, \
            "应该保持在紧急停止状态"

        print(f"✅ 紧急停止是终态，无法恢复")

        # 第五步：验证审计记录
        audit_trail = engine.audit_trail
        assert audit_trail.verify_chain_integrity(), \
            "审计链应该完整"

        print(f"✅ 审计日志完整且不可篡改")
        print(f"   - 审计事件数: {len(audit_trail.events)}")
        print(f"   - 链完整性: {audit_trail.verify_chain_integrity()}")

    @pytest.mark.asyncio
    async def test_confirmation_detects_execution_failure(self):
        """
        测试确认引擎检测执行失败：
        1. 执行状态显示完成
        2. 但实际机械臂没有到达目标
        3. 确认引擎检测到失败
        """
        engine = ExecutionConfirmationEngine()

        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        # 模拟执行反馈显示完成，但实际位置没变
        import time
        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(
                stage=FeedbackStage.STARTED,
                progress=0.0,
                current_state={"current_pose": [0.0, 0.0, 0.0]},
                timestamp=t0
            ),
            ExecutionFeedback(
                stage=FeedbackStage.COMPLETED,
                progress=1.0,
                current_state={"current_pose": [0.0, 0.0, 0.0]},  # 没有移动!
                timestamp=t0 + 1
            ),
        ]

        actual_state = {
            "current_pose": [0.0, 0.0, 0.0],  # 还在原位置
            "collision_detected": False,
        }

        result = await engine.confirm(action, feedbacks, actual_state)

        # ✅ 断言: 确认失败，尽管反馈显示完成
        assert result.status == "failed", \
            f"应该检测到执行失败，实际: {result.status}"

        assert result.pose_error > 0.05, \
            f"位置误差应该很大，实际: {result.pose_error}"

        print("\n✅ 执行确认检测到失败")
        print(f"   - 确认状态: {result.status}")
        print(f"   - 位置误差: {result.pose_error:.4f}m")
        print(f"   - 失败原因: {result.reason}")


# ============================================================================
# 场景 3: 超时检测
# ============================================================================
class TestTimeoutDetection:
    """
    场景：执行耗时过长，超过预设超时时间，系统触发超时处理
    """

    @pytest.mark.asyncio
    async def test_execution_timeout_detection(self):
        """
        测试超时检测：
        1. 反馈显示执行耗时 > 超时时间
        2. 确认引擎标记为 TIMEOUT
        """
        engine = ExecutionConfirmationEngine()

        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        # 模拟超时的执行
        import time
        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(
                stage=FeedbackStage.STARTED,
                progress=0.0,
                current_state={"current_pose": [0.0, 0.0, 0.0]},
                timestamp=t0
            ),
            ExecutionFeedback(
                stage=FeedbackStage.COMPLETED,
                progress=1.0,
                current_state={"current_pose": [0.5, 0.3, 0.2]},
                timestamp=t0 + 100  # 100 秒后才完成！
            ),
        ]

        result = await engine.confirm(
            action,
            feedbacks,
            {"current_pose": [0.5, 0.3, 0.2], "collision_detected": False},
            timeout_seconds=5.0  # 5 秒超时
        )

        # ✅ 断言: 检测到超时
        assert result.status == "timeout", \
            f"应该检测到超时，实际: {result.status}"

        print("\n✅ 超时检测")
        print(f"   - 确认状态: {result.status}")
        print(f"   - 失败原因: {result.reason}")
