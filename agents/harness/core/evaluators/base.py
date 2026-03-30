from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.harness.core.task_set import Task
    from agents.harness.core.tracer import HarnessTrace


@dataclass
class EvaluationScore:
    dimension: str
    score: float        # 0.0 - 1.0
    weight: float       # contribution to total score
    details: dict
    passed: bool

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


class Evaluator(ABC):
    dimension: str = "base"
    weight: float = 1.0

    def evaluate(self, trace: "HarnessTrace", task: "Task") -> EvaluationScore:
        return self._do_evaluate(trace, task)

    @abstractmethod
    def _do_evaluate(self, trace: "HarnessTrace", task: "Task") -> EvaluationScore:
        raise NotImplementedError
