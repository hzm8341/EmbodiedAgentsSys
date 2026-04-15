"""Simulation environment management service"""
import os
from typing import Optional
from simulation.mujoco import MuJoCoDriver
from simulation.mujoco.config import DEFAULT_URDF_PATH

class SimulationService:
    """Singleton simulation service"""
    _instance: Optional['SimulationService'] = None
    _driver: Optional[MuJoCoDriver] = None

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
