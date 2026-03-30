from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace


class RobustnessEvaluator(Evaluator):
    dimension = "robustness"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        max_retries = task.success_criteria.robustness.max_retry_count
        policy_calls = [tc for tc in trace.tool_calls if tc.tool_name == "start_policy"]
        retries = max(0, len(policy_calls) - 1)

        if retries == 0:
            score = 1.0
        elif retries <= max_retries:
            score = 1.0 - (retries / (max_retries + 1)) * 0.5
        else:
            score = max(0.0, 0.5 - (retries - max_retries) * 0.1)

        return EvaluationScore(
            dimension=self.dimension, score=score,
            weight=self.weight,
            details={"retries": retries, "max_retries": max_retries},
            passed=score >= 0.5,
        )
