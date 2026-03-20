# tests/test_voice_template_agent.py
import pytest
from agents.components.voice_template_agent import VoiceTemplateAgent
from agents.components.scene_spec import SceneSpec

ANSWERS = {
    "scene_type": "warehouse_pick",
    "environment": "Large warehouse with metal shelves",
    "robot_type": "arm",
    "task_description": "Pick red box from shelf A and place on conveyor",
    "objects": "red_box, shelf_A, conveyor",
    "constraints": "avoid_fragile_zone",
    "success_criteria": "box_on_conveyor",
}


@pytest.fixture
def agent():
    return VoiceTemplateAgent()


@pytest.mark.anyio
async def test_fill_from_answers_returns_scene_spec(agent):
    spec = await agent.fill_from_answers(ANSWERS)
    assert isinstance(spec, SceneSpec)


@pytest.mark.anyio
async def test_scene_type_preserved(agent):
    spec = await agent.fill_from_answers(ANSWERS)
    assert spec.scene_type == "warehouse_pick"


@pytest.mark.anyio
async def test_objects_parsed_from_comma_string(agent):
    spec = await agent.fill_from_answers(ANSWERS)
    assert "red_box" in spec.objects
    assert "conveyor" in spec.objects


@pytest.mark.anyio
async def test_missing_required_answer_raises(agent):
    bad = {k: v for k, v in ANSWERS.items() if k != "task_description"}
    with pytest.raises((KeyError, ValueError)):
        await agent.fill_from_answers(bad)


def test_questions_list_complete(agent):
    """All required SceneSpec fields have a corresponding question."""
    required = {"scene_type", "environment", "robot_type", "task_description"}
    question_keys = {q[0] for q in agent.QUESTIONS}
    assert required.issubset(question_keys)


@pytest.mark.anyio
async def test_interactive_fill_uses_input_fn(agent):
    """interactive_fill calls input_fn for each question and returns a SceneSpec."""
    answer_map = dict(ANSWERS)
    call_count = [0]

    async def mock_input(prompt: str) -> str:
        call_count[0] += 1
        for key, val in answer_map.items():
            if key in prompt.lower():
                return val
        return "default"

    outputs = []
    async def mock_output(text: str) -> None:
        outputs.append(text)

    spec = await agent.interactive_fill(mock_input, mock_output)
    assert isinstance(spec, SceneSpec)
    assert call_count[0] >= 4
    assert len(outputs) >= 4  # output_fn called at least once per required question
