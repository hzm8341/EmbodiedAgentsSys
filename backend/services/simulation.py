"""仿真环境管理服务"""
from typing import Optional
from simulation.mujoco import GymnasiumEnvDriver

class SimulationService:
    """单例仿真服务"""
    _instance: Optional['SimulationService'] = None
    _driver: Optional[GymnasiumEnvDriver] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, env_name: str = "FrankaPushSparse-v0"):
        """初始化仿真环境"""
        if self._driver is None:
            self._driver = GymnasiumEnvDriver(
                env_name=env_name,
                render_mode="human"
            )
            self._driver.reset()
        return self

    def execute_action(self, action: str, params: dict):
        """执行动作"""
        if self._driver is None:
            self.initialize()
        return self._driver.execute_action(action, params)

    def get_scene(self) -> dict:
        """获取场景状态"""
        if self._driver is None:
            return {"robot_position": [0, 0, 0], "object_position": [0, 0, 0]}
        return self._driver.get_scene()

    def reset(self):
        """重置环境"""
        if self._driver:
            self._driver.reset()
        return {"status": "success", "message": "Environment reset"}


# 全局实例
simulation_service = SimulationService()