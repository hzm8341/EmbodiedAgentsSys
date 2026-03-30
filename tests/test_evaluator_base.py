import pytest
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore


def test_evaluation_score():
    s = EvaluationScore(
        dimension="result", score=0.8, weight=0.25,
        details={"note": "ok"}, passed=True
    )
    assert s.weighted_score == pytest.approx(0.8 * 0.25)


def test_evaluator_abstract():
    with pytest.raises(TypeError):
        Evaluator()
