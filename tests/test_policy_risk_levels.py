from agents.policy.validation_pipeline import TwoLevelValidationPipeline


def test_task_risk_levels():
    pipeline = TwoLevelValidationPipeline()
    assert pipeline.classify_task_risk("move left arm to home") == "low"
    assert pipeline.classify_task_risk("pick and place cube") == "medium"
    assert pipeline.classify_task_risk("real robot high speed force test") == "high"

