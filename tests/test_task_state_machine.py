from agents.core.task_state_machine import TaskStateMachine


def test_task_state_machine_success_path():
    sm = TaskStateMachine(max_replans=1)
    assert sm.state == "planned"
    sm.on_execute_started()
    assert sm.state == "executing"
    sm.on_execute_finished()
    assert sm.state == "verifying"
    sm.on_verified(True)
    assert sm.state == "done"
    assert sm.terminal is True


def test_task_state_machine_failure_to_failed():
    sm = TaskStateMachine(max_replans=1)
    sm.on_execute_started()
    sm.on_execute_finished()
    sm.on_verified(False)
    assert sm.state == "replanning"
    sm.on_execute_started()
    sm.on_execute_finished()
    sm.on_verified(False)
    assert sm.state == "failed"
    assert sm.terminal is True

