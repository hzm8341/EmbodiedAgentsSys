from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskStateMachine:
    state: str = "planned"
    replan_attempts: int = 0
    max_replans: int = 1

    def on_execute_started(self) -> None:
        if self.state in {"planned", "replanning"}:
            self.state = "executing"

    def on_execute_finished(self) -> None:
        if self.state == "executing":
            self.state = "verifying"

    def on_verified(self, success: bool) -> None:
        if success:
            self.state = "done"
            return
        if self.replan_attempts < self.max_replans:
            self.replan_attempts += 1
            self.state = "replanning"
        else:
            self.state = "failed"

    @property
    def terminal(self) -> bool:
        return self.state in {"done", "failed"}

