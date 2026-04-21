"""Simulation environment management service"""
import os
import threading
import time
import mujoco
from typing import Optional
from simulation.mujoco import MuJoCoDriver
from simulation.mujoco.config import DEFAULT_URDF_PATH

class SimulationService:
    """Singleton simulation service"""
    _instance: Optional['SimulationService'] = None
    _driver: Optional[MuJoCoDriver] = None
    _viewer = None
    _viewer_thread: Optional[threading.Thread] = None
    _viewer_running = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, urdf_path: Optional[str] = None):
        """Initialize simulation environment"""
        if self._driver is None:
            urdf = urdf_path or os.getenv("MUJOCO_URDF_PATH", DEFAULT_URDF_PATH)
            self._driver = MuJoCoDriver(urdf_path=urdf)
            self._driver.reset()
        return self

    def launch_viewer(self) -> None:
        """在独立守护线程里启动 MuJoCo passive viewer。

        GLFW 在某些 Linux 环境下不能从 asyncio 事件循环线程创建窗口，
        必须在独立线程里调用 launch_passive 并运行完整的渲染循环。
        设置 NO_MUJOCO_VIEWER=1 可跳过（headless/CI 模式）。
        """
        if self._driver is None:
            return
        if os.getenv("NO_MUJOCO_VIEWER", "0") == "1":
            print("MuJoCo viewer disabled (NO_MUJOCO_VIEWER=1)")
            return

        self._viewer_running = True
        self._viewer_thread = threading.Thread(
            target=self._viewer_loop,
            daemon=True,
            name="mujoco-viewer",
        )
        self._viewer_thread.start()
        # 等待 viewer 初始化完成（最多 5 秒）
        for _ in range(50):
            if self._viewer is not None:
                break
            time.sleep(0.1)

    def _viewer_loop(self) -> None:
        """Viewer 渲染循环（运行在独立线程）。

        viewer.close() 必须在本线程调用，避免与 sync() 产生并发 segfault。
        """
        viewer = None
        try:
            import mujoco.viewer as mjviewer
            print("Launching MuJoCo viewer window...")
            viewer = mjviewer.launch_passive(
                self._driver._model, self._driver._data
            )
            self._viewer = viewer
            self._driver.set_viewer(viewer)
            print("✓ MuJoCo viewer opened successfully")

            while self._viewer_running and viewer.is_running():
                # Acquire render lock before sync() to avoid concurrent access
                # with the simulation thread (animate_joints / ik_solve).
                if self._driver is not None:
                    with self._driver._render_lock:
                        viewer.sync()
                else:
                    viewer.sync()
                time.sleep(0.016)   # ~60 fps

        except Exception as e:
            print(f"✗ MuJoCo viewer error: {e}")
        finally:
            # close() 只在 viewer 线程调用，防止跨线程 segfault
            if viewer is not None:
                try:
                    viewer.close()
                except Exception:
                    pass
            self._viewer = None
            if self._driver is not None:
                self._driver.set_viewer(None)
            print("MuJoCo viewer closed")

    def close_viewer(self) -> None:
        """Stop the viewer loop and wait for clean exit."""
        self._viewer_running = False
        # 不直接调用 viewer.close()，由 _viewer_loop finally 块负责
        if self._viewer_thread and self._viewer_thread.is_alive():
            self._viewer_thread.join(timeout=2.0)

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

    def reset_to_home(self) -> dict:
        """Reset robot to home position and restore objects."""
        if self._driver:
            self._driver.reset_to_home()
        return {"status": "success", "message": "Reset to home position"}

    def reset(self):
        """Reset environment"""
        if self._driver:
            self._driver.reset()
        return {"status": "success", "message": "Environment reset"}


# Global instance
simulation_service = SimulationService()
