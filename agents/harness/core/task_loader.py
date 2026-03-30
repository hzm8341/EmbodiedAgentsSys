from __future__ import annotations
import json
import yaml
from pathlib import Path
from agents.harness.core.task_set import Task, TaskSet


class TaskLoader:
    def load_from_dir(self, dir_path: str | Path) -> TaskSet:
        dir_path = Path(dir_path)
        ts = TaskSet()
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text())
                if data and "task_id" in data:
                    ts.declarative.append(Task.from_dict(data))
            except Exception:
                continue
        return ts

    def load_from_failure_logs(self, log_path: str | Path) -> TaskSet:
        log_path = Path(log_path)
        ts = TaskSet()
        if not log_path.exists():
            return ts
        for line in log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                skill_id = rec.get("skill_id")
                expected_skills = [skill_id] if skill_id else []
                task = Task(
                    task_id=f"regression_{rec.get('timestamp', 'unknown').replace(':', '-')}",
                    description=rec.get("task_description", "regression task"),
                    robot_type=rec.get("robot_type", "arm"),
                    expected_skills=expected_skills,
                    is_regression=True,
                    tags=["regression", rec.get("error_type", "unknown")],
                )
                ts.regression.append(task)
            except Exception:
                continue
        return ts
