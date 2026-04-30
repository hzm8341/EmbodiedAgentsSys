from backend.services.safety_guard import SafetyGuard


def test_safety_guard_blocks_workspace_and_speed_violations():
    guard = SafetyGuard({"max_abs_x": 0.2, "max_abs_y": 0.2, "max_z": 0.5, "max_speed": 0.3})
    d1 = guard.validate("move_arm_to", {"x": 0.5, "y": 0.0, "z": 0.2})
    assert d1.allowed is False
    d2 = guard.validate("move_arm_to", {"x": 0.1, "y": 0.0, "z": 0.2, "speed": 1.0})
    assert d2.allowed is False

