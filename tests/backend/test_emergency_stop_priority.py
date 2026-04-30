from backend.services.safety_guard import SafetyGuard


def test_estop_has_highest_priority():
    guard = SafetyGuard()
    estop = guard.validate("emergency_stop", {})
    assert estop.allowed is False
    after = guard.validate("move_arm_to", {"x": 0.1, "y": 0.1, "z": 0.2})
    assert after.allowed is False
    assert "estop" in after.reason

