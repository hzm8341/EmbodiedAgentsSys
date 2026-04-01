from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace


class EfficiencyEvaluator(Evaluator):
    dimension = "efficiency"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        max_dur = task.success_criteria.efficiency.max_duration_seconds
        duration_ms = trace.duration_ms

        if duration_ms is None:
            score = 0.5
            details = {"note": "duration not available"}
        elif max_dur <= 0:
            score = 0.0
            details = {"note": "invalid max_duration_seconds=0"}
        else:
            duration_s = duration_ms / 1000.0
            if duration_s <= max_dur:
                score = 1.0 - (duration_s / max_dur) * 0.3
            else:
                score = max(0.0, 1.0 - (duration_s / max_dur - 1.0))
            details = {
                "duration_s": duration_s,
                "max_duration_s": max_dur,
                "ratio": duration_s / max_dur,
            }

        return EvaluationScore(
            dimension=self.dimension, score=score,
            weight=self.weight, details=details, passed=score >= 0.5,
        )
