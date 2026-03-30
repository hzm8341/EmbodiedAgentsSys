from agents.harness.core.mode import HarnessMode

def test_harness_mode_enum_values():
    assert HarnessMode.SKILL_MOCK.value == "skill_mock"
    assert HarnessMode.HARDWARE_MOCK.value == "hardware_mock"
    assert HarnessMode.FULL_MOCK.value == "full_mock"
    assert HarnessMode.REAL.value == "real"

def test_harness_mode_from_string():
    assert HarnessMode.from_string("skill_mock") == HarnessMode.SKILL_MOCK
    assert HarnessMode.from_string("HARDWARE_MOCK") == HarnessMode.HARDWARE_MOCK

def test_harness_mode_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        HarnessMode.from_string("nonexistent")
