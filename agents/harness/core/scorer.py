from __future__ import annotations
from dataclasses import dataclass
from agents.harness.core.evaluators.base import EvaluationScore


@dataclass
class ScoreReport:
    task_id: str
    scores: list[EvaluationScore]
    active_dimensions: list[str]
    total_score: float
    passed: bool
    pass_threshold: float

    def summary(self) -> str:
        lines = [
            f"Task: {self.task_id}",
            f"Total: {self.total_score:.3f} ({'PASS' if self.passed else 'FAIL'})",
        ]
        for s in self.scores:
            flag = " [excluded]" if s.weight == 0.0 else ""
            lines.append(f"  {s.dimension}: {s.score:.3f} (w={s.weight:.2f}){flag}")
        return "\n".join(lines)


class HarnessScorer:
    def __init__(self, pass_threshold: float = 0.70):
        self.pass_threshold = pass_threshold

    def score(self, evaluation_scores: list[EvaluationScore],
              task_id: str = "") -> ScoreReport:
        active = [s for s in evaluation_scores if s.weight > 0]
        total = sum(s.score for s in active) / len(active) if active else 0.0

        return ScoreReport(
            task_id=task_id,
            scores=evaluation_scores,
            active_dimensions=[s.dimension for s in active],
            total_score=total,
            passed=total >= self.pass_threshold,
            pass_threshold=self.pass_threshold,
        )
