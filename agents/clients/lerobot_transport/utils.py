import sys
import types
from typing import Any, Dict
from dataclasses import dataclass, field
import numpy as np


# HACK: We define helper classes here, but set their __module__ to match
# what the server expects. This tricks pickle.


@dataclass
class RemotePolicyConfig:
    policy_type: str
    pretrained_name_or_path: str
    lerobot_features: Dict
    actions_per_chunk: int
    device: str = "cpu"
    rename_map: Dict = field(default_factory=dict)


# Tell pickle this class actually belongs to 'lerobot.async_inference.helpers'
RemotePolicyConfig.__module__ = "lerobot.async_inference.helpers"


@dataclass
class TimedObservation:
    timestamp: float
    observation: Any
    timestep: int
    must_go: bool = False


# Tell pickle this class actually belongs to 'lerobot.async_inference.helpers'
TimedObservation.__module__ = "lerobot.async_inference.helpers"


@dataclass
class TimedAction:
    timestamp: float
    timestep: int
    action: Any


# Tell pickle this class actually belongs to 'lerobot.async_inference.helpers'
TimedAction.__module__ = "lerobot.async_inference.helpers"


# Create module chain for pickle
mod_helpers = types.ModuleType("lerobot.async_inference.helpers")
mod_helpers.RemotePolicyConfig = RemotePolicyConfig
mod_helpers.TimedObservation = TimedObservation
mod_helpers.TimedAction = TimedAction

# Add modules to sys path
sys.modules["lerobot"] = types.ModuleType("lerobot")
sys.modules["lerobot.async_inference"] = types.ModuleType("lerobot.async_inference")
sys.modules["lerobot.async_inference.helpers"] = mod_helpers


def build_inference_request(observation: dict, skill_token: str):
    """Build LeRobot inference request

    Args:
        observation: Observation data dict
        skill_token: Skill description/instruction

    Returns:
        InferenceRequest-like object with observation and language fields
    """

    class InferenceRequest:
        def __init__(self):
            self.observation = Observation()
            self.language = skill_token

    class Observation:
        def __init__(self):
            self.state = State()
            self.image = ImageData()

    class State:
        def __init__(self):
            self.joint_positions = []
            self.joint_velocities = []

    class ImageData:
        def __init__(self):
            self.data = b""
            self.height = 0
            self.width = 0
            self.channels = 3

    request = InferenceRequest()

    joint_positions = observation.get("joint_positions", [0.0] * 7)
    joint_velocities = observation.get("joint_velocities", [0.0] * 7)

    if isinstance(joint_positions, (list, tuple)):
        request.observation.state.joint_positions.extend(joint_positions)
    else:
        request.observation.state.joint_positions.extend(list(joint_positions))

    if isinstance(joint_velocities, (list, tuple)):
        request.observation.state.joint_velocities.extend(joint_velocities)
    else:
        request.observation.state.joint_velocities.extend(list(joint_velocities))

    if "image" in observation:
        img = observation["image"]
        if hasattr(img, "tobytes"):
            request.observation.image.data = img.tobytes()
            request.observation.image.height = img.shape[0]
            request.observation.image.width = img.shape[1]
            request.observation.image.channels = (
                img.shape[2] if len(img.shape) > 2 else 3
            )
        elif isinstance(img, np.ndarray):
            request.observation.image.data = img.tobytes()
            request.observation.image.height = img.shape[0]
            request.observation.image.width = img.shape[1]
            request.observation.image.channels = (
                img.shape[2] if len(img.shape) > 2 else 3
            )

    return request
