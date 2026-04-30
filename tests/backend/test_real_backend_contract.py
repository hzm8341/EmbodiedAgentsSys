from backend.backends.real_robot_backend import RealRobotBackend


def test_real_backend_contract_matches_simulation_backend_shape():
    backend = RealRobotBackend()
    descriptor = backend.descriptor
    assert descriptor.backend_id == "real_robot"
    assert "command" in descriptor.capabilities

    not_connected = backend.execute_command("move_arm_to", {"x": 0.1})
    assert not_connected["status"] == "failed"

    backend.initialize()
    hb = backend.heartbeat()
    assert hb["status"] == "ok"
    result = backend.execute_command("move_arm_to", {"x": 0.1})
    assert result["status"] == "success"
    assert result["data"]["acknowledged"] is True

