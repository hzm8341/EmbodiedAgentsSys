from .mujoco_driver import MuJoCoDriver
from .scene_builder import SceneBuilder
from .robot_model import RobotModel
from .sensors import ForceSensor, ContactSensor

try:
    from .gymnasium_env_driver import GymnasiumEnvDriver
except ModuleNotFoundError as exc:
    if exc.name != "gymnasium":
        raise

    class GymnasiumEnvDriver:  # type: ignore[no-redef]
        """Fallback stub when optional gymnasium dependency is unavailable."""

        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "No module named 'gymnasium'. Install optional dependency to use GymnasiumEnvDriver."
            )

__all__ = [
    "MuJoCoDriver",
    "SceneBuilder",
    "RobotModel",
    "ForceSensor",
    "ContactSensor",
    "GymnasiumEnvDriver",
]
