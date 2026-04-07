import pytest
from agents.harness.core.task_set import Task, TaskSet, SuccessCriteria, EfficiencyCriteria


def test_task_creation():
    t = Task(task_id="t1", description="test", robot_type="arm")
    assert t.task_id == "t1"
    assert t.expected_skills == []
    assert t.is_regression is False


def test_task_from_dict():
    data = {
        "task_id": "pick_001",
        "description": "Pick red cube",
        "robot_type": "arm",
        "scene": {
            "objects": [
                {"id": "cube", "type": "cube", "color": "red",
                 "initial_position": [0.3, -0.1, 0.05]}
            ]
        },
        "expected_skills": ["manipulation.reach", "manipulation.grasp"],
        "success_criteria": {
            "result": {"type": "position_match", "object": "cube",
                       "target": "zone_b", "tolerance": 0.02},
            "efficiency": {"max_duration_seconds": 30},
            "robustness": {"max_retry_count": 2, "allowed_failures": ["gripper_slope"]},
        },
        "tags": ["basic"],
    }
    t = Task.from_dict(data)
    assert t.task_id == "pick_001"
    assert len(t.scene_objects) == 1
    assert t.success_criteria.efficiency.max_duration_seconds == 30
    assert "manipulation.grasp" in t.expected_skills


def test_task_set_instances_are_independent():
    """Regression: TaskSet must use @dataclass so list fields are per-instance."""
    ts1 = TaskSet()
    ts2 = TaskSet()
    t = Task(task_id="x", description="x", robot_type="arm")
    ts1.declarative.append(t)
    assert len(ts2.declarative) == 0, "TaskSet instances share list — @dataclass missing!"


def test_task_set_all_tasks():
    ts = TaskSet()
    ts.declarative.append(Task(task_id="d1", description="", robot_type="arm"))
    ts.regression.append(Task(task_id="r1", description="", robot_type="arm", is_regression=True))
    assert len(ts.all_tasks()) == 2


def test_task_set_filter_by_tag():
    ts = TaskSet()
    ts.declarative.append(Task(task_id="a", description="", robot_type="arm", tags=["basic"]))
    ts.declarative.append(Task(task_id="b", description="", robot_type="arm", tags=["vision"]))
    filtered = ts.filter(["basic"])
    assert len(filtered.declarative) == 1
    assert filtered.declarative[0].task_id == "a"
