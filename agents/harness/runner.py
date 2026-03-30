"""HarnessRunner — end-to-end evaluation pipeline."""
from __future__ import annotations
import uuid
from agents.harness.core.config import HarnessConfig
from agents.harness.core.task_set import Task, TaskSet
from agents.harness.core.tracer import HarnessTracer, TaskStatus
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.core.scorer import HarnessScorer, ScoreReport
from agents.harness.core.evaluators.result_eval import ResultEvaluator
from agents.harness.core.evaluators.efficiency_eval import EfficiencyEvaluator
from agents.harness.core.evaluators.robustness_eval import RobustnessEvaluator
from agents.harness.core.evaluators.explainability_eval import ExplainabilityEvaluator


class HarnessRunner:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self._env = HarnessEnvironment.create(config)
        self._scorer = HarnessScorer(pass_threshold=config.pass_threshold)
        self._evaluators = [
            ResultEvaluator(),
            EfficiencyEvaluator(),
            RobustnessEvaluator(),
            ExplainabilityEvaluator(),
        ]

    def evaluate(self, task_set: TaskSet) -> list[ScoreReport]:
        return [self._run_task(task) for task in task_set.all_tasks()]

    def _run_task(self, task: Task) -> ScoreReport:
        tracer = HarnessTracer(self.config)
        tracer.start_trace(task.task_id, str(uuid.uuid4())[:8])

        all_passed = True
        for skill_id in task.expected_skills:
            if self._env.skill_registry:
                result = self._env.skill_registry.call_skill(skill_id, {})
                tracer.record_tool_call(
                    "start_policy", {"skill_id": skill_id}, result.content
                )
                if not result.success:
                    all_passed = False
            else:
                tracer.record_tool_call(
                    "start_policy", {"skill_id": skill_id}, "real mode"
                )

        status = TaskStatus.COMPLETED if all_passed else TaskStatus.FAILED
        trace = tracer.stop_trace(status=status)

        eval_scores = [ev.evaluate(trace, task) for ev in self._evaluators]
        return self._scorer.score(eval_scores, task_id=task.task_id)

    def summary(self, reports: list[ScoreReport]) -> str:
        lines = ["=" * 50, "Harness Evaluation Summary", "=" * 50]
        for r in reports:
            lines.append(r.summary())
            lines.append("-" * 30)
        passed = sum(1 for r in reports if r.passed)
        lines.append(f"Total: {passed}/{len(reports)} passed")
        return "\n".join(lines)
