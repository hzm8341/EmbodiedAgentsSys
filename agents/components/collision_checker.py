import numpy as np
from typing import Dict, List, Any, Optional


class CollisionChecker:
    """
    Collision checker for grasp planning.
    Validates grasp points against workspace bounds and known obstacles.
    """

    def __init__(
        self,
        collision_margin: float = 0.05,
        workspace_bounds: Optional[Dict[str, List[float]]] = None
    ):
        self.collision_margin = collision_margin
        self.workspace_bounds = workspace_bounds or {
            "x": [-0.5, 0.5],
            "y": [-0.5, 0.5],
            "z": [0.0, 0.8]
        }
        self.known_obstacles: List[Dict] = []

    def _check_workspace_bounds(self, position: Dict[str, float]) -> bool:
        """Return True if position is within workspace bounds."""
        for axis, bounds in self.workspace_bounds.items():
            if axis in position:
                val = position[axis]
                if val < bounds[0] - self.collision_margin or val > bounds[1] + self.collision_margin:
                    return False
        return True

    def _check_obstacle_collision(self, position: Dict[str, float], radius: float = 0.05) -> bool:
        """Return True if position collides with a known obstacle."""
        pos = np.array([position.get("x", 0), position.get("y", 0), position.get("z", 0)])
        for obs in self.known_obstacles:
            dist = np.linalg.norm(pos - np.array(obs["position"]))
            if dist < (radius + obs["radius"] + self.collision_margin):
                return True
        return False

    def validate_grasp_points(self, grasp_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate grasp points, setting collision_free flag on each.
        Returns all points sorted: collision-free first, then by quality_score desc.
        """
        validated = []
        for gp in grasp_points:
            position = gp.get("position", {})
            in_bounds = self._check_workspace_bounds(position)
            obstacle_hit = self._check_obstacle_collision(position) if in_bounds else False
            point = gp.copy()
            point["collision_free"] = in_bounds and not obstacle_hit
            validated.append(point)

        validated.sort(key=lambda x: (0 if x["collision_free"] else 1, -x.get("quality_score", 0)))
        return validated
