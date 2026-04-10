"""后端 API 测试"""
import sys
sys.path.insert(0, "/media/hzm/Data/EmbodiedAgentsSys")

def test_execute_move_to():
    from backend.services.simulation import simulation_service
    simulation_service.initialize()
    result = simulation_service.execute_action("move_to", {"x": 0.5, "y": 0, "z": 0.3})
    assert result.status.value == "success"

def test_get_scene():
    from backend.services.simulation import simulation_service
    scene = simulation_service.get_scene()
    assert "robot_position" in scene