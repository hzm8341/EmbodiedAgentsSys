from backend.backends.ros2_gazebo_backend import ROS2GazeboBackend


def test_ros2_backend_exposes_expected_capabilities():
    backend = ROS2GazeboBackend(node=None)

    descriptor = backend.descriptor

    assert descriptor.backend_id == "ros2_gazebo"
    assert descriptor.display_name == "ROS2 Humble + Gazebo"
    assert descriptor.kind == "ros2_gazebo"
    assert descriptor.available is False
    assert "scene" in descriptor.capabilities
    assert "command" in descriptor.capabilities
