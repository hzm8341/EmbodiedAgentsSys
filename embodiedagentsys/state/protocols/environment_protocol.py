"""ENVIRONMENT protocol - current environment state."""

from dataclasses import dataclass


@dataclass
class ObjectState:
    """Object in environment."""
    id: str
    class_name: str
    position: dict
    confidence: float = 1.0


@dataclass
class RobotState:
    """Robot state in environment."""
    id: str
    position: dict
    status: str = "idle"


@dataclass
class EnvironmentState:
    """Complete environment state."""
    objects: list[ObjectState] = None
    robots: list[RobotState] = None
    updated_at: str = ""


def parse_environment_protocol(content: dict) -> EnvironmentState:
    """Parse environment protocol content."""
    objects = [ObjectState(**o) for o in content.get("objects", [])]
    robots = [RobotState(**r) for r in content.get("robots", [])]
    return EnvironmentState(objects=objects, robots=robots, updated_at=content.get("updated_at", ""))
