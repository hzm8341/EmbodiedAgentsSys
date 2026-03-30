from enum import Enum


class HarnessMode(str, Enum):
    SKILL_MOCK = "skill_mock"
    HARDWARE_MOCK = "hardware_mock"
    FULL_MOCK = "full_mock"
    REAL = "real"

    @classmethod
    def from_string(cls, value: str) -> "HarnessMode":
        v = value.lower()
        for mode in cls:
            if mode.value == v:
                return mode
        raise ValueError(f"Unknown HarnessMode: {value!r}")
