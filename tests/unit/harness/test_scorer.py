import pytest
from agents.harness.core.scorer import HarnessScorer, ScoreReport
from agents.harness.core.evaluators.base import EvaluationScore


def test_scorer_basic():
    scores = [
        EvaluationScore("result", 1.0, 0.25, {}, True),
        EvaluationScore("efficiency", 0.8, 0.25, {}, True),
        EvaluationScore("robustness", 0.9, 0.25, {}, True),
        EvaluationScore("explainability", 0.7, 0.25, {}, True),
    ]
    report = HarnessScorer(pass_threshold=0.70).score(scores)
    assert report.total_score == pytest.approx((1.0 + 0.8 + 0.9 + 0.7) / 4, abs=0.01)
    assert report.passed is True


def test_scorer_excludes_zero_weight_dimension():
    """When explainability weight=0 (mock mode), use only other 3 dimensions."""
    scores = [
        EvaluationScore("result", 1.0, 0.25, {}, True),
        EvaluationScore("efficiency", 0.8, 0.25, {}, True),
        EvaluationScore("robustness", 0.9, 0.25, {}, True),
        EvaluationScore("explainability", 0.0, 0.0, {}, True),  # excluded
    ]
    report = HarnessScorer(pass_threshold=0.70).score(scores)
    assert report.total_score == pytest.approx((1.0 + 0.8 + 0.9) / 3, abs=0.01)
    assert report.passed is True
    assert len(report.active_dimensions) == 3


def test_scorer_fails_below_threshold():
    scores = [
        EvaluationScore("result", 0.2, 0.25, {}, False),
        EvaluationScore("efficiency", 0.3, 0.25, {}, False),
        EvaluationScore("robustness", 0.4, 0.25, {}, False),
        EvaluationScore("explainability", 0.1, 0.25, {}, False),
    ]
    report = HarnessScorer(pass_threshold=0.70).score(scores)
    assert report.passed is False
