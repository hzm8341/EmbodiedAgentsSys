import json
import pytest
from pathlib import Path
from agents.harness.core.task_loader import TaskLoader


def test_load_tasks_from_dir(tmp_path):
    (tmp_path / "t1.yaml").write_text("""
task_id: test_001
description: Test task
robot_type: arm
scene:
  objects: []
expected_skills:
  - "manipulation.grasp"
success_criteria:
  result: {}
  efficiency: {}
  robustness: {}
""")
    loader = TaskLoader()
    ts = loader.load_from_dir(tmp_path)
    assert len(ts.declarative) == 1
    assert ts.declarative[0].task_id == "test_001"


def test_load_from_failure_logs_extracts_skill_id(tmp_path):
    record = {
        "timestamp": "2026-03-30T10:00:00+00:00",
        "task_description": "pick apple",
        "subtask_id": "sub_001",
        "subtask_description": "grasp apple",
        "skill_id": "manipulation.grasp",
        "error_type": "grasp_failure",
        "error_detail": "gripper slipped",
        "robot_type": "arm",
        "scene_context": {},
    }
    log_file = tmp_path / "failure_log.ndjson"
    log_file.write_text(json.dumps(record) + "\n")

    loader = TaskLoader()
    ts = loader.load_from_failure_logs(log_file)
    assert len(ts.regression) == 1
    assert "manipulation.grasp" in ts.regression[0].expected_skills
    assert ts.regression[0].robot_type == "arm"


def test_load_skips_invalid_yaml(tmp_path):
    (tmp_path / "bad.yaml").write_text("not: a: task")
    loader = TaskLoader()
    ts = loader.load_from_dir(tmp_path)
    assert len(ts.declarative) == 0
