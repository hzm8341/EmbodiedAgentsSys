from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace
from agents.harness.core.mode import HarnessMode

_MOCK_MODES = {HarnessMode.SKILL_MOCK, HarnessMode.HARDWARE_MOCK, HarnessMode.FULL_MOCK}


class ExplainabilityEvaluator(Evaluator):
    dimension = "explainability"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        is_mock = trace.mode in _MOCK_MODES
        n_decisions = len(trace.cot_decisions)

        # Mock mode + no CoT: exclude from scoring (weight=0)
        if is_mock and n_decisions == 0:
            return EvaluationScore(
                dimension=self.dimension,
                score=0.0,
                weight=0.0,
                details={"mode_aware": True, "reason": "mock mode, no CoT data available"},
                passed=True,
            )

        # Real mode with no CoT: penalize
        if n_decisions == 0:
            return EvaluationScore(
                dimension=self.dimension, score=0.0, weight=self.weight,
                details={"cot_count": 0, "note": "no CoT decisions recorded"},
                passed=False,
            )

        decisions_with_reasoning = sum(
            1 for d in trace.cot_decisions if d.reasoning and len(d.reasoning) > 5
        )
        reasoning_completeness = decisions_with_reasoning / n_decisions

        expected = set(task.expected_skills)
        decision_skills = {
            d.action_args.get("skill_id", "") for d in trace.cot_decisions
            if d.action_type == "skill"
        } - {""}
        skill_alignment = (
            len(expected & decision_skills) / len(expected) if expected else 1.0
        )

        score = 0.5 * reasoning_completeness + 0.5 * skill_alignment
        return EvaluationScore(
            dimension=self.dimension, score=score, weight=self.weight,
            details={
                "cot_count": n_decisions,
                "reasoning_completeness": reasoning_completeness,
                "skill_alignment": skill_alignment,
            },
            passed=score >= 0.5,
        )
