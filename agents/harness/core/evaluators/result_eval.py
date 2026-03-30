from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace, TaskStatus


class ResultEvaluator(Evaluator):
    dimension = "result"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        if trace.final_status == TaskStatus.COMPLETED:
            base_score = 1.0
        elif trace.final_status == TaskStatus.FAILED:
            base_score = 0.0
        else:
            base_score = 0.3

        expected = set(task.expected_skills)
        if not expected:
            skill_coverage = 1.0
        else:
            called = set(trace.skill_calls)
            skill_coverage = len(expected & called) / len(expected)

        final_score = base_score * skill_coverage
        passed = final_score >= 0.5

        return EvaluationScore(
            dimension=self.dimension,
            score=final_score,
            weight=self.weight,
            details={
                "base_score": base_score,
                "skill_coverage": skill_coverage,
                "expected_skills": list(expected),
                "called_skills": list(trace.skill_calls),
            },
            passed=passed,
        )
