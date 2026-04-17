"""Simulation environment management service"""
import os
from typing import Optional
from simulation.mujoco import MuJoCoDriver
from simulation.mujoco.config import DEFAULT_URDF_PATH

class SimulationService:
    """Singleton simulation service"""
    _instance: Optional['SimulationService'] = None
    _driver: Optional[MuJoCoDriver] = None
    _viewer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, urdf_path: Optional[str] = None):
        """Initialize simulation environment"""
        if self._driver is None:
            # Use provided URDF path or default
            urdf = urdf_path or os.getenv("MUJOCO_URDF_PATH", DEFAULT_URDF_PATH)
            self._driver = MuJoCoDriver(urdf_path=urdf)
            self._driver.reset()
        return self

    def launch_viewer(self) -> None:
        """Launch passive MuJoCo viewer and attach to driver."""
        if self._driver is None:
            return
        try:
            import mujoco.viewer
            self._viewer = mujoco.viewer.launch_passive(
                self._driver._model, self._driver._data
            )
            self._driver.set_viewer(self._viewer)
        except Exception as e:
            print(f"Warning: Could not launch MuJoCo viewer: {e}")

    def close_viewer(self) -> None:
        """Close the passive viewer if open."""
        if self._viewer is not None:
            try:
                self._viewer.close()
            except Exception:
                pass
            self._viewer = None
            if self._driver is not None:
                self._driver.set_viewer(None)

    def execute_action(self, action: str, params: dict):
        """Execute action"""
        if self._driver is None:
            self.initialize()
        return self._driver.execute_action(action, params)

    def get_scene(self) -> dict:
        """Get scene state"""
        if self._driver is None:
            return {"robot_position": [0, 0, 0], "object_position": [0, 0, 0]}
        return self._driver.get_scene()

    def reset(self):
        """Reset environment"""
        if self._driver:
            self._driver.reset()
        return {"status": "success", "message": "Environment reset"}


# Global instance
simulation_service = SimulationService()
